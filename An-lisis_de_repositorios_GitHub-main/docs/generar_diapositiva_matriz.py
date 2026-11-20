"""
Genera docs/diapositiva_matriz_metricas.png (1920x1080): precisión, recall y F1 explicados
desde la matriz de confusión real de Random Forest en la prueba ciega
(VP 36, FN 2, FP 57, VN 86 · 181 hallazgos).

Uso:
    python docs/generar_diapositiva_matriz.py
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'diapositiva_matriz_metricas.png')

BG, PANEL, INK, SOFT, MUTED, LINE = '#17212B', '#202D39', '#F8F6F1', '#C8D2D6', '#8FA0AA', '#34424F'
PREC = '#7CC4BC'     # precisión: la columna "el modelo dice real"
REC = '#E39A6B'      # recall: la fila "es credencial real"
BASE = '#4A5763'     # barra de referencia (regex solas)
SERIF, SANS = 'Georgia', 'Arial'

fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor=BG)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1920)
ax.set_ylim(1080, 0)
ax.axis('off')


def t(x, y, s, size, color, font=SANS, weight='normal', ha='left', va='top', **kw):
    ax.text(x, y, s, fontsize=size * 0.72, color=color, family=font, fontweight=weight, ha=ha, va=va, **kw)


def rbox(x, y, w, h, fill, edge=None, lw=0, r=12):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f'round,pad=0,rounding_size={r}',
                                facecolor=fill, edgecolor=edge or fill, linewidth=lw))


# --- Encabezado ---
t(128, 104, 'RESULTADOS · MATRIZ DE CONFUSIÓN DE RANDOM FOREST', 26, PREC, weight='bold')
t(128, 150, 'De 4 números salen las 3 métricas', 64, INK, font=SERIF, weight='bold')

# --- Matriz de confusión (izquierda) ---
mx, my, cw, ch = 330, 360, 250, 210          # esquina superior izquierda de las celdas
t(mx + cw, my - 78, 'Lo que dice el modelo', 26, SOFT, ha='center')
t(mx + cw / 2, my - 38, 'Real', 24, MUTED, ha='center')
t(mx + cw * 1.5, my - 38, 'Descartado', 24, MUTED, ha='center')
t(mx - 26, my + ch / 2, 'Credencial\nreal', 24, MUTED, ha='right', va='center', linespacing=1.2)
t(mx - 26, my + ch * 1.5, 'Falso\npositivo', 24, MUTED, ha='right', va='center', linespacing=1.2)
ax.text(150, my + ch, 'La realidad', fontsize=26 * 0.72, color=SOFT, family=SANS, rotation=90,
        ha='center', va='center')

cells = [  # (fila, columna, valor, sigla, descripción)
    (0, 0, '36', 'VP', 'reales detectadas'),
    (0, 1, '2', 'FN', 'reales que se escaparon'),
    (1, 0, '57', 'FP', 'ruido que pasó'),
    (1, 1, '86', 'VN', 'ruido descartado'),
]
for row, col, value, tag, desc in cells:
    x, y = mx + col * cw, my + row * ch
    fill = '#2C4A4C' if (row, col) == (0, 0) else PANEL
    ax.add_patch(Rectangle((x + 4, y + 4), cw - 8, ch - 8, facecolor=fill, edgecolor='none'))
    t(x + cw / 2, y + 38, value, 72, INK, font=SERIF, weight='bold', ha='center')
    t(x + cw / 2, y + 128, tag, 24, SOFT, weight='bold', ha='center')
    t(x + cw / 2, y + 160, desc, 21, MUTED, ha='center')

# Columna de la precisión y fila del recall
ax.add_patch(Rectangle((mx, my), cw, ch * 2, facecolor='none', edgecolor=PREC, linewidth=4))
ax.add_patch(Rectangle((mx - 2, my - 2), cw * 2 + 4, ch + 4, facecolor='none', edgecolor=REC, linewidth=4,
                       linestyle=(0, (8, 5))))
t(mx + cw / 2, my + ch * 2 + 20, 'columna → precisión', 22, PREC, weight='bold', ha='center')
t(mx + cw * 2 + 16, my + 14, 'fila →\nrecall', 22, REC, weight='bold', linespacing=1.2)
t(128, 940, '181 hallazgos de 7 repositorios que el modelo nunca vio · etiquetados a mano y a ciegas', 22, MUTED)

# --- Métricas (derecha) ---
rx, rw = 1010, 782
rows = [
    ('Precisión', '¿Cuánto de lo que marca es real?', '36 ÷ (36 + 57)', 0.387, '38,7%', 0.210, '21,0%', PREC),
    ('Recall', '¿Cuántas credenciales reales encuentra?', '36 ÷ (36 + 2)', 0.947, '94,7%', 1.000, '100%', REC),
    ('F1-score', 'Equilibrio entre las dos', '2·P·R ÷ (P + R)', 0.550, '0,550', 0.347, '0,347', INK),
]
for i, (name, question, formula, value, vtext, base, btext, color) in enumerate(rows):
    y = 300 + i * 205
    rbox(rx, y, rw, 180, PANEL)
    ax.add_patch(Rectangle((rx, y), 8, 180, facecolor=color, edgecolor='none'))
    t(rx + 40, y + 24, name, 38, color, font=SERIF, weight='bold')
    t(rx + 40, y + 78, question, 24, SOFT)
    t(rx + rw - 36, y + 18, vtext, 56, INK, font=SERIF, weight='bold', ha='right')
    t(rx + rw - 36, y + 96, formula, 22, MUTED, ha='right')
    # Barras: modelo frente a regex solas
    bx, bw = rx + 40, rw - 340
    ax.add_patch(Rectangle((bx, y + 128), bw * value, 16, facecolor=color, edgecolor='none'))
    ax.add_patch(Rectangle((bx, y + 152), bw * base, 10, facecolor=BASE, edgecolor='none'))
    t(bx + bw + 14, y + 124, 'Random Forest', 18, SOFT)
    t(bx + bw + 14, y + 148, f'regex solas {btext}', 18, MUTED)

fig.savefig(OUT, dpi=100, facecolor=BG)
print(OUT)
