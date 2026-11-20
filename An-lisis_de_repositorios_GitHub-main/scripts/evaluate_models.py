"""
Mide los modelos de CyberGuard y guarda la tabla de resultados.

  - Clasificador de hallazgos: CART frente a Random Forest, en el benchmark
    leaky-repo y en el conjunto de prueba ciego (ninguno se usa para entrenar).
  - Isolation Forest: commits anómalos frente a commits con credenciales reales.
  - K-Means: agrupamiento de repositorios y coeficiente Silhouette.

Requiere haber ejecutado antes scripts/benchmark_leaky_repo.py y tener la base
de datos con repositorios analizados.

Uso:
    python scripts/evaluate_models.py
"""
import os
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
warnings.filterwarnings('ignore')

import pandas as pd

from database.db_manager import db_manager
from models.credential_classifier import CredentialClassifier
from models.anomaly_detector import CommitAnomalyDetector
from models.ml_repo_clusterer import RepositoryClusterer, build_repo_features

TESTSET = os.path.join(ROOT, 'models', 'test_data', 'testset_labeled.csv')
LEAKY = os.path.join(ROOT, 'scripts', 'benchmark_leaky_repo_resultados.csv')
REPORT = os.path.join(ROOT, 'scripts', 'evaluate_models_resultados.md')


def prf(y_true, y_pred):
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def main():
    lines = ['# Resultados de los modelos de CyberGuard', '']

    blind = pd.read_csv(TESTSET, keep_default_na=False)
    blind['manual_label'] = blind['manual_label'].astype(int)
    leaky = pd.read_csv(LEAKY, keep_default_na=False)
    leaky['label'] = leaky['in_benchmark_file'].astype(str).str.lower().eq('true').astype(int)
    no_gl = blind[blind['repo'] != 'gitleaks/gitleaks']

    rows = []
    for algorithm in ('cart', 'random_forest'):
        model = CredentialClassifier(algorithm=algorithm)
        metrics = model.train_default()
        row = {'Modelo': metrics['algorithm_name'], 'F1 validación cruzada': metrics['cv_mean_f1']}
        for name, data, label in [('leaky-repo', leaky, 'label'), ('Prueba ciega', blind, 'manual_label'),
                                  ('Prueba ciega sin gitleaks', no_gl, 'manual_label')]:
            pred, _ = model.predict(data)
            p, r, f = prf(data[label].to_numpy(), pred)
            row[f'{name} P'], row[f'{name} R'], row[f'{name} F1'] = p, r, f
        rows.append(row)
    clf = pd.DataFrame(rows)

    lines += ['## Clasificador de hallazgos (supervisado)', '',
              '| Modelo | F1 validación cruzada | leaky-repo P / R / F1 | Prueba ciega P / R / F1 | Sin gitleaks P / R / F1 |',
              '|---|---|---|---|---|']
    for _, r in clf.iterrows():
        cell = lambda n: f"{r[f'{n} P']:.1%} / {r[f'{n} R']:.1%} / {r[f'{n} F1']:.3f}"
        lines.append(f"| {r['Modelo']} | {r['F1 validación cruzada']:.3f} | {cell('leaky-repo')} | "
                     f"{cell('Prueba ciega')} | {cell('Prueba ciega sin gitleaks')} |")
    p0 = blind['manual_label'].mean()
    lines += ['', f'Referencia, regex solas en la prueba ciega: precisión {p0:.1%}, recall 100%, '
                  f'F1 {2 * p0 / (1 + p0):.3f}. En leaky-repo no hay negativos: la precisión siempre es 100%.', '']

    detector = CommitAnomalyDetector()
    anomalies = detector.fit_predict(db_manager.get_commits_with_features())
    ev = detector.evaluate(anomalies)
    lines += ['## Isolation Forest: commits anómalos (no supervisado)', '',
              f"- Commits analizados: {ev['commits']} · marcados como anómalos: {ev['anomalous']} (5%)",
              f"- Con credenciales reales: {ev['rate_anomalous']:.1%} de los anómalos frente a "
              f"{ev['rate_normal']:.1%} de los normales ({ev['lift']:.1f} veces más)",
              f"- Tomando \"tiene una credencial real\" como positivo: precisión {ev['precision']:.1%}, "
              f"recall {ev['recall']:.1%}, F1 {ev['f1']:.3f}", '']

    clusterer = RepositoryClusterer()
    groups = clusterer.fit(build_repo_features(db_manager.get_repository_summary(),
                                               db_manager.get_credentials_dataframe()))
    lines += ['## K-Means: grupos de repositorios (no supervisado)', '',
              f"- K elegido: {clusterer.k} · Silhouette: {clusterer.silhouette:.3f} "
              f"(probados: {', '.join(f'K={k}: {v:.3f}' for k, v in clusterer.silhouette_by_k.items())})", '']
    for name, g in groups.groupby('cluster_name'):
        lines.append(f"- **{name}**: {', '.join(g['repo'])}")

    text = '\n'.join(lines) + '\n'
    open(REPORT, 'w', encoding='utf-8').write(text)
    print(text)
    print(f'Guardado en {REPORT}')


if __name__ == '__main__':
    main()
