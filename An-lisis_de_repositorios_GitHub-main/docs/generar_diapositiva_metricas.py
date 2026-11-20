"""
Genera docs/diapositiva_metricas.png (1920x1080): precisión, recall y F1-score con el
cálculo real de Random Forest en la prueba ciega (VP 36, FP 57, FN 2).

Uso:
    python docs/generar_diapositiva_metricas.py
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'diapositiva_metricas.png')

PAPER, CARD, INK, BODY, LINE = '#F8F6F1', '#FFFEFB', '#17212B', '#46525C', '#DDD8CC'
TEAL, TEAL_LIGHT, CHIP, CHIP_DARK, DARK_TEXT, MUTED = '#1E6F6A', '#7CC4BC', '#EFECE4', '#24313D', '#C8D2D6', '#5B6670'
SERIF, SANS = 'Georgia', 'Arial'

fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor=PAPER)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1920)
ax.set_ylim(1080, 0)
ax.axis('off')


def box(x, y, w, h, fill, edge=None, radius=14):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f'round,pad=0,rounding_size={radius}',
                                facecolor=fill, edgecolor=edge or fill, linewidth=1.5))


def text(x, y, s, size, color, font=SANS, weight='normal', **kw):
    ax.text(x, y, s, fontsize=size * 0.72, color=color, family=font, fontweight=weight, va='top', **kw)


# Encabezado
text(128, 118, '06 — RESULTADOS · CÓMO MEDIMOS', 26, TEAL, weight='bold')
text(128, 166, 'Tres métricas, tres preguntas', 64, INK, font=SERIF, weight='bold')

# Tarjetas
cards = [
    ('Precisión', 'De lo que marca como\ncredencial, ¿cuánto lo es?', 'VP ÷ (VP + FP)', '36 ÷ (36 + 57) = 38,7%', False),
    ('Recall', 'De las credenciales reales,\n¿cuántas encuentra?', 'VP ÷ (VP + FN)', '36 ÷ (36 + 2) = 94,7%', False),
    ('F1-score', '¿Qué tan bien equilibra\nlas dos?', '2·P·R ÷ (P + R)', '2·0,387·0,947 ÷ 1,334 = 0,550', True),
]
x0, y0, w, h, gap = 128, 290, 530, 470, 37
for i, (title, question, formula, example, dark) in enumerate(cards):
    x = x0 + i * (w + gap)
    box(x, y0, w, h, INK if dark else CARD, None if dark else LINE)
    text(x + 40, y0 + 40, title, 46, TEAL_LIGHT if dark else TEAL, font=SERIF, weight='bold')
    text(x + 40, y0 + 120, question, 30, PAPER if dark else INK, linespacing=1.4)
    box(x + 40, y0 + 230, w - 80, 72, CHIP_DARK if dark else CHIP, radius=10)
    text(x + 60, y0 + 250, formula, 29, DARK_TEXT if dark else BODY)
    ax.plot([x + 40, x + w - 40], [y0 + 345, y0 + 345], color='#34424F' if dark else LINE, lw=1.5)
    text(x + 40, y0 + 368, 'En CyberGuard (Random Forest)', 22, TEAL_LIGHT if dark else TEAL, weight='bold')
    text(x + 40, y0 + 406, example, 27, PAPER if dark else INK, weight='bold')

# Leyenda y pie
text(128, 800, 'VP', 28, INK, weight='bold')
text(178, 800, 'credencial real detectada (36)    ·', 28, BODY)
text(640, 800, 'FP', 28, INK, weight='bold')
text(690, 800, 'ruido reportado como credencial (57)    ·', 28, BODY)
text(1250, 800, 'FN', 28, INK, weight='bold')
text(1300, 800, 'credencial real que se escapó (2)', 28, BODY)
text(128, 950, 'Prueba ciega: 181 hallazgos de 7 repositorios que el modelo nunca vio. Las regex solas lo reportan todo: '
     'recall 100%, precisión 21,0%, F1 0,347.', 24, MUTED)

fig.savefig(OUT, dpi=100, facecolor=PAPER)
print(OUT)
