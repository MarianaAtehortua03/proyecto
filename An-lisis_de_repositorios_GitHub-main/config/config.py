import os
from dotenv import load_dotenv


load_dotenv()

# Configuracion de Base de Datos PostgreSQL
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'github_analyzer'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', "miContraseña123")
}
# Configuracion de GitHub API
# NOTE: do not hardcode the token. Store it in an environment variable or .env file.
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')

# Configuracion de Machine Learning
ML_CONFIG = {
    'test_size': 0.2,          # 80% entrenamiento / 20% prueba
    'random_state': 42,
    'max_depth': 10,
    'min_samples_split': 5,
    'criterion': 'gini'
}

# Patrones regex para deteccion de credenciales
CREDENTIAL_PATTERNS = {
    'aws_access_key': r'AKIA[0-9A-Z]{16}',
    'aws_secret_key': r'aws(.{0,20})?[\'"\s:=]+[0-9a-zA-Z\/+]{40}(?![0-9a-zA-Z\/+])',
    'github_token': r'gh[pousr]_[0-9a-zA-Z]{36}',
    'github_pat': r'github_pat_[0-9a-zA-Z_]{82}',
    'github_oauth': r'gho_[0-9a-zA-Z]{36}',
    # Contraseñas en asignaciones (password=, "userPassword": ..., pwd: ...). Mínimo 6 caracteres:
    # las contraseñas débiles también son fugas reales; el modelo ML filtra los ejemplos
    'db_password': r'(?:password|passwd|pwd|db_pass|db_password)[\'"\s]*[:=]+\s*[\'"]?[^\s\'"{}[\],;<>]{6,}',
    'db_user': r'(?:db_user|db_username|database_user)[\'"\s:=]+[\'"][^\s\'"]{5,}[\'"]',
    'connection_string': r'(?:mongodb|mysql|postgresql|sqlserver|postgres|mssql|oracle|sqlite|redis|amqp):\/\/[^\s\'"{}]+:[^\s\'"{}]+@[^\s\'"]+',
    # Cualquier URL con usuario:contraseña (ftp://, https://, smtp://, ...)
    'url_with_credentials': r'[a-z][a-z0-9+.-]{2,}:\/\/[^\s:\/@\'"]+:[^\s:\/@\'"]{3,}@[^\s\'"]+',
    'generic_api_key': r'api[_-]?key[\'"\s:=]+[0-9a-zA-Z\-_]{12,}',
    'generic_secret': r'secret(?:[_-]?(?:key|token|access[_-]?key)(?:[_-]?base)?)?[\'"\s]*[:=]+\s*[\'"]?[^\s\'"{}[\],;<>]{12,}',
    'generic_token': r'(?:access|auth|api|oauth|refresh)[_-]?token[\'"\s]*[:=]+\s*[\'"]?[0-9a-zA-Z\-._~+\/]{16,}',
    # Variables de entorno: DB_PASSWORD=..., export SMTP_SECRET=..., GITHUB_TOKEN=...
    # (?-i:...) = distingue mayúsculas: solo nombres de variable en MAYÚSCULAS
    'env_secret': r'(?-i:^\s*(?:export\s+)?[A-Z][A-Z0-9_]*(?:PASSWORD|PASSWD|PWD|SECRET|TOKEN|API_KEY|APIKEY|ACCESS_KEY|AUTH)[A-Z0-9_]*\s*=\s*[\'"]?[^\s\'"#]{4,})',
    # PHP: define('DB_PASSWORD', '...'); define('AUTH_KEY', '...')
    'php_define_secret': r'define\(\s*[\'"][A-Z_]*(?:PASSWORD|SECRET|KEY|SALT|TOKEN)[A-Z_]*[\'"]\s*,\s*[\'"][^\'"]{4,}[\'"]',
    # Atributos y etiquetas XML: password="...", <Pass>...</Pass>
    'xml_password': r'<(?:pass|password)\b[^>]*>[^<]{4,}<\/(?:pass|password)>',
    # npm (.npmrc) y Docker (.dockercfg / config.json)
    'npm_auth': r'_auth(?:Token)?\s*=\s*[^\s]{8,}',
    'docker_auth': r'"auth"\s*:\s*"[A-Za-z0-9+\/=]{8,}"',
    # .netrc ("machine x login y password z") y .pgpass ("host:puerto:bd:usuario:clave")
    'netrc_password': r'(?:\b(?:machine|login)\s+\S+.*\bpassword\s+[^\s=:]{4,}\s*$|^\s*(?:password|passwd)\s+[^\s=:]{4,}\s*$)',
    'pgpass_entry': r'^[^\s:#]+:(?:\d+|\*):[^\s:]+:[^\s:]+:[^\s:]{4,}$',
    # Hashes de contraseñas (htpasswd, /etc/shadow, volcados SQL)
    'password_hash': r'\$(?:2[abxy]?|apr1|1|5|6)\$[^\s:\'",]{8,}',
    'private_key': r'-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY(?: BLOCK)?-----',
    'slack_token': r'xox[baprs]-[0-9a-zA-Z]{10,48}',
    'stripe_key': r'sk_live_[0-9a-zA-Z]{24}',
    'google_api': r'AIza[0-9A-Za-z\\-_]{35}',
    'heroku_api': r'[h|H][e|E][r|R][o|O][k|K][u|U].{0,30}[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}',
    'mailgun_api': r'key-[0-9a-zA-Z]{32}',
    'jwt_token': r'eyJ[0-9a-zA-Z_-]*\.eyJ[0-9a-zA-Z_-]*\.[0-9a-zA-Z_-]*',
    'bearer_token': r'Bearer\s+[0-9a-zA-Z\-._~+\/]+=*'
}

# Configuracion de GUI
GUI_CONFIG = {
    'window_title': 'GitHub Repository Analyzer - ML',
    'window_size': '1400x800',
    'theme': 'clam'
}
