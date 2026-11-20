"""
Genera docs/grafica_fallas.png (1920x1080): porcentaje de fallas en la prueba ciega
(181 hallazgos, 38 credenciales reales), regex solas frente a Random Forest.

  Fallas% = (N_fallas / N_total) × 100
  · Credenciales que se escaparon: FN / reales      (regex 0/38,  RF 2/38)
  · Falsas alarmas reportadas:     FP / reportados  (regex 143/181, RF 57/93)

Uso:
    python docs/generar_grafica_fallas.py
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grafica_fallas.png')

PAPER, INK, BODY, MUTED, LINE = '#F8F6F1', '#17212B', '#46525C', '#7A848C', '#DDD8CC'
REGEX, RF = '#B9B2A4', '#1E6F6A'
SERIF, SANS = 'Georgia', 'Arial'

groups = [
    ('Falsas alarmas', 'alertas reportadas que no eran credenciales', (143, 181), (57, 93)),
    ('Credenciales que se escaparon', 'reales que el sistema no reportó', (0, 38), (2, 38)),
]

fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor=PAPER)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1920)
ax.set_ylim(1080, 0)
ax.axis('off')


def t(x, y, s, size, color, font=SANS, weight='normal', ha='left', va='center'):
    ax.text(x, y, s, fontsize=size * 0.72, color=color, family=font, fontweight=weight, ha=ha, va=va)


t(128, 110, '¿Cuánto falla el sistema?', 64, INK, font=SERIF, weight='bold')
t(128, 185, 'Fallas % = (N fallas ÷ N total) × 100   ·   prueba ciega: 181 hallazgos de 7 repositorios nunca vistos',
  26, BODY)

x0, full, bar_h = 128, 1230, 64          # 100% = 1230 px
label_x = x0 + full + 40                 # columna fija para las etiquetas
for x in range(0, 101, 25):
    xx = x0 + full * x / 100
    ax.plot([xx, xx], [365, 880], color=LINE, lw=1, zorder=0)
    t(xx, 905, f'{x}%', 18, MUTED, ha='center')

for i, (name, desc, regex, rf) in enumerate(groups):
    y = 300 + i * 310
    t(x0, y, name, 34, INK, weight='bold')
    t(x0, y + 40, desc, 22, MUTED)
    for j, ((n, total), color, who) in enumerate(((regex, REGEX, 'Regex solas'), (rf, RF, 'Random Forest'))):
        by = y + 80 + j * (bar_h + 14)
        pct = n / total * 100
        ax.add_patch(plt.Rectangle((x0, by), max(full * pct / 100, 3), bar_h, facecolor=color, edgecolor='none'))
        t(label_x, by + bar_h / 2, f'{pct:.1f}%'.replace('.', ','), 40, INK if color == RF else BODY,
          font=SERIF, weight='bold')
        t(label_x + 170, by + bar_h / 2, f'{who}\n{n} de {total}', 20, MUTED)

t(128, 990, 'Random Forest elimina 86 de las 143 falsas alarmas de las regex (−17,7 puntos) '
  'a cambio de dejar escapar solo 2 credenciales reales.', 25, BODY)

fig.savefig(OUT, dpi=100, facecolor=PAPER)
print(OUT)
