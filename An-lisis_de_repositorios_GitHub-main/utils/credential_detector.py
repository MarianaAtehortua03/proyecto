"""
Módulo de detección de credenciales expuestas usando expresiones regulares
"""
import re
import hashlib
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import CREDENTIAL_PATTERNS

# Patrones genéricos: ceden ante uno específico cuando cubren el mismo fragmento
GENERIC_TYPES = {
    'db_password', 'db_user', 'env_secret', 'generic_secret', 'generic_token', 'generic_api_key',
    'url_with_credentials', 'netrc_password', 'xml_password', 'bearer_token'
}

# Encabezado de hunk de un diff unificado: "@@ -12,7 +14,9 @@"
HUNK_HEADER = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@')


class CredentialDetector:
    """Detector de credenciales expuestas en código"""
    
    def __init__(self):
        """Inicializa el detector con patrones regex"""
        self.patterns = CREDENTIAL_PATTERNS
        self.compiled_patterns = {}
        
        # Compilar todos los patrones regex para mejor rendimiento
        for credential_type, pattern in self.patterns.items():
            try:
                self.compiled_patterns[credential_type] = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                print(f"✗ Error compilando patrón {credential_type}: {e}")
        
        # Palabras clave sospechosas adicionales
        self.suspicious_keywords = [
            'password', 'passwd', 'pwd', 'secret', 'token', 'api_key',
            'apikey', 'access_key', 'private_key', 'auth', 'credential',
            'database_url', 'db_password', 'oauth', 'jwt'
        ]
        
        # Archivos sensibles que suelen contener credenciales
        self.sensitive_files = [
            '.env', '.env.local', '.env.production', 'config.json',
            'credentials.json', 'secrets.yml', 'secrets.yaml',
            'settings.py', 'config.py', 'application.properties',
            'docker-compose.yml', 'kubernetes.yml', '.aws/credentials'
        ]
    
    def detect_in_text(self, text, file_path=''):
        """
        Detecta credenciales en un texto
        
        Args:
            text (str): Texto a analizar
            file_path (str): Ruta del archivo analizado
            
        Returns:
            list: Lista de credenciales detectadas
        """
        detections = []
        for line_number, line in enumerate(text.split('\n'), start=1):
            detections.extend(self.detect_in_line(line.strip(), file_path, line_number))
        return detections

    def detect_in_commit_diff(self, diff_content, file_path=''):
        """
        Detecta credenciales en un diff de commit (solo líneas añadidas)

        Args:
            diff_content (str): Contenido del diff
            file_path (str): Ruta del archivo

        Returns:
            list: Lista de credenciales detectadas
        """
        detections = []
        for line_number, clean_line in self.iter_added_lines(diff_content):
            detections.extend(self.detect_in_line(clean_line, file_path, line_number))
        return detections

    def detect_in_line(self, line, file_path, line_number):
        """
        Aplica todos los patrones a una línea. Si varios patrones cubren el mismo
        fragmento (ej. 'db_password' y 'env_secret' sobre DB_PASSWORD=...), se conserva
        solo la coincidencia más larga para no contar dos veces el mismo secreto.
        """
        candidates = []
        for credential_type, pattern in self.compiled_patterns.items():
            for match in pattern.finditer(line):
                if not self._is_false_positive(match.group(), credential_type, file_path):
                    candidates.append((match.start(), match.end(), credential_type, match.group()))

        accepted = []
        # Primero los patrones específicos (AWS, GitHub...), luego los genéricos; a igualdad, el más largo
        priority = lambda c: (c[2] in GENERIC_TYPES, c[0] - c[1])
        for start, end, credential_type, text in sorted(candidates, key=priority):
            if any(start < a_end and a_start < end for a_start, a_end, _, _ in accepted):
                continue
            accepted.append((start, end, credential_type, text))

        return [{
            'type': credential_type,
            'file_path': file_path,
            'line_number': line_number,
            'pattern': text[:50],          # Limitar tamaño
            'secret': text,                # Valor completo (para fingerprint)
            'line_content': line[:500],    # Contexto (para el modelo ML)
            'severity': self._determine_severity(credential_type)
        } for start, end, credential_type, text in sorted(accepted)]

    @staticmethod
    def iter_added_lines(diff_content):
        """
        Recorre las líneas añadidas (+) de un diff unificado devolviendo el
        número de línea REAL en el archivo nuevo, calculado a partir de los
        encabezados de hunk "@@ -a,b +c,d @@".

        Args:
            diff_content (str): Contenido del diff (campo 'patch' de la API)

        Yields:
            tuple: (numero_linea_en_archivo, contenido_sin_prefijo)
        """
        current_line = None

        for line in diff_content.split('\n'):
            hunk = HUNK_HEADER.match(line)
            if hunk:
                current_line = int(hunk.group(1))
                continue

            if current_line is None or line.startswith('\\'):
                # Antes del primer hunk o "\ No newline at end of file"
                continue

            if line.startswith('+') and not line.startswith('+++'):
                yield current_line, line[1:].strip()
                current_line += 1
            elif line.startswith('-'):
                # Línea eliminada: no existe en el archivo nuevo
                continue
            else:
                # Línea de contexto (' ') presente en ambas versiones
                current_line += 1

    @staticmethod
    def normalize_file_path(file_path):
        """Estandariza una ruta: minúsculas, '/' como separador, sin './' inicial"""
        path = (file_path or '').strip().replace('\\', '/').lower()
        path = re.sub(r'/+', '/', path)
        while path.startswith('./'):
            path = path[2:]
        return path.lstrip('/')

    @staticmethod
    def normalize_secret(secret):
        """Limpia el valor detectado: espacios y comillas/caracteres residuales"""
        return (secret or '').strip().strip('\'"`;,').strip()

    def compute_fingerprint(self, repo_owner, repo_name, file_path, secret):
        """
        Genera el identificador único (SHA-256) de un hallazgo a partir del
        secreto detectado, la ruta del archivo y el repositorio de origen.
        Un mismo secreto en el mismo archivo y repositorio produce siempre el
        mismo fingerprint, aunque aparezca en otra línea o en otro commit.
        """
        repo_key = f"{repo_owner}/{repo_name}".strip().lower()
        raw = '\x1f'.join([
            repo_key,
            self.normalize_file_path(file_path),
            self.normalize_secret(secret),
        ])
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()
    
    def has_suspicious_keywords(self, text):
        """
        Verifica si el texto contiene palabras clave sospechosas
        
        Args:
            text (str): Texto a analizar
            
        Returns:
            bool: True si contiene palabras sospechosas
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.suspicious_keywords)
    
    def is_sensitive_file(self, file_path):
        """
        Verifica si un archivo es sensible (puede contener credenciales)
        
        Args:
            file_path (str): Ruta del archivo
            
        Returns:
            bool: True si es un archivo sensible
        """
        file_path_lower = file_path.lower()
        return any(sensitive in file_path_lower for sensitive in self.sensitive_files)
    
    def _is_false_positive(self, match_text, credential_type, file_path=''):
        """
        Determina si una coincidencia es un falso positivo
        
        Args:
            match_text (str): Texto que coincidió
            credential_type (str): Tipo de credencial
            file_path (str): Ruta del archivo
            
        Returns:
            bool: True si es falso positivo
        """
        # En <Pass>valor</Pass> se evalúa solo el valor (las etiquetas no son una plantilla)
        if credential_type == 'xml_password':
            match_text = re.sub(r'^<[^>]*>|<[^>]*>$', '', match_text)

        # Patrones de falsos positivos comunes
        false_positive_patterns = [
            r'example\.com',
            r'your[_-]?api[_-]?key',
            r'your[_-]?password',
            r'placeholder',
            r'dummy',
            r'test[_-]?key',
            r'fake[_-]?token',
            r'xxxxxxxx',
            r'\*\*\*\*\*',
            r'<.*>',  # Placeholders en XML/HTML
            r'\$\{.*\}',  # Variables de entorno
            r'\{\{.*\}\}',  # Plantillas
r'config\.',
            r'os\.environ',
            r'getenv',
            r'YOUR[_-]?[A-Z0-9]+', # Ej: YOUR_API_KEY
            r'<[A-Z0-9_]+>',      # Ej: <TOKEN>
            r'\[[A-Z0-9_]+\]',    # Ej: [PASSWORD]
            r'example[_-]?user',
            r'example[_-]?password',
r'mongodb\+srv',      # A menudo usado en ejemplos de Atlas
        ]
        
        match_lower = match_text.lower()
        
        for fp_pattern in false_positive_patterns:
            if re.search(fp_pattern, match_lower):
                return True
        
        # Ignorar si parece una llamada a función (ej. get_password(), os.getenv()).
        # define('DB_PASSWORD', '...') de PHP sí es una asignación literal
        if credential_type != 'php_define_secret' and re.search(r'\(.*\)', match_text):
            return True

        # Ignorar asignaciones a un atributo u otra variable (pwd = self.pwd, pass = user.password)
        if credential_type in ('db_password', 'db_user') and not re.search(r'[\'"]', match_text):
            value = re.split(r'[:=]+', match_text, maxsplit=1)[-1].strip().rstrip(');}')
            value = re.split(r'\(', value)[0]
            if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+', value):
                return True
            # Variables PHP ($input) y palabras reservadas (password = function / null / true)
            if value.startswith('$') or value.lower() in ('function', 'null', 'none', 'true', 'false',
                                                           'undefined', 'nil', 'new', 'await', 'this'):
                return True

        # Si el archivo es una documentación (.md), ser mucho más estricto
        if file_path.lower().endswith('.md'):
            # Ignorar si parece un ejemplo de URL con placeholders comunes
            if re.search(r'[:=].*([<\[{]|YOUR_|EXAMPLE)', match_text, re.IGNORECASE):
                return True
            # Ignorar si el valor parece una descripción de tipo y no un valor real
            if re.search(r'string|key|token|password|mypassword|admin|root', match_text, re.IGNORECASE) and len(match_text.split(':')[-1].strip()) < 15:
                # Si en un README dice "password: root", es casi seguro un ejemplo
                return True
        
        # Verificaciones adicionales por tipo
        if credential_type == 'password':
            # Intentar extraer solo el valor de la contraseña (después del separador)
            # Ejemplo: "password": "valor" -> extrae "valor"
            value_match = re.search(r'[:=\s\'"]+([^\s\'"{}[\],;]+)', match_text)
            if value_match:
                value = value_match.group(1).lower()
                # Si el valor en sí es muy corto o es una palabra de ejemplo
                if len(value) < 6 or value in ['password', 'passwd', 'mypassword', 'yourpassword', 'contraseña', 'secret', 'xxxx', '****', 'admin', 'root']:
                    return True
            else:
                # Si no se puede extraer el valor, aplicamos lógica básica sobre el texto completo
                if len(match_text) < 8:
                    return True
        
        return False
    
    def _determine_severity(self, credential_type):
        """
        Determina la severidad de una credencial detectada
        
        Args:
            credential_type (str): Tipo de credencial
            
        Returns:
            str: Nivel de severidad (CRITICAL, HIGH, MEDIUM)
        """
        critical_types = ['aws_access_key', 'aws_secret_key', 'private_key', 'stripe_key',
                          'connection_string', 'url_with_credentials', 'pgpass_entry']
        high_types = ['github_token', 'github_pat', 'github_oauth', 'google_api', 'heroku_api',
                      'slack_token', 'npm_auth', 'docker_auth', 'php_define_secret', 'password_hash']
        
        if credential_type in critical_types:
            return 'CRITICAL'
        elif credential_type in high_types:
            return 'HIGH'
        else:
            return 'MEDIUM'
    
    def analyze_file_content(self, file_content, file_path):
        """
        Análisis completo de un archivo
        
        Args:
            file_content (str): Contenido del archivo
            file_path (str): Ruta del archivo
            
        Returns:
            dict: Resultado del análisis
        """
        detections = self.detect_in_text(file_content, file_path)
        
        return {
            'has_credentials': len(detections) > 0,
            'credential_count': len(detections),
            'detections': detections,
            'has_suspicious_keywords': self.has_suspicious_keywords(file_content),
            'is_sensitive_file': self.is_sensitive_file(file_path)
        }
    
    def get_statistics(self, detections_list):
        """
        Obtiene estadísticas de detecciones
        
        Args:
            detections_list (list): Lista de todas las detecciones
            
        Returns:
            dict: Estadísticas
        """
        if not detections_list:
            return {
                'total': 0,
                'by_type': {},
                'by_severity': {},
                'unique_files': 0
            }
        
        by_type = {}
        by_severity = {}
        unique_files = set()
        
        for detection in detections_list:
            # Contar por tipo
            cred_type = detection['type']
            by_type[cred_type] = by_type.get(cred_type, 0) + 1
            
            # Contar por severidad
            severity = detection['severity']
            by_severity[severity] = by_severity.get(severity, 0) + 1
            
            # Archivos únicos
            unique_files.add(detection['file_path'])
        
        return {
            'total': len(detections_list),
            'by_type': by_type,
            'by_severity': by_severity,
            'unique_files': len(unique_files)
        }


# Instancia global del detector
credential_detector = CredentialDetector()