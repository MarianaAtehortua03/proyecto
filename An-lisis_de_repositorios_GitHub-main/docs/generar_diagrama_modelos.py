"""
Genera docs/diagrama_modelos.png: resumen visual de los tres modelos de CyberGuard
(Random Forest, Isolation Forest y K-Means).

Uso:
    python docs/generar_diagrama_modelos.py
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'diagrama_modelos.png')

DARK, LIGHT, BG = '#10192B', '#F5F3EE', '#F5F3EE'
BLUE, BLUE_T = '#2F6FB0', '#EAF1F8'
ORANGE, ORANGE_T = '#B85A15', '#FBEDE2'
GREEN, GREEN_T = '#3D6B2E', '#E8F1E2'
GRAY, GRAY_T = '#5F6875', '#E6E2D8'
TEXT = '#3A4555'

fig = plt.figure(figsize=(16, 9), dpi=150, facecolor=BG)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis('off')


def box(x, y, w, h, title, sub='', fill='#FFFFFF', edge=BLUE, title_color=DARK, sub_color=TEXT,
        dashed=False, title_size=14, sub_size=11):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=0.16',
                                facecolor=fill, edgecolor=edge, linewidth=2,
                                linestyle='--' if dashed else '-'))
    if sub:
        ax.text(x + w / 2, y + h * 0.66, title, ha='center', va='center', fontsize=title_size,
                fontweight='bold', color=title_color)
        ax.text(x + w / 2, y + h * 0.30, sub, ha='center', va='center', fontsize=sub_size,
                color=sub_color, linespacing=1.35)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha='center', va='center', fontsize=title_size,
                fontweight='bold', color=title_color)


def arrow(x1, y1, x2, y2, color=DARK):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='-|>', color=color, lw=2, shrinkA=0, shrinkB=0, mutation_scale=16))


def section(x, y, text, color=ORANGE):
    ax.text(x, y, text, fontsize=12, fontweight='bold', color=color, va='center')


# --- Título ---
ax.text(0.6, 8.5, 'Modelos de Machine Learning en CyberGuard', fontsize=25, fontweight='bold', color=DARK, va='center')
ax.text(0.6, 8.02, 'Un modelo supervisado decide si cada hallazgo es real; dos no supervisados ayudan a priorizar',
        fontsize=13.5, color=TEXT, va='center')

# --- 1. Random Forest dentro del flujo ---
section(0.6, 7.45, '1 · RANDOM FOREST (SUPERVISADO) — ¿ESTE HALLAZGO ES UNA CREDENCIAL REAL?')
y1, h1 = 5.9, 1.25
box(0.6, y1, 2.2, h1, 'Commit', 'línea añadida', fill=GRAY_T, edge=GRAY, dashed=True)
box(3.3, y1, 2.5, h1, 'Detector regex', '28 patrones', edge=GRAY)
box(6.3, y1, 2.5, h1, 'Fingerprint', 'sin duplicados', edge=GRAY)
box(9.3, y1, 3.6, h1, 'Random Forest', '200 árboles CART votan\n34 características', fill=DARK, edge=DARK,
    title_color=LIGHT, sub_color='#C9D3E0', title_size=15)
box(13.4, y1, 2.2, h1, 'Veredicto', 'real o falso positivo\n+ confianza', fill=ORANGE_T, edge=ORANGE,
    sub_size=10.5)
for xa, xb in [(2.8, 3.3), (5.8, 6.3), (8.8, 9.3), (12.9, 13.4)]:
    arrow(xa, y1 + h1 / 2, xb, y1 + h1 / 2)

# Cómo vota el bosque
yv = 4.65
for i, (x, name) in enumerate([(0.6, 'Árbol 1'), (2.2, 'Árbol 2'), (3.8, 'Árbol 3')]):
    box(x, yv, 1.35, 0.7, name, fill=BLUE_T, edge=BLUE, title_size=11.5)
ax.text(5.55, yv + 0.35, '…', fontsize=20, color=BLUE, ha='center', va='center', fontweight='bold')
box(6.0, yv, 1.5, 0.7, 'Árbol 200', fill=BLUE_T, edge=BLUE, title_size=11.5)
box(8.1, yv, 1.9, 0.7, 'Votación', fill='#FFFFFF', edge=BLUE, title_size=11.5)
arrow(7.5, yv + 0.35, 8.1, yv + 0.35, color=BLUE)
ax.plot([10.0, 11.1], [yv + 0.35, yv + 0.35], color=BLUE, lw=2)
arrow(11.1, yv + 0.35, 11.1, y1, color=BLUE)
ax.text(11.35, yv + 0.62, 'cada árbol se entrena con una\nmuestra distinta de los datos',
        fontsize=10.5, color=BLUE, va='center', style='italic')

# --- 2 y 3: no supervisados ---
section(0.6, 3.85, '2 · ISOLATION FOREST (NO SUPERVISADO)', color=GREEN)
section(8.4, 3.85, '3 · K-MEANS (NO SUPERVISADO)', color=GREEN)
y3, h3 = 1.55, 1.95
box(0.6, y3, 3.2, h3, '¿Qué commits son raros?', 'aísla los commits que se\nseparan con pocas divisiones\n(tamaño, hora, .env)',
    fill=GREEN_T, edge=GREEN, title_size=13, sub_size=10.5)
arrow(3.8, y3 + h3 / 2, 4.3, y3 + h3 / 2, color=GREEN)
box(4.3, y3, 3.4, h3, '35 de 684 commits', 'anómalos: 17% con credenciales\nreales frente a 3% normales\n(5,3 veces más)',
    edge=GREEN, title_size=13, sub_size=10.5)
box(8.4, y3, 3.2, h3, '¿Qué repos se parecen?', 'agrupa por hallazgos por commit,\nproporción de reales y\ndónde aparecen',
    fill=GREEN_T, edge=GREEN, title_size=13, sub_size=10.5)
arrow(11.6, y3 + h3 / 2, 12.1, y3 + h3 / 2, color=GREEN)
box(12.1, y3, 3.5, h3, '4 grupos · Silhouette 0,467', 'fuga masiva · fugas reales\nruido de docs y pruebas\nsin credenciales reales',
    edge=GREEN, title_size=13, sub_size=10.5)

# --- Pie ---
ax.text(0.6, 0.85, 'Random Forest en la prueba ciega: precisión 38,7% · recall 94,7% · F1 0,550 '
        '(regex solas: 21,0% · 100% · 0,347; árbol CART: 0,345)', fontsize=12.5, color=DARK, va='center',
        fontweight='bold')
ax.text(0.6, 0.42, 'Random Forest se eligió frente a un solo árbol CART por validación cruzada (F1 0,989 frente a 0,970). '
        'Los dos modelos no supervisados no necesitan etiquetas.', fontsize=11, color=GRAY, va='center')

fig.savefig(OUT, dpi=150, facecolor=BG)
print(OUT)
