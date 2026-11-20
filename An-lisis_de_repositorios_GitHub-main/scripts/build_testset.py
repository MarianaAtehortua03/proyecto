"""
Construye el conjunto de PRUEBA para medir la precisión del modelo (descarte de
falsos positivos). Escanea repositorios que NO se usan para entrenar y guarda
los hallazgos de las regex SIN predicción del modelo, para etiquetarlos a ciegas.

Salida: models/test_data/testset_findings.csv  (columna manual_label vacía)

Uso:
    python scripts/build_testset.py
"""
import os
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
warnings.filterwarnings('ignore')

import pandas as pd
from utils.github_api import github_analyzer
from utils.credential_detector import credential_detector

# (dueño, repositorio, rama, máximo de commits)
TEST_REPOS = [
    ('awslabs', 'git-secrets', 'master', 150),
    ('OWASP', 'NodeGoat', 'master', 250),
    ('docker', 'awesome-compose', 'master', 300),
    ('cr0hn', 'vulnerable-node', 'master', 60),
    ('we45', 'Vulnerable-Flask-App', 'master', 40),
    ('gitleaks', 'gitleaks', 'master', 150),
    ('getsentry', 'self-hosted', 'master', 150),
]
OUTPUT = os.path.join(ROOT, 'models', 'test_data', 'testset_findings.csv')


def scan(owner, repo, branch, limit):
    findings = {}
    for commit in github_analyzer.get_commits(owner, repo, branch, limit):
        details = github_analyzer.get_commit_details(owner, repo, commit['sha'])
        for file_data in (details or {}).get('files', []):
            for det in credential_detector.detect_in_commit_diff(file_data.get('patch', ''), file_data['filename']):
                fp = credential_detector.compute_fingerprint(owner, repo, det['file_path'], det['secret'])
                findings.setdefault(fp, {
                    'fingerprint': fp, 'repo': f'{owner}/{repo}', 'commit_sha': commit['sha'][:7],
                    'credential_type': det['type'], 'file_path': det['file_path'],
                    'line_number': det['line_number'], 'matched_pattern': det['pattern'],
                    'line_content': det['line_content'],
                })
    return list(findings.values())


def main():
    rows = []
    for owner, repo, branch, limit in TEST_REPOS:
        found = scan(owner, repo, branch, limit)
        print(f'{owner}/{repo}: {len(found)} hallazgos únicos', flush=True)
        rows += found
    df = pd.DataFrame(rows)
    df['manual_label'] = ''
    df['note'] = ''
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    df.to_csv(OUTPUT, index=False, encoding='utf-8')
    print(f'\n{len(df)} hallazgos -> {OUTPUT}')


if __name__ == '__main__':
    main()
