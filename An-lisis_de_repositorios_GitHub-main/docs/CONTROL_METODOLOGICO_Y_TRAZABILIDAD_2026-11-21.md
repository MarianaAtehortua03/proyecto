# CyberGuard — control metodológico y trazabilidad (21/11/2026)

> Documento académico y de auditoría. Registra hechos visibles en el repositorio y en el expediente, no certifica un despliegue, una prueba ejecutada, una aceptación comercial ni el cierre técnico de todas las historias.

## Fuentes y alcance
- **Repositorio oficial de código:** https://github.com/MarianaAtehortua03/proyecto
- **Proyecto y tablero Jira:** https://jeremirenteria123.atlassian.net/jira/software/projects/SCRUM/boards/1
- **Expediente documental y HTML:** https://drive.google.com/drive/folders/1Bub0SLWPi8WykJnOUYvbgySesCzmAdq-
- **Corte de referencia:** 21/11/2026; los datos no se sincronizan en tiempo real.

La evaluación académica exige documentar siete fases, trazabilidad, Scrum, resultados y procedimientos. No exige agregar funcionalidad al software ni desplegarlo en Azure. El HTML es el entregable documental principal; GitHub se mantiene como fuente del código.

## 1. Identidad técnica comprobada

El código está ubicado bajo `An-lisis_de_repositorios_GitHub-main/` dentro del repositorio. El commit de referencia previo a esta propuesta es `fb25a387ee1bdd112553ad40b28b59d1050501d0`.

| Componente | Archivo fuente del repositorio |
| --- | --- |
| Integración API GitHub | `utils/github_api.py` |
| Detección de credenciales | `utils/credential_detector.py` |
| Interfaz de escritorio | `gui/main_gui.py` |
| Datos PostgreSQL | `database/schema.sql`, `database/db_manager.py`, `init_database.py` |
| Clasificación ML | `models/ml_classifier.py` |
| Configuración / dependencias | `config/config.py`, `requirements.txt` |
| Pruebas existentes | `tests/test_credential_detector.py` (framework `unittest`) |
| Resultados experimentales | `scripts/evaluate_models_resultados.md`, `scripts/measure_performance_resultados.csv` |

**Advertencias:** una prueba escrita no demuestra ejecución ni éxito. Los resultados de scripts son artefactos históricos; sus métricas no deben presentarse como una verificación nueva sin constancia de entorno, SHA y fecha.

## 2. Trazabilidad de las 16 historias

Cada fila necesita para considerarse validada: evidencia de implementación identificable por SHA/PR, revisión, ejecución de caso CT, resultado y versión aceptada. Actualmente, la matriz enlaza requisitos e historias al diseño y a módulos existentes; **no se atribuyen PR no verificadas**.

| Historia | Jira | RF | Caso de prueba previsto | Área de código |
| --- | --- | --- | --- | --- |
| US-01 | SCRUM-84 | RF-01 | CT-01 | Configuración / API / GUI |
| US-02 | SCRUM-85 | RF-02 | CT-02 | GUI |
| US-03 | SCRUM-86 | RF-03 | CT-03 | API |
| US-04 | SCRUM-87 | RF-04 | CT-04 | Detector |
| US-05 | SCRUM-88 | RF-05 | CT-05 | Detector |
| US-06 | SCRUM-89 | RF-06 | CT-06 | Detector |
| US-07 | SCRUM-90 | RF-07 | CT-07 | Inicialización / esquema |
| US-08 | SCRUM-91 | RF-07 | CT-08 | Persistencia |
| US-09 | SCRUM-92 | RF-08 | CT-09 | GUI / riesgo |
| US-10 | SCRUM-93 | RF-09 | CT-10 | GUI / datos |
| US-11 | SCRUM-94 | RF-09 | CT-11 | GUI / CART |
| US-12 | SCRUM-95 | RF-10 | CT-12 | GUI / modelo |
| US-13 | SCRUM-96 | RF-09 | CT-13 | Modelo |
| US-14 | SCRUM-97 | RF-11 | CT-14 | GUI |
| US-15 | SCRUM-98 | RF-11 | CT-15 | GUI |
| US-16 | SCRUM-99 | RF-12 | CT-16 | GUI |

## 3. Estados de GitHub y cambios no integrados al corte

- PR [#1](https://github.com/MarianaAtehortua03/proyecto/pull/1): saneamiento propuesto de configuración y archivos generados; **abierta, sin merge**, no confirma rotación de credenciales.
- PR [#2](https://github.com/MarianaAtehortua03/proyecto/pull/2): plantilla `.env.example` y exclusiones; **borrador, sin merge**.
- Al corte no existe release publicada; `v1.0.0` es un objetivo planificado.
- El código `main` tiene `imbalanced-learn==0.12.4` en `requirements.txt`. El defecto histórico SCRUM-103 ya no representa ausencia del paquete en ese archivo; falta instalación limpia verificada.
- Existe `tests/test_credential_detector.py` escrito usando `unittest`; no se acreditó su ejecución con logs, ni integración continua. Las descripciones históricas de SCRUM-59 deben leerse junto a su actualización del 21/11/2026.
- SCRUM-100 figura Finalizado en Jira de manera administrativa; no implica prueba de arranque aceptada en la versión actual.
- SCRUM-101 permanece En curso y requiere revisión de secretos históricos. No se reproducen tokens, passwords ni otras credenciales en este documento.

## 4. Resultados experimentales almacenados, no reejecutados

El archivo `scripts/evaluate_models_resultados.md` contiene F1 de prueba ciega **0,345 para CART** y **0,550 para Random Forest**. Son evaluaciones distintas del criterio principal de US-11 (CART); las métricas no deben intercambiarse. Las mediciones de `measure_performance_resultados.csv` dependen del entorno de ejecución original y no equivalen a una prueba de aceptación CT con resultado y firma.

## 5. Lista de cierre honesto

1. Registrar prueba de arranque en la versión actual con fecha, entorno, SHA, responsable y resultado.
2. Registrar instalación limpia y compatibilidad de dependencias.
3. Realizar revisión de secretos y del ZIP histórico; gestionar la rotación de cualquier credencial real de forma privada.
4. Revisar y fusionar PR pertinentes **solo tras validación**; no declarar integración antes de su merge.
5. Asociar cada historia y caso CT a un cambio, ejecutor, resultado y decisión de aceptación auténticos.
6. Documentar ceremonias Scrum solo si tuvieron lugar; conservar las seis asesorías históricas como asesorías, no como Sprint Review/Retrospective inventadas.
7. No publicar `v1.0.0` ni declarar operación de cliente sin controles de release y aceptación.
8. Verificar desde la cuenta del docente que Drive y Jira permitan acceder a los originales; el HTML debe contener las evidencias esenciales sin usar estos enlaces.
9. Preparar aparte el MP4 explicativo exigido y la sustentación con participación de los integrantes.

## 6. Roles del informe

El corte documental de SCRUM-37 identifica a **Mariana Atehortua (Scrum Master)**, **Jeremi Rentaría (Product Owner)** y **Juan Osorio (análisis y QA)**. Esta asignación actual no pretende reescribir autorías, firmas o menciones históricas en actas académicas.

**Integridad documental:** no inventar resultados, asistentes, fechas de reuniones, aprobaciones, despliegues o credenciales. Los estados de Jira son administrativos; cada afirmación técnica requiere su prueba de origen.
