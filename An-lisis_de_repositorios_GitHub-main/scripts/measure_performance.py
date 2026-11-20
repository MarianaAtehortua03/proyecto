"""
Mide la eficiencia de CyberGuard: tiempo de cada etapa del análisis y de cada modelo.

  - API de GitHub: descarga de commits y diffs (Plazmaz/leaky-repo, 25 commits).
  - Detector regex y fingerprint sobre esos diffs.
  - Entrenamiento de CART y Random Forest; predicción por hallazgo.
  - Isolation Forest (commits de la base) y K-Means (repositorios de la base).

Cada medición se repite varias veces y se informa el promedio.

Uso:
    python scripts/measure_performance.py
"""
import os
import statistics
import sys
import time
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
warnings.filterwarnings('ignore')

import pandas as pd

from utils.github_api import github_analyzer
from utils.credential_detector import credential_detector
from models.credential_classifier import CredentialClassifier
from models.anomaly_detector import CommitAnomalyDetector
from models.ml_repo_clusterer import RepositoryClusterer, build_repo_features
from database.db_manager import db_manager

OWNER, REPO, BRANCH = 'Plazmaz', 'leaky-repo', 'master'
REPORT = os.path.join(ROOT, 'scripts', 'measure_performance_resultados.csv')


def timed(fn, repeat):
    times, result = [], None
    for _ in range(repeat):
        start = time.perf_counter()
        result = fn()
        times.append(time.perf_counter() - start)
    return statistics.mean(times), result


def main():
    rows = []

    # 1. API de GitHub (3 repeticiones: es la etapa más lenta y gasta cuota de la API)
    def fetch():
        commits = github_analyzer.get_commits(OWNER, REPO, BRANCH, 50)
        return [github_analyzer.get_commit_details(OWNER, REPO, c['sha']) for c in commits]
    api_time, details = timed(fetch, 3)
    files = [f for d in details if d for f in d.get('files', [])]
    n_commits = len(details)
    rows.append(('API de GitHub', 'Descarga de commits y diffs', api_time, n_commits, 'commits'))

    # 2. Detector regex
    def detect():
        return [det for f in files for det in credential_detector.detect_in_commit_diff(f.get('patch', ''), f['filename'])]
    regex_time, detections = timed(detect, 20)
    rows.append(('Detector regex', '28 patrones sobre los diffs', regex_time, n_commits, 'commits'))

    # 3. Fingerprint
    def fingerprint():
        return {credential_detector.compute_fingerprint(OWNER, REPO, d['file_path'], d['secret']) for d in detections}
    fp_time, unique = timed(fingerprint, 50)
    rows.append(('Fingerprint SHA-256', 'Deduplicación', fp_time, len(detections), 'detecciones'))

    # 4. Entrenamiento de los clasificadores
    cart_time, cart = timed(lambda: (m := CredentialClassifier('cart'), m.train_default(), m)[2], 5)
    rows.append(('Árbol CART', 'Entrenamiento (771 ejemplos)', cart_time, 771, 'ejemplos'))
    rf_time, rf = timed(lambda: (m := CredentialClassifier('random_forest'), m.train_default(), m)[2], 5)
    rows.append(('Random Forest', 'Entrenamiento (771 ejemplos)', rf_time, 771, 'ejemplos'))

    # 5. Predicción
    test = pd.read_csv(os.path.join(ROOT, 'models', 'test_data', 'testset_labeled.csv'), keep_default_na=False)
    cart_pred, _ = timed(lambda: cart.predict(test), 20)
    rows.append(('Árbol CART', f'Predicción ({len(test)} hallazgos)', cart_pred, len(test), 'hallazgos'))
    rf_pred, _ = timed(lambda: rf.predict(test), 20)
    rows.append(('Random Forest', f'Predicción ({len(test)} hallazgos)', rf_pred, len(test), 'hallazgos'))

    # 6. Modelos no supervisados
    commits = db_manager.get_commits_with_features()
    if_time, _ = timed(lambda: CommitAnomalyDetector().fit_predict(commits), 10)
    rows.append(('Isolation Forest', f'Entrenar y puntuar ({len(commits)} commits)', if_time, len(commits), 'commits'))
    features = build_repo_features(db_manager.get_repository_summary(), db_manager.get_credentials_dataframe())
    km_time, _ = timed(lambda: RepositoryClusterer().fit(features), 10)
    rows.append(('K-Means', f'Agrupar ({len(features)} repositorios, K=2..4)', km_time, len(features), 'repositorios'))

    df = pd.DataFrame(rows, columns=['componente', 'tarea', 'segundos', 'cantidad', 'unidad'])
    df['ms_por_unidad'] = df['segundos'] / df['cantidad'] * 1000
    df.to_csv(REPORT, index=False, encoding='utf-8')

    print(f'Repositorio: {OWNER}/{REPO} · {n_commits} commits · {len(files)} archivos modificados · '
          f'{len(detections)} detecciones · {len(unique)} únicas\n')
    for r in df.itertuples():
        print(f'{r.componente:20s} {r.tarea:42s} {r.segundos:8.3f} s   ({r.ms_por_unidad:8.3f} ms por {r.unidad[:-1] if r.unidad.endswith("s") else r.unidad})')
    pipeline = api_time + regex_time + fp_time + rf_pred / len(test) * len(unique)
    print(f'\nAnálisis completo del repositorio (API + regex + fingerprint + Random Forest): {pipeline:.2f} s '
          f'· {pipeline / n_commits * 1000:.0f} ms por commit · la API es el {api_time / pipeline:.1%} del tiempo')
    print(f'Detalle guardado en {REPORT}')


if __name__ == '__main__':
    main()
