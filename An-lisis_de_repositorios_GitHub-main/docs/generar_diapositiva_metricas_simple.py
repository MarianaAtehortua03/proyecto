"""
Genera docs/diapositiva_metricas_simple.png (1920x1080): las tres métricas explicadas en
lenguaje sencillo para una exposición (Random Forest en la prueba ciega).

Uso:
    python docs/generar_diapositiva_metricas_simple.py
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'diapositiva_metricas_simple.png')

PAPER, INK, BODY, MUTED, LINE, ACCENT = '#F8F6F1', '#17212B', '#46525C', '#7A848C', '#DDD8CC', '#1E6F6A'
SERIF, SANS = 'Georgia', 'Arial'

fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor=PAPER)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1920)
ax.set_ylim(1080, 0)
ax.axis('off')


def t(x, y, s, size, color, font=SANS, weight='normal', ha='center', **kw):
    ax.text(x, y, s, fontsize=size * 0.72, color=color, family=font, fontweight=weight, ha=ha, va='top', **kw)


t(960, 130, '¿Qué tan bien funciona el modelo?', 72, INK, font=SERIF, weight='bold')
t(960, 236, 'Random Forest probado con repositorios que nunca había visto', 32, BODY)

columns = [
    ('38,7%', 'Precisión', 'De cada 10 alertas,\ncasi 4 son reales', 'Antes: 2 de cada 10'),
    ('94,7%', 'Recall', 'Encuentra 36 de las\n38 credenciales reales', 'Solo se escapan 2'),
    ('0,55', 'F1-score', 'Nota general del modelo,\nde 0 a 1', 'Antes: 0,35'),
]
centers = [380, 960, 1540]
for cx, (value, name, phrase, before) in zip(centers, columns):
    t(cx, 380, value, 150, ACCENT, font=SERIF, weight='bold')
    t(cx, 590, name, 44, INK, weight='bold')
    t(cx, 668, phrase, 34, BODY, linespacing=1.35)
    t(cx, 820, before, 28, MUTED)
for x in (670, 1250):
    ax.plot([x, x], [400, 860], color=LINE, lw=2)

fig.savefig(OUT, dpi=100, facecolor=PAPER)
print(OUT)
