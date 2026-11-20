"""
Evalúa el clasificador de hallazgos sobre el conjunto de PRUEBA etiquetado a mano
(models/test_data/testset_labeled.csv), formado por repositorios que no se usan
para entrenar.

Compara:
  - Regex solas: todo hallazgo se reporta como credencial (precisión = reales / total).
  - Regex + ML: solo se reportan los hallazgos que el modelo clasifica como reales.

Uso:
    python scripts/evaluate_testset.py
"""
import os
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

from models.credential_classifier import CredentialClassifier, LABELED_APPS_DATASET

TESTSET = os.path.join(ROOT, 'models', 'test_data', 'testset_labeled.csv')
REPORT = os.path.join(ROOT, 'scripts', 'evaluate_testset_resultados.csv')


def metrics(y_true, y_pred):
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    discard = tn / (tn + fp) if tn + fp else 0.0
    return {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn, 'precision': precision, 'recall': recall,
            'f1': f1, 'discard_rate': discard, 'accuracy': (tp + tn) / len(y_true)}


def bootstrap_ci(y_true, y_pred, key, n=2000, seed=42):
    """Intervalo de confianza del 95% por bootstrap"""
    rng = np.random.default_rng(seed)
    idx = np.arange(len(y_true))
    values = []
    for _ in range(n):
        sample = rng.choice(idx, size=len(idx), replace=True)
        values.append(metrics(y_true[sample], y_pred[sample])[key])
    return np.percentile(values, 2.5), np.percentile(values, 97.5)


def main():
    test = pd.read_csv(TESTSET, keep_default_na=False)
    test = test[test['manual_label'].astype(str).isin(['0', '1'])].copy()
    test['manual_label'] = test['manual_label'].astype(int)

    # Garantía de separación: ningún repositorio de prueba en los datos de entrenamiento
    apps = pd.read_csv(LABELED_APPS_DATASET, keep_default_na=False)
    train_repos = set(apps['repo_owner'] + '/' + apps['repo_name'])
    overlap = train_repos & set(test['repo'])
    assert not overlap, f'Repositorios de prueba presentes en entrenamiento: {overlap}'

    model = CredentialClassifier()
    model.train_default()
    pred, conf = model.predict(test)
    test['ml_prediction'] = pred
    test['ml_confidence'] = conf.round(3)
    test.to_csv(REPORT, index=False, encoding='utf-8')

    y = test['manual_label'].to_numpy()
    p = test['ml_prediction'].to_numpy()
    real, total = int(y.sum()), len(y)
    print(f'Conjunto de prueba: {total} hallazgos de {test.repo.nunique()} repositorios '
          f'({real} credenciales reales, {total - real} falsos positivos)\n')

    m = metrics(y, p)
    regex_precision = real / total
    lo, hi = bootstrap_ci(y, p, 'precision')
    print(f'{"":30s} {"Regex solas":>12s} {"Regex + ML":>12s}')
    print(f'{"Hallazgos reportados":30s} {total:>12d} {m["tp"] + m["fp"]:>12d}')
    print(f'{"Precisión":30s} {regex_precision:>12.1%} {m["precision"]:>12.1%}   (IC 95%: {lo:.1%} - {hi:.1%})')
    print(f'{"Recall (credenciales reales)":30s} {1:>12.1%} {m["recall"]:>12.1%}')
    print(f'{"Falsos positivos reportados":30s} {total - real:>12d} {m["fp"]:>12d}')
    print(f'{"Falsos positivos descartados":30s} {0:>12.1%} {m["discard_rate"]:>12.1%}')
    print(f'\nMatriz de confusión del modelo: TP {m["tp"]} · FP {m["fp"]} · FN {m["fn"]} · TN {m["tn"]}'
          f' · F1 {m["f1"]:.3f} · Accuracy {m["accuracy"]:.3f}')

    # Sensibilidad: sin el repositorio con más peso (puede dominar el resultado)
    biggest = test['repo'].value_counts().idxmax()
    rest = test[test['repo'] != biggest]
    mr = metrics(rest['manual_label'].to_numpy(), rest['ml_prediction'].to_numpy())
    print(f'\nSin {biggest} ({len(rest)} hallazgos): precisión regex {rest.manual_label.mean():.1%} → '
          f'ML {mr["precision"]:.1%} · recall {mr["recall"]:.1%} · descarte de FP {mr["discard_rate"]:.1%}')

    print('\nPor repositorio:')
    for repo, g in test.groupby('repo'):
        r = metrics(g['manual_label'].to_numpy(), g['ml_prediction'].to_numpy())
        print(f'  {repo:30s} hallazgos {len(g):>3d} · reales {int(g.manual_label.sum()):>3d} · '
              f'precisión regex {g.manual_label.mean():>6.1%} → ML {r["precision"]:>6.1%} · recall {r["recall"]:>6.1%}')

    for title, mask in [('Falsos positivos que el modelo NO descartó', (y == 0) & (p == 1)),
                        ('Credenciales reales que el modelo descartó', (y == 1) & (p == 0))]:
        print(f'\n{title}:')
        for _, r in test[mask].iterrows():
            print(f'  {r.repo} · {r.file_path}:{r.line_number} [{r.credential_type}] {str(r.line_content)[:80]}')
    print(f'\nDetalle guardado en {REPORT}')


if __name__ == '__main__':
    main()
