# GitHub Repository Analyzer - Machine Learning Edition

## 📋 Descripción del Proyecto

Herramienta de escritorio desarrollada en Python para analizar repositorios de GitHub, detectar credenciales expuestas y clasificar commits usando Machine Learning con Árboles de Decisión CART.

## 🎯 Características Principales

### 1. Detección de Credenciales
- Utiliza **expresiones regulares (regex)** con la librería `re`
- Detecta múltiples tipos de credenciales:
  - Claves AWS
  - Tokens de GitHub
  - Claves API
  - Contraseñas
  - Claves privadas
  - Y más...

### 2. Análisis de Commits
- Integración con la API de GitHub
- Análisis de diff de commits
- Extracción de características
- Almacenamiento en PostgreSQL

### 3. Machine Learning
- **Algoritmo**: Árbol de Decisión CART
- **Criterio**: Índice de Gini para pureza de nodos
- **Librería**: scikit-learn
- **Procesamiento**: pandas
- **Clasificación**: Commits seguros vs. riesgosos

### 4. Base de Datos
- PostgreSQL para almacenamiento persistente
- Tablas relacionales optimizadas
- Vistas para análisis rápido

### 5. Interfaz Gráfica
- Desarrollada con tkinter
- Tablas interactivas
- Visualización de resultados
- Exportación de datos

## 🏗️ Arquitectura del Proyecto

```
github_analyzer/
│
├── main.py                 # Punto de entrada
├── requirements.txt        # Dependencias
├── README.md              # Este archivo
│
├── config/
│   └── config.py          # Configuración global
│
├── database/
│   ├── schema.sql         # Esquema de BD
│   └── db_manager.py      # Gestor de PostgreSQL
│
├── utils/
│   ├── credential_detector.py  # Detección con regex
│   └── github_api.py          # Integración con GitHub
│
├── models/
│   └── ml_classifier.py   # Modelo CART con Gini
│
└── gui/
    └── main_gui.py        # Interfaz gráfica
```

## 📊 Diseño de Datos

### Modelo Entidad-Relación

```
repositories (1) ──< (N) commits (1) ──< (N) credentials_detected
                                │
                                └──< (1) commit_features
```

### Tablas Principales

1. **repositories**: Información de repositorios analizados
2. **commits**: Detalles de cada commit
3. **credentials_detected**: Credenciales encontradas
4. **commit_features**: Características para ML
5. **ml_model_results**: Resultados del modelo

## 🚀 Instalación y Configuración

### 1. Requisitos Previos
- Python 3.8+
- PostgreSQL 12+
- Token de GitHub (Personal Access Token)

