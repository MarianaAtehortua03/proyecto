"""
Genera docs/infografia_resultados.png: rendimiento del modelo, eficiencia del sistema,
resultados técnicos y comparativa de modelos. Todos los valores salen de:
  scripts/evaluate_models_resultados.md, scripts/benchmark_leaky_repo.py y
  scripts/measure_performance_resultados.csv

Uso:
    python docs/generar_infografia_resultados.py
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'infografia_resultados.png')

SURFACE, CARD = '#f5f4f0', '#fcfcfb'
INK, INK2, MUTED, GRID = '#0b0b0b', '#52514e', '#898781', '#e1e0d9'
RF = '#2a78d6'          # serie destacada (énfasis)
CART = '#8f8e88'        # gris medio
REGEX = '#c9c8c1'       # gris claro
plt.rcParams.update({'font.family': 'Segoe UI', 'axes.edgecolor': GRID, 'axes.labelcolor': INK2,
                     'xtick.color': MUTED, 'ytick.color': INK2})

fig = plt.figure(figsize=(16, 9), dpi=150, facecolor=SURFACE)


def panel(x, y, w, h, number, title, subtitle):
    ax = fig.add_axes([x, y, w, h])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle='round,pad=0,rounding_size=0.025',
                                facecolor=CARD, edgecolor=GRID, linewidth=1, transform=ax.transAxes))
    ax.text(0.04, 0.92, number, fontsize=12, fontweight='bold', color=RF, va='center')
    ax.text(0.09, 0.92, title, fontsize=16, fontweight='bold', color=INK, va='center')
    ax.text(0.04, 0.84, subtitle, fontsize=11, color=INK2, va='center')
    return ax


def stat(ax, x, y, value, label, color=INK, size=30):
    ax.text(x, y, value, fontsize=size, fontweight='bold', color=color, va='center')
    ax.text(x, y - 0.11, label, fontsize=10.5, color=INK2, va='center', linespacing=1.3)


# --- Título ---
fig.text(0.035, 0.955, 'CyberGuard · Resultados del proyecto', fontsize=24, fontweight='bold', color=INK, va='center')
fig.text(0.035, 0.915, 'Valores medidos en datos que los modelos no usaron para entrenar', fontsize=13,
         color=INK2, va='center')

L, R, W = 0.035, 0.515, 0.45
TOP_Y, BOT_Y, H = 0.47, 0.035, 0.405

# --- 1. Rendimiento del modelo ---
ax = panel(L, TOP_Y, W, H, '01', 'Rendimiento del modelo', 'Random Forest en la prueba ciega: 181 hallazgos de 7 repositorios nuevos')
stat(ax, 0.05, 0.58, '38,7%', 'Precisión\n(regex solas: 21,0%)', RF)
stat(ax, 0.37, 0.58, '94,7%', 'Recall\n36 de 38 credenciales reales', RF)
stat(ax, 0.69, 0.58, '0,550', 'F1-score\n(regex solas: 0,347)', RF)
ax.plot([0.05, 0.95], [0.30, 0.30], color=GRID, lw=1)
ax.text(0.05, 0.19, 'F1 en el benchmark leaky-repo: 0,964', fontsize=12, color=INK, va='center')
ax.text(0.05, 0.09, 'IC 95% de la precisión: 28,9%–48,6% · mejora estadísticamente significativa', fontsize=10.5,
        color=INK2, va='center')

# --- 2. Eficiencia del sistema ---
ax = panel(R, TOP_Y, W, H, '02', 'Eficiencia del sistema', 'Tiempos medidos en Windows 11 · Plazmaz/leaky-repo (25 commits)')
stat(ax, 0.05, 0.62, '7,7 s', 'análisis completo\nde 25 commits', INK, 26)
stat(ax, 0.37, 0.62, '308 ms', 'por commit', INK, 26)
stat(ax, 0.66, 0.62, '99%', 'del tiempo es espera\nde la API de GitHub', INK, 26)
bars = fig.add_axes([R + 0.15, TOP_Y + 0.035, W - 0.21, 0.13], facecolor=CARD)
stages = [('Random Forest (72)', 0.020), ('Detector regex', 0.059), ('API de GitHub', 7.624)]
labels, values = zip(*stages)
bars.barh(range(3), values, height=0.55, color=[RF, RF, CART])
for i, v in enumerate(values):
    text = f'{v:.2f} s'.replace('.', ',') if v >= 0.1 else f'{v * 1000:.0f} ms'
    bars.text(v + 0.08, i, text, va='center', fontsize=10, color=INK)
bars.set_yticks(range(3))
bars.set_yticklabels(labels, fontsize=9.5)
bars.set_xlim(0, 9.2)
bars.xaxis.set_visible(False)
for side in ('top', 'right', 'bottom'):
    bars.spines[side].set_visible(False)
bars.tick_params(axis='y', length=0)

# --- 3. Resultados técnicos ---
ax = panel(L, BOT_Y, W, H, '03', 'Resultados técnicos', 'Benchmark público y modelos no supervisados')
stat(ax, 0.05, 0.64, '67/175', 'secretos del benchmark\nleaky-repo (38,3%)', INK, 26)
stat(ax, 0.37, 0.64, '5,3×', 'más credenciales en commits\nanómalos (Isolation Forest)', INK, 26)
stat(ax, 0.69, 0.64, '0,467', 'Silhouette de K-Means\n4 grupos de 11 repos', INK, 26)
ax.plot([0.05, 0.95], [0.36, 0.36], color=GRID, lw=1)
rows = [('Gitleaks', '127/175', '72,6%', '17'), ('CyberGuard + Random Forest', '67/175', '38,3%', '0'),
        ('detect-secrets', '41/175', '23,4%', '0'), ('TruffleHog', '40/175', '22,9%', '43')]
ax.text(0.05, 0.30, 'Herramienta', fontsize=9.5, color=MUTED, va='center')
ax.text(0.62, 0.30, 'Secretos', fontsize=9.5, color=MUTED, va='center', ha='right')
ax.text(0.78, 0.30, 'Cobertura', fontsize=9.5, color=MUTED, va='center', ha='right')
ax.text(0.94, 0.30, 'Falsos pos.', fontsize=9.5, color=MUTED, va='center', ha='right')
for k, (name, found, cov, fp) in enumerate(rows):
    yy = 0.235 - k * 0.058
    weight = 'bold' if 'CyberGuard' in name else 'normal'
    color = RF if 'CyberGuard' in name else INK
    ax.text(0.05, yy, name, fontsize=10.5, color=color, fontweight=weight, va='center')
    ax.text(0.62, yy, found, fontsize=10.5, color=INK, fontweight=weight, va='center', ha='right')
    ax.text(0.78, yy, cov, fontsize=10.5, color=INK, fontweight=weight, va='center', ha='right')
    ax.text(0.94, yy, fp, fontsize=10.5, color=INK, fontweight=weight, va='center', ha='right')

# --- 4. Comparativa de modelos ---
panel(R, BOT_Y, W, H, '04', 'Comparativa de modelos', 'Prueba ciega · mismo conjunto para los tres')
chart = fig.add_axes([R + 0.045, BOT_Y + 0.05, W - 0.07, 0.24], facecolor=CARD)
metrics = ['Precisión', 'Recall', 'F1-score']
series = [('Regex solas', [0.210, 1.000, 0.347], REGEX), ('Árbol CART', [0.238, 0.632, 0.345], CART),
          ('Random Forest', [0.387, 0.947, 0.550], RF)]
width = 0.25
for s, (name, vals, color) in enumerate(series):
    xs = [m + (s - 1) * width for m in range(3)]
    chart.bar(xs, vals, width=width - 0.03, color=color, label=name, zorder=3)
    if name == 'Random Forest':
        for x, v in zip(xs, vals):
            chart.text(x, v + 0.03, f'{v:.3f}'.replace('.', ',') if v < 1 else '1', ha='center',
                       fontsize=9.5, color=INK, fontweight='bold')
chart.set_xticks(range(3))
chart.set_xticklabels(metrics, fontsize=10.5, color=INK2)
chart.set_ylim(0, 1.15)
chart.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
chart.set_yticklabels(['0', '0,25', '0,50', '0,75', '1'], fontsize=9)
chart.grid(axis='y', color=GRID, lw=1, zorder=0)
for side in ('top', 'right', 'left'):
    chart.spines[side].set_visible(False)
chart.tick_params(axis='both', length=0)
chart.legend(loc='upper left', bbox_to_anchor=(0.0, 1.17), ncol=3, frameon=False, fontsize=10,
             labelcolor=INK2, handlelength=1, handleheight=0.8)

fig.savefig(OUT, dpi=150, facecolor=SURFACE)
print(OUT)
