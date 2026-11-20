"""
Clasificador de hallazgos: decide si una credencial detectada por regex es
una credencial real (1) o un falso positivo (0).

Se entrena con datos etiquetados (conjunto semilla, apps vulnerables y las
correcciones del auditor), de modo que el modelo aprende algo distinto a lo que
ya hacen las expresiones regulares.

Algoritmos (criterio de Gini en ambos):
  - CART: un solo árbol de decisión, fácil de interpretar.
  - Random Forest: muchos árboles entrenados sobre muestras distintas que votan.
Con algorithm='auto' se comparan por validación cruzada sobre los datos de
entrenamiento y se usa el de mayor F1.
"""
import math
import os
import pickle
import re
import sys
from collections import Counter

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree
from sklearn.ensemble import RandomForestClassifier
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import ML_CONFIG
from utils.credential_detector import credential_detector

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved', 'credential_classifier.pkl')
SEED_DATASET = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'training_data', 'seed_credentials.csv')
# Hallazgos reales de aplicaciones vulnerables públicas, etiquetados a mano
LABELED_APPS_DATASET = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'training_data',
                                    'labeled_vulnerable_apps.csv')

# Mínimo de ejemplos etiquetados por clase para poder dividir, validar y probar
MIN_PER_CLASS = 3

SEVERITY_LEVEL = {'CRITICAL': 3, 'HIGH': 2, 'MEDIUM': 1}

# Tokens de proveedor con prefijo fijo (formato muy específico)
PROVIDER_TYPES = {
    'aws_access_key', 'aws_secret_key', 'github_token', 'github_pat', 'github_oauth',
    'slack_token', 'stripe_key', 'google_api', 'heroku_api', 'mailgun_api', 'npm_auth', 'docker_auth'
}
# Asignaciones genéricas "nombre = valor"
GENERIC_TYPES = {'password', 'db_password', 'db_user', 'generic_api_key', 'generic_secret',
                 'generic_token', 'env_secret'}
# Formatos de archivos de configuración conocidos (.netrc, .pgpass, wp-config, XML, hashes)
CONFIG_FORMAT_TYPES = {'netrc_password', 'pgpass_entry', 'php_define_secret', 'xml_password', 'password_hash'}
URL_TYPES = {'connection_string', 'url_with_credentials'}
TOKEN_TYPES = {'jwt_token', 'bearer_token'}

# Señal fuerte de placeholder: el valor no es un secreto
STRONG_PLACEHOLDER = re.compile(
    r'example|sample|dummy|fake|changeme|change_me|change-me|your[_-]|yourpassword|placeholder|'
    r'replace|insert|x{4,}|\*{4,}|<[^>]*>|\$\{|\{\{|todo|lorem',
    re.IGNORECASE
)
# Señal débil: aparece en placeholders pero también en contraseñas débiles reales (Pass!12345)
WEAK_PLACEHOLDER = re.compile(r'test|1234|abcd|password|secret|demo|mock|admin', re.IGNORECASE)
WORD_LIKE = re.compile(r'^[A-Za-z]{3,}[0-9!@#$%&*?._-]{0,6}$')
SEQUENCES = ('0123456789', 'abcdefghijklmnopqrstuvwxyz')
DOC_EXT = ('.md', '.rst', '.txt', '.adoc', '.html', '.htm', '.ejs', '.erb')
CONFIG_EXT = ('.json', '.yml', '.yaml', '.ini', '.toml', '.properties', '.xml', '.cfg', '.conf', '.sql')
CODE_EXT = ('.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rb', '.php', '.cs',
            '.kt', '.swift', '.c', '.cpp', '.rs', '.sh', '.ps1')
TEST_PATH = re.compile(r'(^|/)(tests?|spec|specs|mocks?|__mocks__|fixtures?|examples?|samples?|demo)(/|$)|'
                       r'(test|spec|mock|example|sample)[^/]*$')
