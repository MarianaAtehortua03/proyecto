"""
Evaluación de CyberGuard contra el benchmark público Plazmaz/leaky-repo.

Metodología (la misma de .leaky-meta/benchmark.py del benchmark, con la que se
publicaron los resultados de Gitleaks, TruffleHog y detect-secrets):
  - Por archivo: encontrados vs esperados (risk + informative de secrets.csv).
  - Encontrados válidos = min(encontrados, esperados); FP = max(encontrados - esperados, 0).

Conjunto de prueba separado: leaky-repo NUNCA se usa para entrenar. El modelo se
entrena solo con el conjunto semilla sintético y con los hallazgos etiquetados de
otras aplicaciones vulnerables (models/training_data/).

Uso:
    python scripts/benchmark_leaky_repo.py
"""
import csv
import io
import os
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
warnings.filterwarnings('ignore')

import pandas as pd
import requests

from config.config import GITHUB_TOKEN
from utils.github_api import github_analyzer
from utils.credential_detector import credential_detector
from models.credential_classifier import CredentialClassifier, LABELED_APPS_DATASET

OWNER, REPO, BRANCH = 'Plazmaz', 'leaky-repo', 'master'
PUBLISHED = [  # (herramienta, encontrados, archivos cubiertos, falsos positivos) sobre 175 / 44
    ('Gitleaks', 127, 40, 17),
    ('detect-secrets', 41, 23, 0),
    ('TruffleHog', 40, 23, 43),
]
REPORT = os.path.join(ROOT, 'scripts', 'benchmark_leaky_repo_resultados.csv')


def load_ground_truth():
    headers = {'Authorization': f'Bearer {GITHUB_TOKEN}', 'Accept': 'application/vnd.github.raw'}
    url = f'https://api.github.com/repos/{OWNER}/{REPO}/contents/.leaky-meta/secrets.csv'
    raw = requests.get(url, headers=headers, timeout=30).text
    rows = csv.reader(l for l in io.StringIO(raw) if l.strip() and not l.startswith('#'))
    return {r[0]: (int(r[1]), int(r[2])) for r in rows}


def scan_repository():
    """Recorre todos los commits y devuelve hallazgos únicos (por fingerprint)"""
    findings = {}
    for commit in github_analyzer.get_commits(OWNER, REPO, BRANCH, max_commits=500):
        details = github_analyzer.get_commit_details(OWNER, REPO, commit['sha'])
        for file_data in (details or {}).get('files', []):
            for det in credential_detector.detect_in_commit_diff(file_data.get('patch', ''), file_data['filename']):
                fp = credential_detector.compute_fingerprint(OWNER, REPO, det['file_path'], det['secret'])
                findings.setdefault(fp, det)
    return pd.DataFrame([{
        'credential_type': d['type'], 'matched_pattern': d['pattern'], 'file_path': d['file_path'],
        'line_number': d['line_number'], 'line_content': d['line_content'],
    } for d in findings.values()])


def score(counts, expected, expected_of):
    found = fp = covered = 0
    for name in expected:
        n, exp = counts.get(name, 0), expected_of(name)
        found += min(n, exp)
        fp += max(n - exp, 0)
        covered += int(n > 0)
    return found, sum(expected_of(n) for n in expected), fp, covered


def main():
    expected = load_ground_truth()
    print(f'Verdad conocida: {sum(map(sum, expected.values()))} secretos en {len(expected)} archivos')

    findings = scan_repository()
    findings = findings[~findings['file_path'].str.startswith('.leaky-meta/')]  # metadatos del benchmark
    print(f'Hallazgos únicos de CyberGuard: {len(findings)}')

    # Modelo entrenado SIN leaky-repo
    model = CredentialClassifier()
    metrics = model.train_default()
    print(f"Entrenamiento: {metrics['total_samples']} ejemplos "
          f"({metrics['total_samples'] - metrics['apps_samples']} semilla + {metrics['apps_samples']} apps vulnerables); "
          f"F1 en su propio conjunto de prueba: {metrics['f1']:.3f}\n")

    predictions, confidence = model.predict(findings)
    findings['ml_prediction'] = predictions
    findings['ml_confidence'] = confidence.round(3)
    findings['in_benchmark_file'] = findings['file_path'].isin(expected)
    findings.to_csv(REPORT, index=False, encoding='utf-8')

    regex_counts = findings.groupby('file_path').size().to_dict()
    ml_counts = findings[findings.ml_prediction == 1].groupby('file_path').size().to_dict()

    total = sum(map(sum, expected.values()))
    print(f'{"Herramienta":26s} {"Encontrados":>12s} {"Cobertura":>10s} {"Archivos":>9s} {"FP":>5s}')
    for name, counts in [('CyberGuard (solo regex)', regex_counts), ('CyberGuard (regex + ML)', ml_counts)]:
        f, t, fp, cov = score(counts, expected, lambda k: sum(expected[k]))
        print(f'{name:26s} {f:>5d}/{t:<6d} {f / t:>9.1%} {cov:>4d}/{len(expected):<4d} {fp:>5d}')
    for name, f, cov, fp in PUBLISHED:
        print(f'{name + " (publicado)":26s} {f:>5d}/{total:<6d} {f / total:>9.1%} {cov:>4d}/{len(expected):<4d} {fp:>5d}')

    # Desempeño del modelo hallazgo por hallazgo: los archivos listados en el benchmark
    # contienen secretos (positivos); los demás archivos del repo no (negativos)
    y_true = findings['in_benchmark_file'].astype(int)
    y_pred = findings['ml_prediction'].astype(int)
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    print(f'\nModelo ML sobre los {len(findings)} hallazgos de regex (conjunto de prueba no visto):')
    print(f'  Verdaderos positivos {tp} · Falsos negativos {fn} · Falsos positivos {fp} · Verdaderos negativos {tn}')
    if tp + fp:
        print(f'  Precision {tp / (tp + fp):.3f}', end='')
    if tp + fn:
        print(f' · Recall {tp / (tp + fn):.3f}')

    print('\nCredenciales descartadas por el modelo en archivos con secretos:')
    for _, r in findings[(findings.in_benchmark_file) & (findings.ml_prediction == 0)].iterrows():
        print(f'  {r.file_path}:{r.line_number} [{r.credential_type}] {str(r.line_content)[:80]}')
    print(f'\nDetalle guardado en {REPORT}')


if __name__ == '__main__':
    main()
