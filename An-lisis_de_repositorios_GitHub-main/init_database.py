import sys
import os
import psycopg2
from psycopg2 import sql

# Agregar el directorio raiz al path para poder importar config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config.config import DB_CONFIG

def init_database(dedupe=False):
    """Inicializa la base de datos y crea el schema"""
    
    # Leer el schema.sql
    with open('database/schema.sql', 'r', encoding='utf-8') as f:
        schema_content = f.read()
    
    try:
        # Primero conectar al servidor para crear la DB si no existe
        print("Conectando a PostgreSQL...")
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database='postgres' # Nos conectamos a postgres para poder crear la otra DB
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Verificar si la BD existe
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'github_analyzer'")
        exists = cursor.fetchone()
        
        if not exists:
            print('[INFO] Creando base de datos github_analyzer...')
            cursor.execute(sql.SQL('CREATE DATABASE github_analyzer;'))
            print('[OK] Base de datos creada exitosamente')
        else:
            print('[INFO] Base de datos github_analyzer ya existe')
        
        cursor.close()
        conn.close()
        
        # Ahora conectar a la BD y ejecutar el schema
        print("Conectando a la base de datos github_analyzer...")
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database']
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Dividir el script en comandos individuales y ejecutar
        commands = schema_content.split(';')
        command_count = 0
        
        for command in commands:
            # Quitar las líneas de comentario para no descartar el bloque completo
            command = '\n'.join(
                line for line in command.splitlines()
                if not line.strip().startswith('--')
            ).strip()
            if command:
                if not command.startswith('\\c'):  # Skip connection commands
                    try:
                        print(f'[{command_count+1}] Ejecutando: {command[:60]}...')
                        cursor.execute(command)
                        command_count += 1
                    except psycopg2.Error as e:
                        error_msg = str(e)
                        # Ignorar errores de tablas/indices/vistas que ya existen
                        if any(x in error_msg for x in ['ya existe', 'already exists', 'duplicate key']):
                            print(f'    [SKIP] Recurso ya existe')
                        else:
                            print(f'    [ERROR] {error_msg}')

        backfill_fingerprints(cursor, dedupe=dedupe)

        cursor.close()
        conn.close()
        
        print(f'\n[OK] Schema inicializado exitosamente ({command_count} comandos ejecutados)')
        return True
        
    except psycopg2.Error as e:
        print(f'[ERROR] Problema de conexion a PostreSQL: {e}')
        return False
    except Exception as e:
        print(f'[ERROR] {e}')
        return False

def backfill_fingerprints(cursor, dedupe=False):
    """
    Calcula el fingerprint de las credenciales registradas antes del
    fingerprinting. Si varias filas comparten fingerprint, la más antigua
    lo conserva y las demás se reportan como duplicadas (o se eliminan
    si se ejecuta con --dedupe).
    """
    from utils.credential_detector import credential_detector

    cursor.execute("""
        SELECT cd.credential_id, cd.file_path, cd.matched_pattern,
               r.repo_owner, r.repo_name
        FROM credentials_detected cd
        JOIN commits c ON cd.commit_id = c.commit_id
        JOIN repositories r ON c.repo_id = r.repo_id
        WHERE cd.fingerprint IS NULL
        ORDER BY cd.credential_id
    """)
    rows = cursor.fetchall()
    if not rows:
        return

    cursor.execute("SELECT fingerprint FROM credentials_detected WHERE fingerprint IS NOT NULL")
    taken = {r[0] for r in cursor.fetchall()}
    duplicates = []
    updated = 0

    for credential_id, file_path, pattern, owner, name in rows:
        fp = credential_detector.compute_fingerprint(owner, name, file_path, pattern)
        if fp in taken:
            duplicates.append(credential_id)
            continue
        cursor.execute(
            "UPDATE credentials_detected SET fingerprint = %s WHERE credential_id = %s",
            (fp, credential_id)
        )
        taken.add(fp)
        updated += 1

    print(f'[OK] Fingerprint calculado para {updated} credenciales existentes')

    if duplicates:
        if dedupe:
            cursor.execute(
                "DELETE FROM credentials_detected WHERE credential_id = ANY(%s)",
                (duplicates,)
            )
            print(f'[OK] Eliminados {len(duplicates)} registros duplicados')
        else:
            print(f'[WARNING] {len(duplicates)} registros son duplicados de otro hallazgo. '
                  f'Ejecuta "python init_database.py --dedupe" para eliminarlos.')


if __name__ == '__main__':
    import sys
    success = init_database(dedupe='--dedupe' in sys.argv)
    sys.exit(0 if success else 1)
