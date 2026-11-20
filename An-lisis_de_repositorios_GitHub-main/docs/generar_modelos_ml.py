"""
Genera docs/modelos_ml.png (1920x1080): los cuatro modelos de Machine Learning de CyberGuard
en tarjetas sencillas, con el dato medido de cada uno.

Uso:
    python docs/generar_modelos_ml.py
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modelos_ml.png')

PAPER, INK, BODY = '#F8F6F1', '#17212B', '#46525C'
FONT = 'Segoe UI'

# (número, nombre, rol, descripción, dato, etiqueta del dato, color, fondo, círculo)
cards = [
    ('01', 'Random Forest', 'Clasificador principal', '¿El hallazgo es una\ncredencial real o\nun falso positivo?',
     '94,7%', 'recall · F1 0,550', '#3B8FE0', '#0E2A47', '#1C63B8'),
    ('02', 'Isolation Forest', 'Commits anómalos', 'Marca los commits que\nse salen de lo normal\n(muchos archivos, horas raras)',
     '5,3×', 'más fugas en commits anómalos', '#8B78E6', '#16112E', '#5747B5'),
    ('03', 'Árbol CART + Gini', 'Modelo de comparación', 'Árbol de decisión simple\nque compite con\nRandom Forest',
     '0,345', 'F1 · Random Forest lo supera', '#2CC98E', '#0B2219', '#11704F'),
    ('04', 'K-Means (K = 4)', 'Perfil de repositorios', 'Agrupa los repositorios\nsegún cómo son sus\nhallazgos',
     '0,467', 'Silhouette · 4 grupos', '#F0A030', '#241606', '#87500F'),
]

fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor=PAPER)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1920)
ax.set_ylim(1080, 0)
ax.axis('off')


def t(x, y, s, size, color, weight='normal', ha='center', **kw):
    ax.text(x, y, s, fontsize=size * 0.72, color=color, family=FONT, fontweight=weight, ha=ha, va='center', **kw)


t(960, 82, 'Modelos de Machine Learning', 60, INK, weight='bold')
t(960, 148, 'Qué hace cada uno en CyberGuard, en una frase', 28, BODY)

w, h, gap = 405, 790, 32
x0 = (1920 - 4 * w - 3 * gap) / 2
y0 = 220
for i, (num, name, role, desc, value, value_label, accent, bg, circle) in enumerate(cards):
    x = x0 + i * (w + gap)
    cx = x + w / 2
    ax.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle='round,pad=0,rounding_size=22', facecolor=bg,
                                edgecolor=accent, linewidth=2))
    ax.add_patch(Rectangle((x + 1, y0), w - 2, 16, facecolor=accent, edgecolor='none'))
    ax.add_patch(Circle((cx, y0 + 150), 88, facecolor=circle, edgecolor=accent, linewidth=3))
    t(cx, y0 + 150, num, 68, 'white', weight='bold')
    t(cx, y0 + 300, name, 36, 'white', weight='bold')
    t(cx, y0 + 352, role.upper(), 20, accent, weight='bold')
    ax.plot([x + 90, x + w - 90], [y0 + 392, y0 + 392], color=accent, lw=1.5, alpha=0.6)
    t(cx, y0 + 480, desc, 25, '#C9D1D9', linespacing=1.5)
    # Dato medido
    ax.add_patch(FancyBboxPatch((x + 40, y0 + 590), w - 80, 160, boxstyle='round,pad=0,rounding_size=14',
                                facecolor='white', alpha=0.06, edgecolor='none'))
    t(cx, y0 + 648, value, 54, accent, weight='bold')
    t(cx, y0 + 712, value_label, 19, '#C9D1D9')

fig.savefig(OUT, dpi=100, facecolor=PAPER)
print(OUT)
