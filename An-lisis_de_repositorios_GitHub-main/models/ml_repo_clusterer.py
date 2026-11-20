"""
Agrupamiento de repositorios con K-Means (aprendizaje NO supervisado).

Idea: cada repositorio se describe con unos pocos números (cuántos hallazgos tiene
por commit, qué parte son reales, dónde aparecen...). K-Means coloca K centros y
asigna cada repositorio al más cercano, moviendo los centros hasta que no cambian.
Así se forman grupos de repositorios con un perfil de riesgo parecido.

La calidad de los grupos se mide con el coeficiente Silhouette (de -1 a 1):
cerca de 1, cada repositorio está mucho más cerca de su grupo que de los demás.
Se prueba K desde 2 hasta un grupo por cada 2-3 repositorios (como máximo 5) y se
queda el K con mejor Silhouette; ante un empate práctico (diferencia < 0,01) se
prefiere el K mayor, porque separa más perfiles con la misma calidad.
"""
import os
import sys

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import ML_CONFIG

# El tamaño del repositorio (log_commits) se calcula pero no se usa para agrupar:
# no mide riesgo y hacía que los repositorios pequeños se agruparan entre sí
FEATURES = ['findings_per_commit', 'real_ratio', 'real_per_commit',
            'env_config_share', 'docs_tests_share']
FEATURE_LABELS = {
    'log_commits': 'commits analizados (log)',
    'findings_per_commit': 'hallazgos por commit',
    'real_ratio': 'proporción de reales',
    'real_per_commit': 'credenciales reales por commit',
    'env_config_share': 'hallazgos en .env/config',
    'docs_tests_share': 'hallazgos en docs/pruebas',
}


def file_kind(path):
    path = (path or '').lower()
    name = path.rsplit('/', 1)[-1]
    if '.env' in name or 'docker' in name or path.endswith(('.json', '.yml', '.yaml', '.ini', '.properties',
                                                             '.xml', '.toml', '.cfg', '.conf')):
        return 'env_config'
    if path.endswith(('.md', '.rst', '.txt', '.adoc')) or any(p in path for p in ('test', 'spec', 'mock', 'example')):
        return 'docs_tests'
    return 'other'


def build_repo_features(summary_df, credentials_df):
    """Una fila por repositorio con las características del perfil de riesgo"""
    creds = credentials_df.copy()
    creds['verdict'] = creds['manual_label'].where(creds['manual_label'].notna(), creds['ml_prediction'])
    creds['kind'] = creds['file_path'].map(file_kind)
    creds['repo'] = creds['repo_owner'] + '/' + creds['repo_name']

    rows = []
    for r in summary_df.itertuples():
        repo = f'{r.repo_owner}/{r.repo_name}'
        c = creds[creds['repo'] == repo]
        commits = max(int(r.commits_analyzed or 0), 1)
        findings, real = len(c), int((c['verdict'] == 1).sum())
        rows.append({
            'repo': repo,
            'commits': int(r.commits_analyzed or 0),
            'findings': findings,
            'real': real,
            'log_commits': np.log1p(commits),
            'findings_per_commit': findings / commits,
            'real_ratio': real / findings if findings else 0.0,
            'real_per_commit': real / commits,
            'env_config_share': float((c['kind'] == 'env_config').mean()) if findings else 0.0,
            'docs_tests_share': float((c['kind'] == 'docs_tests').mean()) if findings else 0.0,
        })
    return pd.DataFrame(rows)


def name_cluster(centroid):
    """Nombre legible a partir del centro del grupo (en la escala original)"""
    if centroid['real_per_commit'] >= 2:
        return 'Fuga masiva'
    if centroid['docs_tests_share'] >= 0.5:
        return 'Ruido de docs y pruebas'
    if centroid['real_ratio'] >= 0.5:
        return 'Fugas reales'
    if centroid['real_per_commit'] < 0.01:
        return 'Sin credenciales reales'
    return 'Riesgo medio'


class RepositoryClusterer:

    def __init__(self, k_range=None):
        self.k_range = k_range              # None = automático según el número de repositorios
        self.model = None
        self.scaler = StandardScaler()
        self.k = None
        self.silhouette = None
        self.silhouette_by_k = {}

    def fit(self, repo_features):
        """
        Agrupa los repositorios. Devuelve el DataFrame con 'cluster' y 'cluster_name'.
        Necesita al menos 3 repositorios.
        """
        if len(repo_features) < 3:
            raise ValueError('Se necesitan al menos 3 repositorios analizados para agrupar.')
        X = self.scaler.fit_transform(repo_features[FEATURES])

        k_range = self.k_range or range(2, max(2, min(5, len(repo_features) // 2 - 1)) + 1)
        self.silhouette_by_k = {}
        for k in k_range:
            if k >= len(repo_features):
                break
            labels = KMeans(n_clusters=k, n_init=10, random_state=ML_CONFIG['random_state']).fit_predict(X)
            if len(set(labels)) > 1:
                self.silhouette_by_k[k] = float(silhouette_score(X, labels))
        best = max(self.silhouette_by_k.values())
        self.k = max(k for k, score in self.silhouette_by_k.items() if score >= best - 0.01)
        self.silhouette = self.silhouette_by_k[self.k]
        self.model = KMeans(n_clusters=self.k, n_init=10, random_state=ML_CONFIG['random_state']).fit(X)

        result = repo_features.copy()
        result['cluster'] = self.model.labels_
        centroids = pd.DataFrame(self.scaler.inverse_transform(self.model.cluster_centers_), columns=FEATURES)
        names = {cluster: name_cluster(centroid) for cluster, centroid in centroids.iterrows()}
        # Si dos grupos reciben el mismo nombre, se distinguen por su densidad de credenciales reales
        for name in set(names.values()):
            same = [c for c, n in names.items() if n == name]
            if len(same) > 1:
                same.sort(key=lambda c: -centroids.loc[c, 'real_per_commit'])
                labels = ['densidad alta', 'densidad media', 'densidad baja'] if len(same) == 3 \
                    else ['densidad alta', 'densidad baja'] if len(same) == 2 \
                    else [f'nivel {i + 1}' for i in range(len(same))]
                for c, label in zip(same, labels):
                    names[c] = f'{name} · {label}'
        result['cluster_name'] = result['cluster'].map(names)
        self.centroids = centroids.assign(cluster_name=[names[i] for i in centroids.index])
        return result.sort_values(['cluster_name', 'real_per_commit'], ascending=[True, False])


repository_clusterer = RepositoryClusterer()