COMMENT_LINE = re.compile(r'^\s*(#|//|/\*|\*|<!--|--|;)')
ENV_REFERENCE = re.compile(r'process\.env|os\.environ|getenv|\$\{|System\.getenv|ENV\[', re.IGNORECASE)
MARKUP_LINE = re.compile(r'<\s*(input|label|form|button|div|span|a|p|th)\b', re.IGNORECASE)
CONCATENATION = re.compile(r'["\']\s*\+\s*\w+\s*\+\s*["\']')
PROSE = re.compile(r'\b(the|and|or|with|instead|should|never|every|your|para|con|los|las)\b', re.IGNORECASE)


def shannon_entropy(text):
    """Entropía de Shannon (bits por carácter). Los secretos reales suelen ser aleatorios."""
    if not text:
        return 0.0
    counts = Counter(text)
    total = len(text)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


def extract_value(credential_type, matched):
    """
    Obtiene solo el valor del secreto, descartando el nombre de la variable,
    el usuario, las etiquetas o el host según el formato detectado.
    """
    value = matched or ''
    if credential_type in GENERIC_TYPES:
        parts = re.split(r'[:=]', value, maxsplit=1)
        value = parts[1] if len(parts) == 2 else re.sub(r'^\w+[\s\'"]+', '', value)
    elif credential_type == 'netrc_password':
        value = value.split()[-1] if value.split() else value
    elif credential_type == 'pgpass_entry':
        value = value.rsplit(':', 1)[-1]
    elif credential_type == 'php_define_secret':
        quoted = re.findall(r'[\'"]([^\'"]*)[\'"]', value)
        value = quoted[-1] if quoted else value
    elif credential_type == 'xml_password':
        value = re.sub(r'^<[^>]*>|<[^>]*>$', '', value)
    elif credential_type in URL_TYPES:
        found = re.search(r'://[^:/@\s]+:([^@\s]+)@', value)
        value = found.group(1) if found else value
    return credential_detector.normalize_secret(value)


def longest_sequence_run(text):
    """Longitud de la secuencia consecutiva más larga (ej. '123456', 'abcdef')"""
    lower = text.lower()
    best = 0
    for seq in SEQUENCES:
        run = 1
        for a, b in zip(lower, lower[1:]):
            if a in seq and b in seq and seq.index(b) == seq.index(a) + 1:
                run += 1
                best = max(best, run)
            else:
                run = 1
    return best


def extract_features(credential_type, matched_pattern, file_path, line_content=''):
    """
    Características de un hallazgo individual (no del commit).

    Returns:
        dict: nombre_caracteristica -> valor numérico
    """
    value = extract_value(credential_type, matched_pattern)
    path = credential_detector.normalize_file_path(file_path)
    line = line_content or ''
    length = len(value) or 1

    classes = sum([any(ch.islower() for ch in value), any(ch.isupper() for ch in value),
                   any(ch.isdigit() for ch in value), any(not ch.isalnum() for ch in value)])
    file_name = path.rsplit('/', 1)[-1]

    return {
        # Tipo y severidad del patrón regex que lo encontró
        'severity_level': SEVERITY_LEVEL.get(credential_detector._determine_severity(credential_type), 1),
        'is_provider_token': int(credential_type in PROVIDER_TYPES),
        'is_generic_pattern': int(credential_type in GENERIC_TYPES),
        'is_config_format': int(credential_type in CONFIG_FORMAT_TYPES),
        'is_url_credentials': int(credential_type in URL_TYPES),
        'is_bearer_or_jwt': int(credential_type in TOKEN_TYPES),
        'is_private_key': int(credential_type == 'private_key'),
        # Forma del valor
        'value_length': len(value),
        'value_entropy': round(shannon_entropy(value), 4),
        'char_classes': classes,
        'digit_ratio': sum(ch.isdigit() for ch in value) / length,
        'upper_ratio': sum(ch.isupper() for ch in value) / length,
        'special_ratio': sum(not ch.isalnum() for ch in value) / length,
        'unique_char_ratio': len(set(value)) / length,
        'value_is_word_like': int(bool(WORD_LIKE.match(value))),
        'has_strong_placeholder': int(bool(STRONG_PLACEHOLDER.search(value))),
        'has_weak_placeholder': int(bool(WEAK_PLACEHOLDER.search(value))),
        'value_is_identifier': int(bool(re.fullmatch(r'[a-z]+(?:[A-Z][a-z]+|_[a-z]+)+', value))),
        'longest_sequence': longest_sequence_run(value),
        'has_repeated_chars': int(bool(re.search(r'(.)\1{3,}', value))),
        # Archivo donde aparece
        'is_sensitive_file': int(credential_detector.is_sensitive_file(path)),
        'is_env_file': int('.env' in file_name),
        'is_dotfile': int(file_name.startswith('.') and '.' not in file_name[1:]),
        'is_doc_file': int(path.endswith(DOC_EXT)),
        'is_config_file': int(path.endswith(CONFIG_EXT)),
        'is_code_file': int(path.endswith(CODE_EXT)),
        'is_test_or_example_path': int(bool(TEST_PATH.search(path))),
        # Contexto de la línea
        'line_is_comment': int(bool(COMMENT_LINE.match(line))),
        'line_has_env_reference': int(bool(ENV_REFERENCE.search(line))),
        'line_has_strong_placeholder': int(bool(STRONG_PLACEHOLDER.search(line))),
        'line_is_markup': int(bool(MARKUP_LINE.search(line))),
        'line_has_concatenation': int(bool(CONCATENATION.search(line))),
        'line_prose_words': len(PROSE.findall(line)),
        'line_length': len(line),
    }


