"""
Genera el conjunto de entrenamiento semilla (seed_credentials.csv) con el que
el clasificador de hallazgos viene entrenado de fábrica.

Criterio de etiquetado:
  1 = credencial real: un valor LITERAL asignado a un campo de credencial en un
      archivo de configuración, código o dotfile, aunque la contraseña sea débil
      (hunter22, swordfish...). Las contraseñas débiles son de las fugas más comunes.
  0 = falso positivo: solo cuando hay una señal clara de que no es un secreto:
      placeholders (changeme, your_password, ${VAR}), valores de ejemplo conocidos
      (AKIAIOSFODNN7EXAMPLE, token de jwt.io), valores secuenciales/de relleno,
      etiquetas y atributos HTML, código que lee otra variable, prosa de documentación
      y valores marcados como ejemplo en docs/pruebas.

Las líneas se pasan por el MISMO detector regex de la aplicación, de modo que
las filas tienen exactamente el formato que el modelo verá en producción.
Los secretos son cadenas generadas aquí: no corresponden a credenciales reales.

Uso:
    python models/training_data/build_seed_dataset.py
"""
import base64
import csv
import os
import random
import string
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(ROOT)
from utils.credential_detector import credential_detector

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seed_credentials.csv')
VARIANTS = 10  # Variantes aleatorias por plantilla

rng = random.Random(42)
UPPER_DIGITS = string.ascii_uppercase + string.digits
ALNUM = string.ascii_letters + string.digits
B64 = ALNUM + '+/'
URLSAFE = ALNUM + '-_'
HEX = '0123456789abcdef'
WORDS = ['hunter', 'swordfish', 'dragon', 'monkey', 'sunshine', 'letmein', 'qwerty', 'trustno',
         'shadow', 'master', 'welcome', 'football', 'princess', 'mongo', 'redis', 'batman',
         'becareful', 'deployer', 'summer', 'winter', 'castle', 'tigre', 'medellin', 'colombia']
HOSTS = ['db.internal', 'prod-db.acme.io', 'mysql01', '10.0.3.12', 'ftp.files.net', 'smtp.mailhost.org']
USERS = ['admin', 'deploy', 'app_user', 'backup', 'jenkins', 'root', 'webmaster']


def rand(chars, n):
    return ''.join(rng.choice(chars) for _ in range(n))


def weak_password():
    """Contraseña débil pero real: palabra + sufijo (hunter22, Swordfish!23, Pass!12345...)"""
    word = rng.choice(WORDS)
    if rng.random() < 0.4:
        word = word.capitalize()
    return word + rng.choice(['1', '22', '123', '!23', '2024', '!', '#1', '99', '!12345', '007'])


def strong_password():
    pwd = [rng.choice(string.ascii_uppercase), rng.choice(string.ascii_lowercase),
           rng.choice(string.digits), rng.choice('!@#%&*_-')]
    pwd += [rng.choice(ALNUM + '!@#%&*_-') for _ in range(rng.randint(8, 16))]
    rng.shuffle(pwd)
    return ''.join(pwd)


def any_password():
    return weak_password() if rng.random() < 0.5 else strong_password()


def b64(text):
    return base64.b64encode(text.encode()).decode()


def jwt():
    return f"eyJ{rand(URLSAFE, 30)}.eyJ{rand(URLSAFE, 60)}.{rand(URLSAFE, 43)}"


CONFIG_FILES = ['.env', '.env.production', 'config/settings.py', 'src/config.js', 'deploy.sh',
                'docker-compose.yml', 'app/config.yml', 'k8s/secrets.yaml', 'terraform/main.tf',
                'src/main/resources/application.properties', 'scripts/backup.py', 'server/index.js',
                'Dockerfile', 'config.json', 'backend/app/database.py', 'src/services/payments.ts',
                'src/main/java/com/acme/DbConfig.java', 'app/Http/Controllers/AuthController.php']
DOTFILES = ['.bashrc', '.bash_profile', '.zshrc', 'home/dev/.profile']
DOC_FILES = ['README.md', 'docs/setup.md', 'docs/api.md', 'CONTRIBUTING.md', 'docs/install-macos.md',
             'wiki/configuracion.md', 'docs/challenges/explanation.adoc']
