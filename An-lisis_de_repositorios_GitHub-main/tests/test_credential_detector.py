"""
Pruebas del detector regex: formatos que debe encontrar, falsos positivos que
debe descartar, numeración de líneas del diff y fingerprinting.

Ejecutar:
    python -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.credential_detector import credential_detector as detector


def types_in(line, file_path='config.txt'):
    return [d['type'] for d in detector.detect_in_text(line, file_path)]


class TestPatronesDetectados(unittest.TestCase):
    """Cada línea debe producir exactamente el tipo indicado"""

    CASES = [
        ('aws_access_key', 'aws_access_key_id = AKIAQYLPMN5HHHFPZAM2', 'cloud/.credentials'),
        ('aws_secret_key', 'aws_secret_access_key = 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', 'cloud/.credentials'),
        ('db_password', 'password = "hunter22"', 'settings.py'),
        ('db_password', '"userPassword" : "mongopass",', 'db/robomongo.json'),
        ('env_secret', 'export GMAIL_PASSWORD=Pass!12345', '.bashrc'),
        ('env_secret', 'REDIS_PASSWORD=r3d1sPa55', '.env'),
        ('php_define_secret', "define('DB_PASSWORD', 'wp_s3cr3t_pw');", 'wp-config.php'),
        ('xml_password', '<Pass encoding="base64">c2VjcmV0cGFzcw==</Pass>', 'filezilla.xml'),
        ('npm_auth', '_authToken=npm_Zx8Kq2LmN4vB7rT1yW9eA3sD6fG0hJ5', '.npmrc'),
        ('docker_auth', '"auth": "dXNlcjpzM2NyM3RwYXNz",', '.docker/config.json'),
        ('netrc_password', 'machine smtp.example.org login mailer password m4ilP4ss', '.netrc'),
        ('pgpass_entry', 'db.internal:5432:app:app_user:Pg_s3cret!', 'db/.pgpass'),
        ('password_hash', 'admin:$apr1$Zx8Kq2Lm$N4vB7rT1yW9eA3sD6fG0h.', '.htpasswd'),
        ('url_with_credentials', 'url = ftp://deploy:Ftp_pa55@files.example.net/www', 'deploy.cfg'),
        ('connection_string', 'MONGO=mongodb://app:M0ngoPw@cluster0.example.net:27017/app', 'docker-compose.yml'),
        ('private_key', '-----BEGIN PRIVATE KEY-----', 'misc-keys/cert-key.pem'),
        ('private_key', '-----BEGIN OPENSSH PRIVATE KEY-----', '.ssh/id_ed25519'),
        ('generic_secret', "SECRET_KEY = 'django-insecure-zx8kq2lmn4vb7rt1yw9e'", 'web/django/settings.py'),
        ('generic_token', 'oauth_token: 4f9e2b7c1d8a6f3e5b0c9d2a7e1f4b8c', 'hub'),
        ('github_token', 'token = "ghp_Zx8Kq2LmN4vB7rT1yW9eA3sD6fG0hJ5kL8pQ"', 'deploy.sh'),
    ]

    def test_patrones(self):
        for expected, line, path in self.CASES:
            with self.subTest(line=line):
                self.assertEqual(types_in(line, path), [expected])


class TestFalsosPositivosDescartados(unittest.TestCase):
    """El filtro de reglas debe descartar estos casos (el resto lo decide el modelo ML)"""

    CASES = [
        ('password = user.password', 'app/models.py'),
        ('pwd = self.settings.pwd', 'app/db.py'),
        ('password = os.getenv("DB_PASSWORD")', 'settings.py'),
        ('api_key = "${API_KEY}"', 'config.yml'),
        ('password = "{{ vault_db_password }}"', 'ansible/vars.yml'),
    ]

    def test_descartados(self):
        for line, path in self.CASES:
            with self.subTest(line=line):
                self.assertEqual(types_in(line, path), [])


class TestSolapamiento(unittest.TestCase):

    def test_un_hallazgo_por_fragmento(self):
        # db_password y env_secret cubren el mismo texto: solo debe quedar uno
        self.assertEqual(len(types_in('DB_PASSWORD=Sup3rS3cret!', '.env')), 1)


class TestNumeracionDiff(unittest.TestCase):

    def test_lineas_reales(self):
        patch = '\n'.join([
            '@@ -10,4 +10,6 @@ def foo():',
            ' linea10',
            '-borrada',
            '+AWS_KEY = "AKIAQ7XK2M9PLRT4WZ3N"',
            ' linea12',
            '+token = "ghp_Zx8Kq2LmN4vB7rT1yW9eA3sD6fG0hJ5kL8pQ"',
            '@@ -40,2 +42,3 @@',
            ' ctx42',
            '+password = "hunter22"',
        ])
        found = [(d['type'], d['line_number']) for d in detector.detect_in_commit_diff(patch, 'app.py')]
        self.assertEqual(found, [('aws_access_key', 11), ('github_token', 13), ('db_password', 43)])


class TestFingerprint(unittest.TestCase):

    def test_normalizacion(self):
        a = detector.compute_fingerprint('Owner', 'Repo', r'./SRC\app.py', '"AKIA123"')
        b = detector.compute_fingerprint('owner', 'repo', 'src/app.py', 'AKIA123')
        self.assertEqual(a, b)

    def test_repos_distintos(self):
        a = detector.compute_fingerprint('a', 'repo', 'x.py', 'secret')
        b = detector.compute_fingerprint('b', 'repo', 'x.py', 'secret')
        self.assertNotEqual(a, b)


if __name__ == '__main__':
    unittest.main()