def build_feature_matrix(credentials_df):
    """Convierte el DataFrame de credentials_detected en la matriz de características"""
    rows = [
        extract_features(
            row['credential_type'],
            row.get('matched_pattern') or '',
            row.get('file_path') or '',
            row.get('line_content') or ''
        )
        for _, row in credentials_df.iterrows()
    ]
    return pd.DataFrame(rows)


ALGORITHM_NAMES = {'cart': 'Árbol de decisión CART', 'random_forest': 'Random Forest'}


class CredentialClassifier:
    """Clasificador (CART o Random Forest) que separa credenciales reales de falsos positivos"""

    def __init__(self, algorithm='auto'):
        self.algorithm = algorithm          # 'auto', 'cart' o 'random_forest'
        self.algorithm_used = None          # el que quedó entrenado
        self.model = None
        self.feature_names = []
        self.feature_importance = {}
        self.last_metrics = {}
        self.config = ML_CONFIG

    @property
    def is_trained(self):
        return self.model is not None

    def _new_estimator(self, algorithm):
        if algorithm == 'random_forest':
            return RandomForestClassifier(
                n_estimators=200,                 # 200 árboles que votan
                criterion=self.config['criterion'],
                max_depth=self.config['max_depth'],
                min_samples_leaf=2,
                max_features='sqrt',              # cada división ve una parte de las características
                bootstrap=True,                   # cada árbol se entrena con una muestra distinta
                random_state=self.config['random_state'],
                class_weight='balanced',
                n_jobs=-1
            )
        return DecisionTreeClassifier(
            criterion=self.config['criterion'],
            max_depth=self.config['max_depth'],
            min_samples_split=self.config['min_samples_split'],
            # Hojas con al menos 5 ejemplos: evita memorizar casos aislados
            # y da probabilidades (confianza) menos extremas
            min_samples_leaf=5,
            random_state=self.config['random_state'],
            class_weight='balanced'
        )

    def _new_pipeline(self, minority_count, algorithm='cart'):
        """
        SMOTE va DENTRO del pipeline: en validación cruzada se aplica solo a los
        folds de entrenamiento, nunca a los de validación (evita métricas infladas).
        """
        steps = []
        if minority_count >= 2:
            k = min(3, minority_count - 1)
            steps.append(('smote', SMOTE(random_state=self.config['random_state'], k_neighbors=k)))
        steps.append(('clf', self._new_estimator(algorithm)))
        return Pipeline(steps)

    @staticmethod
    def label_summary(credentials_df):
        """Cuántos hallazgos hay etiquetados como reales / falsos positivos"""
        labels = credentials_df['manual_label'].dropna().astype(int)
        return {
            'real': int((labels == 1).sum()),
            'false_positive': int((labels == 0).sum()),
            'unlabeled': int(credentials_df['manual_label'].isna().sum()),
        }

    def train(self, credentials_df):
        """
        Entrena con los hallazgos que tienen etiqueta manual.

        1. División estratificada entrenamiento/prueba (test_size de ML_CONFIG).
        2. Validación cruzada estratificada sobre el conjunto de entrenamiento.
        3. Evaluación sobre el conjunto de prueba (datos no vistos).
        4. Reentrenamiento final con todos los datos etiquetados.

        Returns:
            dict: métricas de evaluación
        """
        labeled = credentials_df[credentials_df['manual_label'].notna()].copy()
        summary = self.label_summary(credentials_df)
        if summary['real'] < MIN_PER_CLASS or summary['false_positive'] < MIN_PER_CLASS:
            raise ValueError(
                f"Se necesitan al menos {MIN_PER_CLASS} hallazgos etiquetados de cada clase. "
                f"Actualmente: {summary['real']} reales y {summary['false_positive']} falsos positivos."
            )

        X = build_feature_matrix(labeled)
        y = labeled['manual_label'].astype(int).reset_index(drop=True)
        self.feature_names = X.columns.tolist()

        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=self.config['test_size'],
            random_state=self.config['random_state'],
            stratify=y
        )

        minority_train = int(y_train.value_counts().min())
        candidates = ['cart', 'random_forest'] if self.algorithm == 'auto' else [self.algorithm]

        # Validación cruzada (solo con datos de entrenamiento) y prueba de cada candidato
        comparison = {}
        folds = 0
        for algorithm in candidates:
            cv_mean, cv_std = None, None
            if minority_train >= 2:
                folds = min(5, minority_train)
                cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=self.config['random_state'])
                # Mínimo de la clase minoritaria que queda en cada fold de entrenamiento
                minority_fold = minority_train - math.ceil(minority_train / folds)
                scores = cross_val_score(self._new_pipeline(minority_fold, algorithm), X_train, y_train,
                                         cv=cv, scoring='f1')
                cv_mean, cv_std = float(scores.mean()), float(scores.std())
            candidate = self._new_pipeline(minority_train, algorithm)
            candidate.fit(X_train, y_train)
            pred = candidate.predict(X_test)
            comparison[algorithm] = {
                'name': ALGORITHM_NAMES[algorithm],
                'cv_mean_f1': cv_mean, 'cv_std_f1': cv_std,
                'precision': precision_score(y_test, pred, zero_division=0),
                'recall': recall_score(y_test, pred, zero_division=0),
                'f1': f1_score(y_test, pred, zero_division=0),
                'y_pred': pred,
            }

        # Se elige por validación cruzada (no por el conjunto de prueba)
        self.algorithm_used = max(candidates, key=lambda a: comparison[a]['cv_mean_f1'] or 0)
        chosen = comparison[self.algorithm_used]
        cv_mean, cv_std, y_pred = chosen['cv_mean_f1'], chosen['cv_std_f1'], chosen['y_pred']
        for result in comparison.values():
            result.pop('y_pred')

        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'confusion_matrix': confusion_matrix(y_test, y_pred, labels=[0, 1]),
            'classification_report': classification_report(
                y_test, y_pred, labels=[0, 1],
                target_names=['Falso positivo', 'Credencial real'], zero_division=0
            ),
            'cv_mean_f1': cv_mean,
            'cv_std_f1': cv_std,
            'cv_folds': folds,
            'algorithm': self.algorithm_used,
            'algorithm_name': ALGORITHM_NAMES[self.algorithm_used],
            'model_comparison': comparison,
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'total_samples': len(X),
            'label_summary': summary,
        }

        # Modelo final: todos los datos etiquetados
        self.model = self._new_pipeline(int(y.value_counts().min()), self.algorithm_used)
        self.model.fit(X, y)
        estimator = self.model.named_steps['clf']
        self.feature_importance = dict(sorted(
            zip(self.feature_names, estimator.feature_importances_),
            key=lambda item: item[1], reverse=True
        ))
        metrics['feature_importance'] = self.feature_importance
        self.last_metrics = metrics
        return metrics

    def train_default(self, user_labeled_df=None):
        """
        Entrena con el conjunto semilla incluido en el proyecto más las
        correcciones que haya hecho el usuario en la pestaña Hallazgos.
        Así la herramienta viene entrenada de fábrica y mejora con el uso.

        Returns:
            dict: métricas de evaluación
        """
        columns = ['credential_type', 'matched_pattern', 'file_path', 'line_content', 'manual_label']
        data = pd.read_csv(SEED_DATASET, keep_default_na=False)[columns]
        data['source'] = 'semilla'
        if os.path.exists(LABELED_APPS_DATASET):
            apps = pd.read_csv(LABELED_APPS_DATASET, keep_default_na=False)[columns]
            apps['source'] = 'apps_vulnerables'
            data = pd.concat([data, apps], ignore_index=True)
        if user_labeled_df is not None and not user_labeled_df.empty:
            user = user_labeled_df[user_labeled_df['manual_label'].notna()][columns].copy()
            user['source'] = 'usuario'
            data = pd.concat([data, user], ignore_index=True)
        data['manual_label'] = data['manual_label'].astype(int)
        metrics = self.train(data)
        metrics['user_samples'] = int((data['source'] == 'usuario').sum())
        metrics['apps_samples'] = int((data['source'] == 'apps_vulnerables').sum())
        self.last_metrics = metrics
        return metrics

    def predict(self, credentials_df):
        """
        Returns:
            tuple: (predicciones 0/1, confianza = probabilidad de la clase predicha)
        """
        if not self.is_trained:
            raise ValueError("El modelo no ha sido entrenado")
        X = build_feature_matrix(credentials_df)[self.feature_names]
        proba = self.model.predict_proba(X)
        classes = list(self.model.classes_)
        predictions = np.array([classes[i] for i in proba.argmax(axis=1)])
        confidence = proba.max(axis=1)
        return predictions, confidence

    def _a_tree(self):
        """El árbol CART, o el primer árbol del bosque si el modelo es Random Forest"""
        estimator = self.model.named_steps['clf']
        return estimator.estimators_[0] if hasattr(estimator, 'estimators_') else estimator

    def get_tree_rules(self):
        if not self.is_trained:
            raise ValueError("El modelo no ha sido entrenado")
        return export_text(self._a_tree(), feature_names=self.feature_names)

    def visualize_tree(self, max_depth=3, output_path='credential_tree.png'):
        if not self.is_trained:
            raise ValueError("El modelo no ha sido entrenado")
        plt.figure(figsize=(20, 10))
        plot_tree(
            self._a_tree(),
            max_depth=max_depth,
            feature_names=self.feature_names,
            class_names=['Falso positivo', 'Credencial real'],
            filled=True, rounded=True, fontsize=10
        )
        plt.title('Árbol de Decisión CART - Clasificador de hallazgos', fontsize=16)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    def save_model(self, filepath=MODEL_PATH):
        if not self.is_trained:
            raise ValueError("El modelo no ha sido entrenado")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'algorithm_used': self.algorithm_used,
                'feature_names': self.feature_names,
                'feature_importance': self.feature_importance,
                'last_metrics': self.last_metrics,
                'config': self.config,
            }, f)

    def load_model(self, filepath=MODEL_PATH):
        """Carga el modelo guardado. Devuelve False si no existe."""
        if not os.path.exists(filepath):
            return False
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        self.model = data['model']
        self.algorithm_used = data.get('algorithm_used', 'cart')
        self.feature_names = data['feature_names']
        self.feature_importance = data['feature_importance']
        self.last_metrics = data.get('last_metrics', {})
        self.config = data.get('config', self.config)
        return True


# Instancia global
credential_classifier = CredentialClassifier()