TEST_FILES = ['tests/test_auth.py', 'test/config.test.js', 'examples/config.example.yml',
              '.env.example', 'src/__mocks__/api.js', 'fixtures/users.json', 'spec/payments_spec.rb',
              'samples/demo_settings.py']
CODE_FILES = ['src/components/LoginForm.jsx', 'frontend/src/pages/LoginPage.jsx', 'app/models/user.py',
              'src/routes/auth.js', 'backend/controllers/userController.js', 'app/forms.py',
              'views/login.ejs', 'src/main/resources/templates/register.html']


def one(*items):
    return lambda: rng.choice(items)


# ---------------------------------------------------------------------------
# Credenciales reales: (plantilla de línea, archivos posibles)
# ---------------------------------------------------------------------------
REAL_TEMPLATES = [
    # Tokens de proveedor con formato real y valor aleatorio
    (lambda: f'AWS_ACCESS_KEY_ID=AKIA{rand(UPPER_DIGITS, 16)}', CONFIG_FILES + DOTFILES),
    (lambda: f'aws_access_key_id = AKIA{rand(UPPER_DIGITS, 16)}', ['.aws/credentials', 'cloud/credentials']),
    (lambda: f'aws_secret_access_key = {rand(B64, 40)}', ['.aws/credentials', 'cloud/credentials', '.s3cfg']),
    (lambda: f'GITHUB_TOKEN=ghp_{rand(ALNUM, 36)}', CONFIG_FILES + DOTFILES),
    (lambda: f'echo "KEY: github_pat_{rand(ALNUM, 22)}_{rand(ALNUM, 59)}"', ['.github/workflows/deploy.yml', 'ci/release.sh']),
    (lambda: f'SLACK_BOT_TOKEN=xoxb-{rand(string.digits, 12)}-{rand(string.digits, 12)}-{rand(ALNUM, 24)}', CONFIG_FILES),
    (lambda: f'STRIPE_SECRET_KEY=sk_live_{rand(ALNUM, 24)}', CONFIG_FILES),
    (lambda: f'const mapsKey = "AIza{rand(URLSAFE, 35)}";', CONFIG_FILES),
    (lambda: f'_authToken=npm_{rand(ALNUM, 36)}', ['.npmrc', 'frontend/.npmrc']),
    (lambda: f'"auth": "{b64(rng.choice(USERS) + ":" + any_password())}",', ['.docker/config.json', '.dockercfg']),
    (lambda: f'oauth_token: {rand(HEX, 40)}', ['.config/hub', 'config/hub.yml']),
    (lambda: f'access_token: {rand(HEX, 64)}', ['.tugboat', 'config/do.yml']),
    (lambda: f'SECRET_KEY = "django-insecure-{rand(ALNUM + "!@#%^&*(-_=+)", 40)}"', ['config/settings.py', 'web/settings.py']),
    (lambda: f'secret_key_base: {rand(HEX, 64)}', ['config/secrets.yml']),
    (lambda: f'api_key: {rand(ALNUM, 32)}', CONFIG_FILES),
    (lambda: f'JWT_TOKEN={jwt()}', CONFIG_FILES),
    (lambda: f'curl -H "Authorization: Bearer {rand(ALNUM, 40)}" https://api.{rand(string.ascii_lowercase, 7)}.com', CONFIG_FILES + DOTFILES),
    (lambda: rng.choice(['-----BEGIN RSA PRIVATE KEY-----', '-----BEGIN PRIVATE KEY-----',
                         '-----BEGIN OPENSSH PRIVATE KEY-----', '-----BEGIN EC PRIVATE KEY-----']),
     ['id_rsa', 'keys/server.pem', 'deploy/key.pem', '.ssh/id_ed25519', 'certs/tls.key']),
    # Contraseñas literales (débiles o fuertes) en configuración y código
    (lambda: f'password = "{any_password()}"', CONFIG_FILES),
    (lambda: f'"password": "{any_password()}",', CONFIG_FILES + ['.vscode/sftp.json', 'deploy/sftp-config.json']),
    (lambda: f'"userPassword" : "{weak_password()}",', ['db/robomongo.json', 'config/mongo.json']),
    (lambda: f'DB_PASSWORD={any_password()}', CONFIG_FILES),
    (lambda: f'export {rng.choice(["GMAIL", "SMTP", "MYSQL", "REDIS"])}_PASSWORD="{any_password()}"', DOTFILES),
    (lambda: f"define('DB_PASSWORD', '{any_password()}');", ['wordpress/wp-config.php', 'config/database.php']),
    (lambda: f'static final String ADMIN_PASSWORD = "{weak_password()}";', ['src/main/java/com/acme/AuthService.java']),
    (lambda: f'if ($username == "{rng.choice(USERS)}" && $password == "{weak_password()}") {{', ['src/LoginController.php', 'login.php']),
    (lambda: f'<fileTransfer host="{rng.choice(HOSTS)}" port="21" password="{rand(HEX, 32)}" />', ['.idea/WebServers.xml']),
    (lambda: f'<Pass encoding="base64">{b64(any_password())}</Pass>', ['filezilla/sitemanager.xml', 'filezilla/recentservers.xml']),
    (lambda: f'machine {rng.choice(HOSTS)} login {rng.choice(USERS)} password {any_password()}', ['.netrc', 'home/dev/.netrc']),
    (lambda: f'{rng.choice(HOSTS)}:5432:app:{rng.choice(USERS)}:{any_password()}', ['.pgpass', 'db/.pgpass']),
    (lambda: f'url = ftp://{rng.choice(USERS)}:{weak_password()}@{rng.choice(HOSTS)}/www', ['deploy.cfg', 'scripts/upload.ini']),
    (lambda: f'DATABASE_URL=postgresql://{rng.choice(USERS)}:{rand(ALNUM, 14)}@{rng.choice(HOSTS)}:5432/prod', CONFIG_FILES),
    (lambda: f'MONGO_URI=mongodb://{rng.choice(USERS)}:{weak_password()}@cluster0.{rand(string.ascii_lowercase, 6)}.net:27017/app', CONFIG_FILES),
    (lambda: f'{rng.choice(USERS)}:$apr1${rand(ALNUM, 8)}${rand(ALNUM + "./", 22)}', ['.htpasswd', 'etc/shadow']),
    (lambda: f"INSERT INTO users VALUES (1,'{rng.choice(USERS)}','$2y$10${rand(ALNUM + './', 53)}');", ['db/dump.sql', 'backup/users.sql']),
    (lambda: f'"encryptedPassword": "MDoEEPgAAAAAAAAAAAAAAAAAAAEwFAYIKoZIhvcNAwcE{rand(B64, 30)}",', ['.mozilla/firefox/logins.json']),
    # Secretos ofuscados por concatenación (siguen siendo secretos en el código)
    (lambda: f'var password = "{rand(B64, 7)}=" + {rng.randint(1, 9)} + "{rand(ALNUM, 4)}" + {rng.randint(1, 9)} + "{rand(B64, 3)}=";', ['js/index.js', 'static/app.js']),
    (lambda: f'export tempPassword="{rand(B64, 43)}="', ['.github/scripts/.bash_history', 'scripts/setup.sh']),
]

