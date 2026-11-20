# -*- coding: utf-8 -*-
"""
Modulo de conexion y operaciones con PostgreSQL
"""

import psycopg2
from psycopg2 import pool, Error
from psycopg2.extras import RealDictCursor
import pandas as pd
import json
import sys
import os

# Agregar el directorio raiz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import DB_CONFIG


class DatabaseManager:
    """Gestor de conexiones y operaciones con PostgreSQL"""

    def __init__(self):
        """Inicializa el pool de conexiones"""
        self.connection_pool = None
        try:
            self.connection_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=20,
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                database=DB_CONFIG['database'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password']
            )
            print("[OK] Pool de conexiones creado exitosamente")
        except Exception as error:
            print(f"[WARNING] Error al crear pool de conexiones: {error}")
            print("[INFO] La aplicacion continuara funcionando sin conexion a BD inicialmente")
            # No levantamos la excepcion para permitir que la aplicacion se inicie

    def get_connection(self):
        """Obtiene una conexion del pool"""
        if not self.connection_pool:
            raise Exception("Pool de conexiones no inicializado")
        return self.connection_pool.getconn()

    def return_connection(self, connection):
        """Devuelve una conexion al pool"""
        if self.connection_pool and connection:
            self.connection_pool.putconn(connection)

    def execute_query(self, query, params=None, fetch=False):
        """
        Ejecuta una consulta SQL
        """
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params)

            if fetch:
                result = cursor.fetchall()
                connection.commit()
                return result
            else:
                connection.commit()
                return None

        except (Exception, Error) as error:
            if connection:
                connection.rollback()
            print(f"[ERROR] Error ejecutando consulta: {error}")
            raise

        finally:
            if cursor:
                cursor.close()
            if connection:
                self.return_connection(connection)

    # --------------------------------------------------
    # INSERTS
    # --------------------------------------------------

    def insert_repository(self, repo_name, repo_owner, repo_url):
        query = """
            INSERT INTO repositories (repo_name, repo_owner, repo_url)
            VALUES (%s, %s, %s)
            ON CONFLICT (repo_owner, repo_name)
            DO UPDATE SET
                repo_url = EXCLUDED.repo_url,
                analysis_date = CURRENT_TIMESTAMP
            RETURNING repo_id
        """
        result = self.execute_query(query, (repo_name, repo_owner, repo_url), fetch=True)
        return result[0]['repo_id'] if result else None

    def insert_commit(self, repo_id, commit_data):
        query = """
            INSERT INTO commits (
                repo_id, commit_sha, commit_message, author_name,
                author_email, commit_date, files_changed, additions,
                deletions, has_credentials, risk_score
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (commit_sha)
            DO UPDATE SET
                has_credentials = EXCLUDED.has_credentials,
                risk_score = EXCLUDED.risk_score
            RETURNING commit_id
        """
        params = (
            repo_id,
            commit_data['sha'],
            commit_data['message'],
            commit_data['author_name'],
            commit_data['author_email'],
            commit_data['date'],
            commit_data.get('files_changed', 0),
            commit_data.get('additions', 0),
            commit_data.get('deletions', 0),
            commit_data.get('has_credentials', False),
            commit_data.get('risk_score', 0.0)
        )
        result = self.execute_query(query, params, fetch=True)
        return result[0]['commit_id'] if result else None

    def insert_credential(self, commit_id, credential_data):
        """
        Inserta un hallazgo. Si su fingerprint ya existe, no se duplica:
        solo se actualiza la fecha en que se volvió a ver.

        Returns:
            tuple: (credential_id, es_nuevo)
        """
        query = """
            INSERT INTO credentials_detected (
                commit_id, credential_type, file_path,
                line_number, matched_pattern, severity,
                fingerprint, line_content
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (fingerprint)
            DO UPDATE SET last_seen = CURRENT_TIMESTAMP
            RETURNING credential_id, (xmax = 0) AS inserted
        """
        params = (
            commit_id,
            credential_data['type'],
            credential_data['file_path'],
            credential_data.get('line_number'),
            credential_data['pattern'],
            credential_data.get('severity', 'HIGH'),
            credential_data['fingerprint'],
            credential_data.get('line_content')
        )
        result = self.execute_query(query, params, fetch=True)
        if not result:
            return None, False
        credential_id = result[0]['credential_id']

        # Registrar la ocurrencia (commit + línea) para el embudo de detección
        self.execute_query(
            """
            INSERT INTO credential_occurrences (credential_id, commit_id, line_number)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (credential_id, commit_id, credential_data.get('line_number'))
        )
        return credential_id, bool(result[0]['inserted'])

    def get_commits_with_features(self):
        """Commits con sus características y cuántos hallazgos reales tiene cada uno"""
        query = """
            SELECT
                c.commit_id, c.commit_sha, c.commit_message, c.author_name, c.commit_date,
                r.repo_owner, r.repo_name,
                cf.commit_hour, cf.commit_day_of_week, cf.message_length, cf.files_modified,
                cf.code_additions, cf.code_deletions, cf.has_config_files, cf.has_env_files,
                cf.is_sensitive_file,
                COUNT(cd.credential_id) FILTER (
                    WHERE COALESCE(cd.manual_label, cd.ml_prediction) = 1
                ) AS real_credentials
            FROM commits c
            JOIN repositories r ON c.repo_id = r.repo_id
            JOIN commit_features cf ON cf.commit_id = c.commit_id
            LEFT JOIN credentials_detected cd ON cd.commit_id = c.commit_id
            GROUP BY c.commit_id, r.repo_owner, r.repo_name, cf.feature_id
            ORDER BY c.commit_id
        """
        connection = self.get_connection()
        try:
            return pd.read_sql_query(query, connection)
        finally:
            self.return_connection(connection)

    def get_detection_count(self, repo_id=None):
        """Total de detecciones regex (cada aparición en cada commit, antes de deduplicar)"""
        query = "SELECT COUNT(*) AS total FROM credential_occurrences co"
        params = None
        if repo_id is not None:
            query += " JOIN commits c ON co.commit_id = c.commit_id WHERE c.repo_id = %s"
            params = (int(repo_id),)
        result = self.execute_query(query, params, fetch=True)
        return int(result[0]['total']) if result else 0

    def insert_commit_features(self, commit_id, features):
        query = """
            INSERT INTO commit_features (
                commit_id, has_suspicious_keywords, commit_hour,
                commit_day_of_week, message_length, files_modified,
                code_additions, code_deletions, has_config_files,
                has_env_files, regex_detected_count, max_regex_severity,
                is_sensitive_file, prediction_label, prediction_confidence
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (commit_id) DO UPDATE SET
                files_modified = EXCLUDED.files_modified,
                code_additions = EXCLUDED.code_additions,
                code_deletions = EXCLUDED.code_deletions,
                has_config_files = EXCLUDED.has_config_files,
                has_env_files = EXCLUDED.has_env_files,
                is_sensitive_file = EXCLUDED.is_sensitive_file
            RETURNING feature_id
        """
        params = (
            commit_id,
            features.get('has_suspicious_keywords', False),
            features.get('commit_hour', 0),
            features.get('commit_day_of_week', 0),
            features.get('message_length', 0),
            features.get('files_modified', 0),
            features.get('code_additions', 0),
            features.get('code_deletions', 0),
            features.get('has_config_files', False),
            features.get('has_env_files', False),
            features.get('regex_detected_count', 0),
            features.get('max_regex_severity', 0),
            features.get('is_sensitive_file', False),
            features.get('prediction_label', 0),
            features.get('prediction_confidence', 0.0)
        )
        result = self.execute_query(query, params, fetch=True)
        return result[0]['feature_id'] if result else None

    def insert_ml_results(self, results):
        query = """
            INSERT INTO ml_model_results (
                model_accuracy, precision_score, recall_score,
                f1_score, gini_importance, total_samples, total_features,
                model_name
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING model_id
        """
        params = (
            results['accuracy'],
            results['precision'],
            results['recall'],
            results['f1'],
            json.dumps(results['gini_importance']),
            results['total_samples'],
            results['total_features'],
            results.get('model_name')
        )
        result = self.execute_query(query, params, fetch=True)
        return result[0]['model_id'] if result else None

    # --------------------------------------------------
    # UPDATES
    # --------------------------------------------------

    def update_repository_stats(self, repo_id, total_commits, total_credentials, risk_level):
        query = """
            UPDATE repositories
            SET total_commits = %s,
                total_credentials_found = %s,
                risk_level = %s
            WHERE repo_id = %s
        """
        self.execute_query(query, (total_commits, total_credentials, risk_level, repo_id))

    def get_repository_counts(self, repo_id):
        """Cuántos commits, hallazgos y correcciones manuales tiene un repositorio"""
        query = """
            SELECT
                (SELECT COUNT(*) FROM commits WHERE repo_id = %s) AS commits,
                COUNT(cd.credential_id) AS credentials,
                COUNT(cd.manual_label) AS labeled
            FROM commits c
            LEFT JOIN credentials_detected cd ON cd.commit_id = c.commit_id
            WHERE c.repo_id = %s
        """
        result = self.execute_query(query, (repo_id, repo_id), fetch=True)
        row = result[0] if result else {}
        return {key: int(row.get(key) or 0) for key in ('commits', 'credentials', 'labeled')}

    def delete_repository(self, repo_id):
        """
        Borra un repositorio y todo lo que depende de él (commits, hallazgos,
        ocurrencias y características) gracias a ON DELETE CASCADE.
        """
        self.execute_query("DELETE FROM repositories WHERE repo_id = %s", (repo_id,))

    def set_manual_label(self, credential_ids, label):
        """
        Registra la etiqueta del auditor para uno o varios hallazgos.

        Args:
            credential_ids (list): IDs de credenciales
            label (int | None): 1 credencial real, 0 falso positivo, None quitar etiqueta
        """
        query = """
            UPDATE credentials_detected
            SET manual_label = %s,
                labeled_at = CASE WHEN %s IS NULL THEN NULL ELSE CURRENT_TIMESTAMP END
            WHERE credential_id = ANY(%s)
        """
        self.execute_query(query, (label, label, list(credential_ids)))

    def update_ml_predictions(self, predictions):
        """
        Guarda las predicciones del modelo.

        Args:
            predictions (list): tuplas (credential_id, prediccion, confianza)
        """
        if not predictions:
            return
        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    UPDATE credentials_detected
                    SET ml_prediction = %s, ml_confidence = %s
                    WHERE credential_id = %s
                    """,
                    [(int(p), float(c), int(cid)) for cid, p, c in predictions]
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            self.return_connection(connection)

    # --------------------------------------------------
    # DATAFRAMES
    # --------------------------------------------------

    def get_commits_dataframe(self, repo_id=None):
        if repo_id:
            query = "SELECT * FROM commits WHERE repo_id = %s"
            params = (repo_id,)
        else:
            query = "SELECT * FROM commits"
            params = None

        connection = self.get_connection()
        try:
            return pd.read_sql_query(query, connection, params=params)
        finally:
            self.return_connection(connection)

    def get_commit_features_dataframe(self):
        query = """
            SELECT
                cf.*,
                c.has_credentials AS actual_label
            FROM commit_features cf
            INNER JOIN commits c ON cf.commit_id = c.commit_id
        """
        connection = self.get_connection()
        try:
            return pd.read_sql_query(query, connection)
        finally:
            self.return_connection(connection)

    def get_credentials_dataframe(self, credential_ids=None):
        query = """
            SELECT
                cd.*,
                c.commit_sha,
                c.commit_message,
                c.author_name,
                c.commit_date,
                r.repo_name,
                r.repo_owner
            FROM credentials_detected cd
            INNER JOIN commits c ON cd.commit_id = c.commit_id
            INNER JOIN repositories r ON c.repo_id = r.repo_id
        """
        params = None
        if credential_ids is not None:
            query += " WHERE cd.credential_id = ANY(%s)"
            params = (list(credential_ids),)
        query += " ORDER BY cd.credential_id"
        connection = self.get_connection()
        try:
            return pd.read_sql_query(query, connection, params=params)
        finally:
            self.return_connection(connection)

    def get_repository_summary(self):
        query = "SELECT * FROM v_repository_summary"
        connection = self.get_connection()
        try:
            return pd.read_sql_query(query, connection)
        finally:
            self.return_connection(connection)

    # --------------------------------------------------
    # CIERRE
    # --------------------------------------------------

    def close_all_connections(self):
        if self.connection_pool:
            self.connection_pool.closeall()
            print("[OK] Conexiones cerradas")


# Singleton - se inicializa al importar pero sin lanzar excepciones
db_manager = DatabaseManager()
