"""
Genera docs/modelos_ml_v2.png (1920x1080): los cuatro modelos de ML en tarjetas oscuras
sobre fondo blanco, con título, rol y una frase por modelo.

Uso:
    python docs/generar_modelos_ml_v2.py
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modelos_ml_v2.png')
FONT = 'Segoe UI'

# (número, nombre, rol, descripción, acento, fondo, círculo)
cards = [
    ('01', 'Random Forest', 'Detección de credenciales', 'Validar si el patrón regex\nes una credencial real',
     '#3B8FE0', '#0E2A47', '#1C63B8'),
    ('02', 'Isolation Forest', 'Riesgo por commit', 'Detectar commits\nanómalos',
     '#8B78E6', '#15102E', '#5747B5'),
    ('03', 'Árbol CART + Gini', 'Modelo de comparación', 'Árbol simple que compite\ncon Random Forest',
     '#2CC98E', '#0B2219', '#11704F'),
    ('04', 'K-Means (k=4)', 'Nivel de riesgo por repo', 'Agrupar repositorios\npor perfil de riesgo',
     '#F0A030', '#241606', '#87500F'),
]

fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor='white')
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1920)
ax.set_ylim(1080, 0)
ax.axis('off')


def t(x, y, s, size, color, weight='normal', **kw):
    ax.text(x, y, s, fontsize=size * 0.72, color=color, family=FONT, fontweight=weight, ha='center',
            va='center', **kw)


def spaced(s):
    return '\u200a'.join(s)  # espacio muy fino entre letras


t(960, 100, 'Modelos ML usados', 66, '#17212B')

w, h, gap = 420, 800, 30
x0 = (1920 - 4 * w - 3 * gap) / 2
y0 = 200
for i, (num, name, role, desc, accent, bg, circle) in enumerate(cards):
    x = x0 + i * (w + gap)
    cx = x + w / 2
    # Sombra suave
    ax.add_patch(FancyBboxPatch((x + 10, y0 + 12), w, h, boxstyle='round,pad=0,rounding_size=26',
                                facecolor=accent, alpha=0.08, edgecolor='none'))
    ax.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle='round,pad=0,rounding_size=26', facecolor=bg,
                                edgecolor=accent, linewidth=2))
    ax.add_patch(Rectangle((x - 2, y0 - 22), w + 4, 22, facecolor=accent, edgecolor='none'))
    ax.add_patch(Circle((cx, y0 + 175), 112, facecolor=circle, edgecolor=accent, linewidth=3))
    t(cx, y0 + 175, num, 80, 'white', weight='bold')
    t(cx, y0 + 365, name, 38, 'white', weight='bold')
    t(cx, y0 + 430, spaced(role), 22, accent, weight='bold')
    ax.plot([x + 95, x + w - 95], [y0 + 485, y0 + 485], color=accent, lw=2, alpha=0.7)
    t(cx, y0 + 590, desc, 27, '#B8C2CC', linespacing=1.7)

fig.savefig(OUT, dpi=100, facecolor='white')
print(OUT)