# ---------------------------------------------------------------------------
# Falsos positivos
# ---------------------------------------------------------------------------
FP_TEMPLATES = [
    # Valores de ejemplo oficiales o secuenciales
    (one('AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE', 'echo "Using Access Key: AKIAIOSFODNN7EXAMPLE"'), CONFIG_FILES + DOC_FILES),
    (one('aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'), CONFIG_FILES + DOC_FILES),
    (one('GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz', 'token = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"'), CONFIG_FILES),
    (one('SECRET = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"', 'secret: "1234567890abcdef1234567890abcdef"'), CONFIG_FILES),
    (one('MAILGUN_API_KEY=key-abcdefghijklmnopqrstuvwxyz123456', 'STRIPE_SECRET_KEY=sk_live_000000000000000000000000'), CONFIG_FILES),
    (one('SLACK_BOT_TOKEN=xoxb-123456789012-ABCDEFGHIJKLMNOPQRSTUVWX', 'api_key = "abcdefghijklmnop1234"'), CONFIG_FILES),
    (one('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'), CONFIG_FILES + DOC_FILES),
    # Placeholders explícitos
    (one('password = "changeme"', 'password: changeme123', 'DB_PASSWORD=your_password_here', '"password": "********",',
         'password = "xxxxxxxx"', 'DB_PASSWORD=<password>', 'password: "REPLACE_ME"', 'export DB_PASSWORD=your-db-password'),
     CONFIG_FILES + TEST_FILES),
    (one('api_key: YOUR_API_KEY', 'api_key: insert_api_key_here', 'SECRET_KEY = "replace-me-in-production"',
         'access_token: your_access_token_here', 'GITHUB_TOKEN=<your-token>'), CONFIG_FILES + DOC_FILES),
    (one('DATABASE_URL=postgresql://user:password@host:5432/dbname', 'mongodb://username:password@example-cluster.net:27017/test',
         'ftp://user:pass@example.org/path'), DOC_FILES + TEST_FILES),
    (one('curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"', 'Authorization: Bearer <token>'), DOC_FILES),
    # Etiquetas HTML y código que no contiene el secreto
    (one('<input type="password" className="form-input" />', '<input class="form-control" id="password" name="password" type="password" placeholder="Password">',
         '<label class="control-label" for="login_password">Password </label>',
         '<label for="register_password">Password</label>'), CODE_FILES),
    (one('"password": password_hash,', 'password = request.form.get("password")', 'password: { type: String, required: true },',
         'const [password, setPassword] = useState("");', 'if (password !== confirmPassword) setError("passwordMismatch");',
         'password = form.passwordField', 'secret = settings.SECRET_KEY_FROM_VAULT',
         'this.password = credentials.password;', 'db_password = config.database.password'), CODE_FILES),
    # Prosa de documentación
    (one('Use bearer tokens or workload identity federation instead.', 'The password field accepts passphrases longer than twelve characters.',
         'Pass the api_key parameter with every request to the endpoint.', 'Store your access_token in a secret manager, never in the repo.'),
     DOC_FILES),
    # Valores aleatorios marcados como ejemplo en docs y pruebas
    (lambda: f'Ejemplo: GITHUB_TOKEN=ghp_{rand(ALNUM, 36)}', DOC_FILES),
    (lambda: f'export AWS_ACCESS_KEY_ID=AKIA{rand(UPPER_DIGITS, 16)}  # example', DOC_FILES),
    (lambda: f'api_key: {rand(ALNUM, 32)}  # sample value', DOC_FILES + TEST_FILES),
    (lambda: f'password = "test_{rand(ALNUM, 10)}"', TEST_FILES),
    (lambda: f'SECRET_KEY = "test-{rand(ALNUM, 24)}"', TEST_FILES),
    (lambda: f'JWT_TOKEN={jwt()}  # dummy token for tests', TEST_FILES),
]