### 2. Clonar o Crear el Proyecto
```bash
# Si usas git
git clone [url-del-repositorio]
cd github_analyzer

# O crea las carpetas manualmente según la estructura
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar PostgreSQL

#### Crear la base de datos:
```bash
psql -U postgres
```

```sql
-- Ejecutar el contenido de database/schema.sql
\i database/schema.sql
```

#### Configurar credenciales:
Edita `config/config.py`:
```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'github_analyzer',
    'user': 'tu_usuario',
    'password': 'tu_password'
}
```

### 5. Configurar Token de GitHub

1. Crear un Personal Access Token:
   - GitHub → Settings → Developer settings → Personal access tokens
   - Permisos necesarios: `repo`, `read:user`

2. Edita `config/config.py`:
```python
GITHUB_TOKEN = 'ghp_tu_token_aqui'
```

### 6. Ejecutar la Aplicación
```bash
python main.py
```

## 📖 Uso de la Aplicación

### Análisis de Repositorio

1. **Abrir la pestaña "Análisis de Repositorio"**
2. **Ingresar datos**:
   - Propietario: `facebook`
   - Repositorio: `react`
   - Rama: `main`
   - Máx. Commits: `100`
3. **Clic en "Iniciar Análisis"**
4. **Esperar resultados en el log**

### Ver Resultados

1. **Pestaña "Resultados"**: Tabla con credenciales detectadas
2. **Pestaña "Estadísticas"**: Resumen general
3. **Exportar**: Botón para guardar en CSV

### Veredicto automático con Machine Learning

El modelo viene **entrenado de fábrica**: al abrir la aplicación se entrena en menos de un
segundo y clasifica cada hallazgo de las regex como **🚨 Credencial real** o **✅ Falso positivo**
(columnas "Veredicto" y "Confianza" de la pestaña Hallazgos). No hay que configurar nada.

- **Datos de entrenamiento** (`models/training_data/`):
  - `seed_credentials.csv` (720 ejemplos) — **sintético**, generado por `build_seed_dataset.py`
    pasando líneas de código por el mismo detector regex de la aplicación. Criterio: un valor
    literal en configuración o código es una credencial real aunque sea débil (`hunter22`);
    solo es falso positivo con una señal clara (placeholder, valor de ejemplo oficial como
    `AKIAIOSFODNN7EXAMPLE`, etiqueta HTML, código que lee otra variable, prosa de documentación).
  - `labeled_vulnerable_apps.csv` (51 hallazgos) — hallazgos reales de DVWA, WebGoat, DVNA,
    OWASP WrongSecrets, digininja/leakyrepo y trufflesecurity/test_keys, **etiquetados a mano**.
- **Corregir un veredicto**: en Hallazgos, selecciona la fila y pulsa "Es una credencial real"
  o "Es un falso positivo". La corrección manda sobre el modelo y este se reentrena con ella.
- **Dashboard**: cuenta solo los hallazgos con veredicto de credencial real.
- **Métricas del modelo**: menú Ayuda → "Información del modelo ML".

### Modelos de Machine Learning

| Modelo | Tipo | Pregunta que responde | Archivo |
|---|---|---|---|
| **Random Forest** | Supervisado | ¿Este hallazgo es una credencial real? | `models/credential_classifier.py` |
| **Isolation Forest** | No supervisado | ¿Qué commits son anómalos y conviene revisar primero? | `models/anomaly_detector.py` |
| **K-Means** | No supervisado | ¿Qué repositorios tienen un perfil de riesgo parecido? | `models/ml_repo_clusterer.py` |

- **Random Forest**: 200 árboles CART (Gini), cada uno entrenado con una muestra distinta de
  los datos y una parte de las 34 características; la clase se decide por votación. Se compara
  con un solo árbol CART y se usa el de mayor F1 en validación cruzada (0,989 frente a 0,970).
- **Isolation Forest**: describe cada commit por tamaño, hora, día y archivos sensibles; marca
  como anómalo el 5% que se aísla con menos cortes aleatorios.
- **K-Means**: describe cada repositorio por hallazgos y credenciales reales por commit,
  proporción de reales y dónde aparecen; elige K con el coeficiente Silhouette.

Los resultados de los tres se reproducen con
`python scripts/evaluate_models.py` (guarda `scripts/evaluate_models_resultados.md`).
`docs/diagrama_modelos.png` los resume en una imagen.

### Evaluación con un benchmark público

`python scripts/benchmark_leaky_repo.py` mide la herramienta contra
[Plazmaz/leaky-repo](https://github.com/Plazmaz/leaky-repo) (175 secretos documentados en 44
archivos) con la misma metodología con la que el benchmark publica los resultados de otras
herramientas. **leaky-repo nunca se usa para entrenar** (conjunto de prueba separado).

| Herramienta | Encontrados | Cobertura | Archivos | Falsos positivos |
|---|---|---|---|---|
| Gitleaks (publicado) | 127/175 | 72.6% | 40/44 | 17 |
| CyberGuard, solo regex | 72/175 | 41.1% | 36/44 | 0 |
| **CyberGuard, regex + Random Forest** | **67/175** | **38.3%** | **34/44** | **0** |
| CyberGuard, regex + CART | 61/175 | 34.9% | 30/44 | 0 |
| detect-secrets (publicado) | 41/175 | 23.4% | 23/44 | 0 |
| TruffleHog (publicado) | 40/175 | 22.9% | 23/44 | 43 |

Random Forest conserva 67 de los 72 hallazgos de las regex (recall 0,931, F1 0,964). Limitaciones:
todos los hallazgos de las regex en leaky-repo están en archivos con secretos, por lo que este
benchmark no mide la capacidad de descartar falsos positivos; y los patrones regex nuevos se
diseñaron después de analizar los fallos en este benchmark, así que la cobertura de las regex
es optimista. El detalle por hallazgo queda en `scripts/benchmark_leaky_repo_resultados.csv`.

### Evaluación de precisión (descarte de falsos positivos)

`python scripts/evaluate_testset.py` evalúa el modelo sobre un conjunto de prueba de 181
hallazgos de 7 repositorios que **no se usan para entrenar** (`awslabs/git-secrets`,
`OWASP/NodeGoat`, `docker/awesome-compose`, `cr0hn/vulnerable-node`,
`we45/Vulnerable-Flask-App`, `gitleaks/gitleaks`, `getsentry/self-hosted`). Los hallazgos se
etiquetaron a mano y a ciegas (sin ver la predicción) con los criterios de
`models/test_data/CRITERIOS_ETIQUETADO.md`, definidos antes de revisar los datos.
`scripts/build_testset.py` regenera el escaneo.

| | Regex solas | CART | **Random Forest** |
|---|---|---|---|
| Precisión | 21,0% | 23,8% | **38,7%** (IC 95%: 28,9%–48,6%) |
| Recall | 100% | 63,2% | **94,7%** |
| F1-score | 0,347 | 0,345 | **0,550** |
| Falsos positivos descartados | 0% | 46,2% | **60,1%** |
| Sin `gitleaks/gitleaks` (99 hallazgos): precisión / F1 | 38,4% / 0,555 | 60,0% / 0,615 | **70,6% / 0,809** |

Lectura: Random Forest casi duplica la precisión de las regex sin perder credenciales reales
(solo 2 de 38) y la mejora es estadísticamente significativa (el intervalo no incluye el 21%).
Su error típico es aceptar código que solo lee un secreto o claves falsas con formato real,
como las de los casos de prueba de Gitleaks.

**Isolation Forest** (684 commits): 35 anómalos; el 17,1% contiene credenciales reales frente
al 3,2% de los normales (5,3 veces más). **K-Means** (11 repositorios): K = 4, Silhouette 0,467.

### Pruebas automáticas

```bash
python -m unittest discover tests
```

### Hallazgos únicos (fingerprinting)

Cada hallazgo se identifica con un SHA-256 de (repositorio, ruta normalizada, secreto).
Si el mismo secreto aparece en varios commits o se vuelve a analizar el repositorio,
no se duplica en la base de datos. Para bases creadas antes de este cambio:

```bash
python init_database.py            # agrega columnas y calcula fingerprints
python init_database.py --dedupe   # además elimina los registros duplicados
```

## 🤖 Machine Learning - Detalles Técnicos

### Árbol de Decisión CART

**CART** (Classification and Regression Trees) es un algoritmo que construye árboles de decisión binarios.

#### Índice de Gini

La **impureza de Gini** mide qué tan "mezcladas" están las clases en un nodo:

```
Gini(node) = 1 - Σ(p_i²)
```

Donde `p_i` es la proporción de muestras de la clase `i`.

**Interpretación**:
- `Gini = 0`: Nodo puro (todas las muestras de la misma clase)
- `Gini = 0.5`: Máxima impureza (50%-50% en clasificación binaria)

#### Proceso de Construcción

1. **Selección de división**: 
   - Para cada característica, evaluar todas las divisiones posibles
   - Calcular la ganancia de Gini de cada división
   - Elegir la división que minimiza la impureza

2. **División recursiva**:
   - Aplicar el mismo proceso a cada nodo hijo
   - Continuar hasta alcanzar criterios de parada

3. **Criterios de parada**:
   - Profundidad máxima (`max_depth`)
   - Mínimo de muestras para dividir (`min_samples_split`)
   - Nodo puro

#### Características Utilizadas

1. **Temporales**:
   - Hora del commit
   - Día de la semana

2. **Mensaje**:
   - Longitud
   - Palabras clave sospechosas

3. **Código**:
   - Archivos modificados
   - Líneas añadidas/eliminadas
   - Ratio de cambios

4. **Archivos**:
   - Presencia de archivos de configuración
   - Presencia de archivos .env

### Importancia de Características

La importancia se calcula como la **reducción total de Gini** que aporta cada característica:

```python
importance(feature) = Σ (reducción_gini_en_divisiones_que_usan_feature)
```

## 🔍 Detección de Credenciales

### Patrones Regex

La aplicación utiliza expresiones regulares compiladas para detectar:

```python
CREDENTIAL_PATTERNS = {
    'aws_access_key': r'AKIA[0-9A-Z]{16}',
    'github_token': r'gh[pousr]_[0-9a-zA-Z]{36}',
    'private_key': r'-----BEGIN (RSA|DSA|EC) PRIVATE KEY-----',
    # ... más patrones
}
```

### Proceso de Detección

1. **Compilación de patrones** (al inicio)
2. **Análisis de diff** (líneas añadidas en commits)
3. **Filtrado de falsos positivos**
4. **Clasificación por severidad**:
   - CRITICAL: AWS keys, private keys
   - HIGH: GitHub tokens, API keys
   - MEDIUM: Otros tipos

## 📈 Visualización de Datos

### Tablas en GUI

La interfaz muestra:
- ID de credencial
- Tipo detectado
- Archivo y línea
- Severidad (con código de color)
- Commit SHA
- Autor y fecha

### Exportación

Todos los resultados se pueden exportar a CSV para análisis externo.

## 🎓 Capítulo de Diseño de Datos (Proyecto de Grado)

### 3.1 Modelo de Datos

#### 3.1.1 Diagrama Entidad-Relación

El modelo de datos se diseñó siguiendo los principios de normalización hasta la 3FN, garantizando la integridad referencial y minimizando la redundancia.

**Entidades principales**:

1. **REPOSITORY**: Representa un repositorio de GitHub
   - Atributos: repo_id, repo_name, repo_owner, repo_url, analysis_date
   - Clave primaria: repo_id
   - Restricción UNIQUE en (repo_owner, repo_name)

2. **COMMIT**: Representa un commit dentro de un repositorio
   - Atributos: commit_id, repo_id, commit_sha, commit_message, author_name, commit_date
   - Clave primaria: commit_id
   - Clave foránea: repo_id → repositories(repo_id)

3. **CREDENTIAL**: Credencial expuesta detectada
   - Atributos: credential_id, commit_id, credential_type, file_path, severity
   - Clave primaria: credential_id
   - Clave foránea: commit_id → commits(commit_id)

#### 3.1.2 Justificación del Diseño

**PostgreSQL** fue elegido por:
- Soporte robusto para transacciones ACID
- Capacidad de manejar grandes volúmenes de datos
- Excelente rendimiento en consultas complejas
- Soporte nativo para JSON (útil para almacenar importancia de características)

**Normalización**:
- Evita redundancia de información de repositorios
- Permite análisis histórico de commits
- Facilita consultas agregadas por repositorio

#### 3.1.3 Índices

Se crearon índices en:
- `commit_sha`: Búsquedas rápidas de commits específicos
- `repo_id` en tabla commits: Join eficiente con repositories
- `commit_id` en credentials: Join eficiente

### 3.2 Diccionario de Datos

[Incluir tablas detalladas con cada campo, tipo de dato, restricciones]

### 3.3 Vistas del Sistema

**v_repository_summary**:
- Propósito: Análisis rápido de estadísticas por repositorio
- Campos: repo_id, total_commits, total_credentials, avg_risk_score

**v_commits_with_credentials**:
- Propósito: Listar todos los commits que contienen credenciales
- Incluye: información de commit, tipo de credencial, severidad

## 🔧 Configuración Avanzada

### Ajustar Parámetros del Modelo

En `config/config.py`:

```python
ML_CONFIG = {
    'test_size': 0.3,          # 30% para prueba
    'random_state': 42,        # Reproducibilidad
    'max_depth': 10,           # Profundidad máxima del árbol
    'min_samples_split': 5,    # Mínimo para dividir nodo
    'criterion': 'gini'        # Usar Gini (CART)
}
```

### Agregar Nuevos Patrones de Credenciales

En `config/config.py`:

```python
CREDENTIAL_PATTERNS = {
    # Agregar tu patrón
    'mi_api_key': r'mi_patron_regex_aqui',
    # ...
}
```

## 🐛 Solución de Problemas

### Error de Conexión a PostgreSQL
```
✗ Error al crear pool de conexiones
```
**Solución**: Verificar que PostgreSQL esté corriendo y las credenciales sean correctas.

### Error de Token de GitHub
```
⚠ Token de GitHub no configurado o inválido
```
**Solución**: Verificar que el token tenga los permisos correctos.

### No hay datos para entrenar ML
```
No hay suficientes datos para entrenar
```
**Solución**: Analizar al menos 10-20 commits antes de entrenar el modelo.

## 📚 Librerías Utilizadas

- **psycopg2**: Conexión con PostgreSQL
- **requests**: Llamadas a GitHub API
- **scikit-learn**: Machine Learning (CART)
- **pandas**: Manipulación de datos
- **numpy**: Operaciones numéricas
- **matplotlib/seaborn**: Visualización
- **re**: Expresiones regulares
- **tkinter**: Interfaz gráfica

## 🤝 Contribuciones

Este es un proyecto de grado. Para sugerencias o mejoras, contactar al autor.

## 📄 Licencia

Proyecto académico - Todos los derechos reservados

## ✍️ Autor

Proyecto de Grado - 2024
Análisis de Repositorios GitHub con Machine Learning

---

**Nota**: Esta aplicación está diseñada con fines educativos y de investigación. El análisis de repositorios debe hacerse respetando los términos de servicio de GitHub y con los permisos apropiados.