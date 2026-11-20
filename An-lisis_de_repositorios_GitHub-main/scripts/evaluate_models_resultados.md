# Resultados de los modelos de CyberGuard

## Clasificador de hallazgos (supervisado)

| Modelo | F1 validación cruzada | leaky-repo P / R / F1 | Prueba ciega P / R / F1 | Sin gitleaks P / R / F1 |
|---|---|---|---|---|
| Árbol de decisión CART | 0.970 | 100.0% / 84.7% / 0.917 | 23.8% / 63.2% / 0.345 | 60.0% / 63.2% / 0.615 |
| Random Forest | 0.989 | 100.0% / 93.1% / 0.964 | 38.7% / 94.7% / 0.550 | 70.6% / 94.7% / 0.809 |

Referencia, regex solas en la prueba ciega: precisión 21.0%, recall 100%, F1 0.347. En leaky-repo no hay negativos: la precisión siempre es 100%.

## Isolation Forest: commits anómalos (no supervisado)

- Commits analizados: 684 · marcados como anómalos: 35 (5%)
- Con credenciales reales: 17.1% de los anómalos frente a 3.2% de los normales (5.3 veces más)
- Tomando "tiene una credencial real" como positivo: precisión 17.1%, recall 22.2%, F1 0.194

## K-Means: grupos de repositorios (no supervisado)

- K elegido: 4 · Silhouette: 0.467 (probados: K=2: 0.379, K=3: 0.311, K=4: 0.467)

- **Fuga masiva**: JuanOsorioa/laberinto_camelas
- **Fugas reales**: Plazmaz/leaky-repo, trufflesecurity/test_keys, digininja/leakyrepo, OWASP/wrongsecrets, WebGoat/WebGoat, digininja/DVWA
- **Ruido de docs y pruebas**: juice-shop/juice-shop, appsecco/dvna
- **Sin credenciales reales**: haderrenteria13/portfolio, JeremyRenteria/arte-memoria-tienda