def detect(line, file_path, label, source):
    """Pasa la línea por el detector de la app y devuelve las filas resultantes"""
    return [{
        'credential_type': det['type'],
        'matched_pattern': det['pattern'],
        'file_path': file_path,
        'line_content': det['line_content'],
        'manual_label': label,
        'source': source,
    } for det in credential_detector.detect_in_text(line, file_path)]


def build():
    rows = []
    for template, files in REAL_TEMPLATES:
        for _ in range(VARIANTS):
            rows += detect(template(), rng.choice(files), 1, 'real')
    # Más variantes de falsos positivos: muchas plantillas son constantes y solo varía el archivo
    for template, files in FP_TEMPLATES:
        for _ in range(VARIANTS * 3):
            rows += detect(template(), rng.choice(files), 0, 'falso_positivo')

    # Eliminar duplicados exactos
    unique = {(r['credential_type'], r['matched_pattern'], r['file_path']): r for r in rows}
    rows = list(unique.values())
    rng.shuffle(rows)

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    real = sum(r['manual_label'] == 1 for r in rows)
    print(f'[OK] {len(rows)} ejemplos -> {OUTPUT}')
    print(f'     {real} credenciales reales / {len(rows) - real} falsos positivos')
    return rows


if __name__ == '__main__':
    build()
