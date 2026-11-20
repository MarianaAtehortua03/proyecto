"""
Detector de commits anómalos con Isolation Forest (aprendizaje NO supervisado).

Idea: un commit "normal" se parece a la mayoría (pocos archivos, horario habitual,
sin archivos sensibles). Isolation Forest construye árboles que dividen los datos
al azar; los puntos raros quedan aislados en muy pocas divisiones. Cuantas menos
divisiones hacen falta para aislar un commit, más anómalo es.

No necesita etiquetas: sirve para priorizar qué commits revisar primero.
"""
import os
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import ML_CONFIG

# Proporción de commits que se marcan como anómalos
CONTAMINATION = 0.05

FEATURES = ['log_files', 'log_additions', 'log_deletions', 'log_message', 'commit_hour',
            'is_weekend', 'has_config_files', 'has_env_files', 'is_sensitive_file']


def build_commit_features(commits_df):
    """Características numéricas de cada commit (las cantidades en escala logarítmica)"""
    df = pd.DataFrame(index=commits_df.index)
    df['log_files'] = np.log1p(commits_df['files_modified'].fillna(0))
    df['log_additions'] = np.log1p(commits_df['code_additions'].fillna(0))
    df['log_deletions'] = np.log1p(commits_df['code_deletions'].fillna(0))
    df['log_message'] = np.log1p(commits_df['message_length'].fillna(0))
    df['commit_hour'] = commits_df['commit_hour'].fillna(12)
    df['is_weekend'] = (commits_df['commit_day_of_week'].fillna(0) >= 5).astype(int)
    for column in ('has_config_files', 'has_env_files', 'is_sensitive_file'):
        df[column] = commits_df[column].fillna(False).astype(int)
    return df[FEATURES]


def explain(row, medians):
    """Motivos legibles de por qué un commit se sale de lo normal"""
    reasons = []
    if row['files_modified'] > 3 * max(medians['files_modified'], 1):
        reasons.append(f"{int(row['files_modified'])} archivos")
    if row['code_additions'] > 5 * max(medians['code_additions'], 1):
        reasons.append(f"{int(row['code_additions'])} líneas añadidas")
    if row['code_deletions'] > 5 * max(medians['code_deletions'], 1):
        reasons.append(f"{int(row['code_deletions'])} líneas borradas")
    if row['commit_hour'] < 6 or row['commit_hour'] >= 23:
        reasons.append(f"hora {int(row['commit_hour'])}:00")
    if row['has_env_files']:
        reasons.append('incluye .env')
    elif row['is_sensitive_file']:
        reasons.append('archivo sensible')
    return ', '.join(reasons) if reasons else 'combinación poco común'


class CommitAnomalyDetector:

    def __init__(self, contamination=CONTAMINATION):
        self.contamination = contamination
        self.model = None

    def fit_predict(self, commits_df):
        """
        Entrena con todos los commits y devuelve el DataFrame con:
        anomaly_score (más alto = más raro), is_anomaly y reason.
        """
        X = build_commit_features(commits_df)
        self.model = IsolationForest(
            n_estimators=200,
            contamination=self.contamination,
            random_state=ML_CONFIG['random_state']
        )
        labels = self.model.fit_predict(X)          # -1 = anómalo, 1 = normal
        result = commits_df.copy()
        result['anomaly_score'] = -self.model.score_samples(X)
        result['is_anomaly'] = labels == -1
        medians = commits_df[['files_modified', 'code_additions', 'code_deletions']].median()
        result['reason'] = [explain(row, medians) if anomalous else ''
                            for (_, row), anomalous in zip(commits_df.iterrows(), result['is_anomaly'])]
        return result.sort_values('anomaly_score', ascending=False)

    @staticmethod
    def evaluate(result):
        """
        Sin etiquetas de "anomalía" se mide cuánto ayuda a priorizar: proporción de
        commits con al menos una credencial real entre los anómalos frente a los normales.
        """
        has_real = result['real_credentials'] > 0
        anomalous = result['is_anomaly']
        rate_anomalous = float(has_real[anomalous].mean()) if anomalous.any() else 0.0
        rate_normal = float(has_real[~anomalous].mean()) if (~anomalous).any() else 0.0
        tp = int((has_real & anomalous).sum())
        precision = tp / int(anomalous.sum()) if anomalous.any() else 0.0
        recall = tp / int(has_real.sum()) if has_real.any() else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return {
            'commits': len(result),
            'anomalous': int(anomalous.sum()),
            'rate_anomalous': rate_anomalous,
            'rate_normal': rate_normal,
            'lift': rate_anomalous / rate_normal if rate_normal else None,
            'precision': precision, 'recall': recall, 'f1': f1,
        }


commit_anomaly_detector = CommitAnomalyDetector()
