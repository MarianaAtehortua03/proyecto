"""
Genera los diagramas del proyecto en docs/diagramas/ (PNG 2400x1350):
  1_casos_de_uso.png · 2_arquitectura_capas.png · 3_modulos.png · 4_entidad_relacion.png

Uso:
    python docs/generar_diagramas.py
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, FancyBboxPatch, Rectangle

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'diagramas')
os.makedirs(OUT_DIR, exist_ok=True)

PAPER, CARD, INK, BODY, MUTED, LINE = '#F8F6F1', '#FFFEFB', '#17212B', '#46525C', '#6B757D', '#CFC9BC'
TEAL, TEAL_T, TERRA, TERRA_T, GRAY_T, BLUE_T = '#1E6F6A', '#E3EFEC', '#B5542F', '#F6E6DD', '#ECE9E1', '#E6EEF5'
plt.rcParams['font.family'] = 'Segoe UI'


def canvas(title, subtitle):
    fig = plt.figure(figsize=(16, 9), dpi=150, facecolor=PAPER)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1600)
    ax.set_ylim(900, 0)
    ax.axis('off')
    ax.text(60, 52, title, fontsize=24, fontweight='bold', color=INK, va='center')
    ax.text(60, 92, subtitle, fontsize=13, color=BODY, va='center')
    return fig, ax


def box(ax, x, y, w, h, title, sub='', fill=CARD, edge=TEAL, title_color=INK, sub_color=BODY,
        dashed=False, size=13.5, sub_size=11.5, lw=1.8, mono_sub=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=10', facecolor=fill,
                                edgecolor=edge, linewidth=lw, linestyle='--' if dashed else '-'))
    if sub:
        ax.text(x + w / 2, y + h * 0.38, title, fontsize=size, fontweight='bold', color=title_color,
                ha='center', va='center')
        ax.text(x + w / 2, y + h * 0.70, sub, fontsize=sub_size, color=sub_color, ha='center', va='center',
                family='Consolas' if mono_sub else 'Segoe UI')
    else:
        ax.text(x + w / 2, y + h / 2, title, fontsize=size, fontweight='bold', color=title_color,
                ha='center', va='center')


def arrow(ax, x1, y1, x2, y2, color=INK, dashed=False, head=True, both=False, lw=1.6):
    style = '<|-|>' if both else ('-|>' if head else '-')
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, linestyle='--' if dashed else '-',
                                shrinkA=0, shrinkB=0, mutation_scale=16))


def label(ax, x, y, text, color=MUTED, size=11, ha='center', bold=False, italic=False):
    ax.text(x, y, text, fontsize=size, color=color, ha=ha, va='center',
            fontweight='bold' if bold else 'normal', style='italic' if italic else 'normal')


def actor(ax, cx, cy, name, note=''):
    """Monigote UML: cabeza en (cx, cy)"""
    ax.add_patch(Circle((cx, cy), 18, facecolor=CARD, edgecolor=INK, linewidth=2))
    ax.plot([cx, cx], [cy + 18, cy + 75], color=INK, lw=2)
    ax.plot([cx - 32, cx + 32], [cy + 38, cy + 38], color=INK, lw=2)
    ax.plot([cx, cx - 26], [cy + 75, cy + 115], color=INK, lw=2)
    ax.plot([cx, cx + 26], [cy + 75, cy + 115], color=INK, lw=2)
    ax.text(cx, cy + 140, name, fontsize=13.5, fontweight='bold', color=INK, ha='center', va='center')
    if note:
        ax.text(cx, cy + 166, note, fontsize=11, color=MUTED, ha='center', va='center', style='italic')


def save(fig, name):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=150, facecolor=PAPER)
    plt.close(fig)
    print(path)


# ---------------------------------------------------------------------------
# 1. Casos de uso
# ---------------------------------------------------------------------------
def casos_de_uso():
    fig, ax = canvas('Diagrama de casos de uso', 'Qué puede hacer el auditor con CyberGuard')
    ax.add_patch(FancyBboxPatch((330, 135), 920, 720, boxstyle='round,pad=0,rounding_size=18',
                                facecolor='#FBFAF6', edgecolor='#8A949C', linewidth=1.8, linestyle='--'))
    label(ax, 352, 162, 'Sistema CyberGuard', color=MUTED, size=13, ha='left', bold=True)

    col1, col2, w, h = 560, 1015, 330, 74
    main_cases = [('Analizar repositorio', 220), ('Consultar hallazgos', 345), ('Corregir veredicto', 470),
                  ('Consultar dashboard', 595), ('Borrar repositorio', 720)]
    for text, y in main_cases:
        edge = TERRA if 'Borrar' in text else TEAL
        ax.add_patch(Ellipse((col1, y), w, h, facecolor=CARD, edgecolor=edge, linewidth=1.8))
        label(ax, col1, y, text, color=INK, size=13)
    inner = [('Detectar credenciales', 220), ('Clasificar con Random Forest', 345),
             ('Reentrenar el modelo', 470), ('Filtrar por repositorio', 595)]
    for text, y in inner:
        ax.add_patch(Ellipse((col2, y), 360, h, facecolor=TEAL_T, edgecolor=TEAL, linewidth=1.8))
        label(ax, col2, y, text, color=INK, size=13)

    # Actores
    actor(ax, 150, 395, 'Auditor', 'usuario')
    actor(ax, 1430, 150, 'API de GitHub', 'sistema externo')
    # Asociaciones auditor -> casos de uso (desde el cuerpo del monigote)
    for _, y in main_cases:
        arrow(ax, 185, 450, col1 - w / 2, y, color=BODY, head=False, lw=1.4)
    # API de GitHub <-> Detectar credenciales
    arrow(ax, 1395, 250, col2 + 180, 220, color=BODY, head=False, lw=1.4)

    # include / extend
    arrow(ax, col1 + w / 2, 220, col2 - 180, 220, color=TEAL, dashed=True)
    label(ax, (col1 + w / 2 + col2 - 180) / 2, 202, '«include»', color=TEAL, size=11)
    arrow(ax, col2, 220 + h / 2, col2, 345 - h / 2, color=TEAL, dashed=True)
    label(ax, col2 + 14, 282, '«include»', color=TEAL, size=11, ha='left')
    arrow(ax, col1 + w / 2, 470, col2 - 180, 470, color=TEAL, dashed=True)
    label(ax, (col1 + w / 2 + col2 - 180) / 2, 452, '«include»', color=TEAL, size=11)
    arrow(ax, col2 - 180, 595, col1 + w / 2, 595, color=TERRA, dashed=True)
    label(ax, (col1 + w / 2 + col2 - 180) / 2, 577, '«extend»', color=TERRA, size=11)

    label(ax, 1430, 470, 'Leyenda', color=INK, size=11.5, bold=True)
    ax.add_patch(Ellipse((1350, 510), 60, 26, facecolor=TEAL_T, edgecolor=TEAL, linewidth=1.5))
    label(ax, 1390, 510, 'incluidos', color=BODY, size=11, ha='left')
    ax.add_patch(Ellipse((1350, 550), 60, 26, facecolor=CARD, edgecolor=TEAL, linewidth=1.5))
    label(ax, 1390, 550, 'acción del auditor', color=BODY, size=11, ha='left')
    ax.add_patch(Ellipse((1350, 590), 60, 26, facecolor=CARD, edgecolor=TERRA, linewidth=1.5))
    label(ax, 1390, 590, 'acción irreversible', color=BODY, size=11, ha='left')
    save(fig, '1_casos_de_uso.png')


# ---------------------------------------------------------------------------
# 2. Arquitectura en capas
# ---------------------------------------------------------------------------
def arquitectura_capas():
    fig, ax = canvas('Arquitectura en capas', 'Cada capa solo se comunica con la capa vecina')
    bx, bw, bh = 270, 1060, 190
    bands = [(140, BLUE_T, '#1F5A94', 'CAPA DE PRESENTACIÓN · tkinter'),
             (395, TERRA_T, '#8A3F22', 'CAPA DE LÓGICA · Python'),
             (650, GRAY_T, '#4A4F57', 'CAPA DE DATOS')]
    for y, fill, color, text in bands:
        ax.add_patch(FancyBboxPatch((bx, y), bw, bh, boxstyle='round,pad=0,rounding_size=14', facecolor=fill,
                                    edgecolor='none'))
        label(ax, bx + 24, y + 26, text, color=color, size=12, ha='left', bold=True)

    cols = [300, 645, 990]
    cw, ch = 310, 110
    rows = [
        (190, [('Escáner', 'inicia el análisis'), ('Hallazgos', 'veredicto y corrección'),
               ('Dashboard', 'métricas y gráficos')], '#2F6FB0', CARD, INK),
        (445, [('Cliente GitHub', 'commits y diffs'), ('Detector', '28 regex + fingerprint'),
               ('Modelos ML', 'Random Forest · IF · K-Means')], TERRA, CARD, INK),
        (700, [('Configuración', 'config.py y .env'), ('Gestor de BD', 'db_manager.py'),
               ('PostgreSQL 18', '6 tablas')], '#8A949C', CARD, INK),
    ]
    for y, items, edge, fill, color in rows:
        for x, (title, sub) in zip(cols, items):
            dark = title == 'Modelos ML'
            box(ax, x, y, cw, ch, title, sub, fill=INK if dark else fill, edge=INK if dark else edge,
                title_color=CARD if dark else color, sub_color='#C8D2D6' if dark else BODY, size=15, sub_size=12,
                mono_sub=(sub == 'db_manager.py'))
    # Flujo dentro de la capa de lógica
    for x in (cols[0] + cw, cols[1] + cw):
        arrow(ax, x, 500, x + 35, 500, color=TERRA)
    arrow(ax, cols[1] + cw, 755, cols[2], 755, color=MUTED, both=True)
    # Entre capas
    arrow(ax, 800, 330, 800, 395, both=True)
    label(ax, 815, 362, 'solicitudes del usuario y resultados', color=BODY, size=11.5, ha='left')
    arrow(ax, 800, 585, 800, 650, both=True)
    label(ax, 815, 617, 'guarda y consulta los hallazgos', color=BODY, size=11.5, ha='left')

    actor(ax, 135, 170, 'Auditor')
    arrow(ax, 172, 225, bx, 235, color=INK)
    label(ax, 220, 212, 'usa', color=MUTED, size=11)
    box(ax, 1395, 440, 170, 120, 'API de GitHub', 'externo', fill=CARD, edge=INK, dashed=True, size=13)
    arrow(ax, bx + bw, 500, 1395, 500, color=INK, both=True)
    label(ax, 1362, 482, 'HTTPS', color=MUTED, size=11)
    save(fig, '2_arquitectura_capas.png')


# ---------------------------------------------------------------------------
# 3. Módulos / componentes
# ---------------------------------------------------------------------------
def modulos():
    fig, ax = canvas('Diagrama de módulos', 'Cómo está organizado el código de CyberGuard')
    box(ax, 640, 135, 320, 70, 'main.py', 'punto de entrada', fill=GRAY_T, edge='#8A949C', size=13, sub_size=11)
    arrow(ax, 800, 205, 800, 245)
    box(ax, 560, 245, 480, 110, 'gui/main_gui.py', 'Interfaz: Escáner · Hallazgos · Dashboard', fill=INK, edge=INK,
        title_color=CARD, sub_color='#C8D2D6', size=16, sub_size=12.5)

    cols = [60, 440, 820, 1200]
    w = 340
    mods = [('utils/github_api.py', 'descarga commits y diffs'),
            ('utils/credential_detector.py', 'regex, línea real y fingerprint'),
            ('models/credential_classifier.py', 'Random Forest: real o no'),
            ('database/db_manager.py', 'guarda y consulta datos')]
    deps = [('API REST de GitHub', 'token personal en .env'), ('config/config.py', 'los 28 patrones regex'),
            ('models/training_data/', '771 ejemplos etiquetados'), ('PostgreSQL 18', '6 tablas')]
    centers = [x + w / 2 for x in cols]
    # Bus GUI -> módulos
    ax.plot([800, 800], [355, 410], color=INK, lw=1.6)
    ax.plot([centers[0], centers[-1]], [410, 410], color=INK, lw=1.6)
    for cx in centers:
        arrow(ax, cx, 410, cx, 445)
    for x, cx, (title, sub), (dtitle, dsub) in zip(cols, centers, mods, deps):
        box(ax, x, 445, w, 120, title.split('/')[-1] if title.endswith('.py') else title, sub, edge=TEAL,
            size=14, sub_size=12)
        label(ax, cx, 462, title.rsplit('/', 1)[0] + '/', color=MUTED, size=10.5)
        arrow(ax, cx, 565, cx, 650, color=MUTED, dashed=True)
        box(ax, x, 650, w, 110, dtitle, dsub, fill=GRAY_T, edge='#8A949C', dashed=True, size=13.5, sub_size=12)
    label(ax, 60, 820, 'Flecha continua: llamada entre módulos · flecha punteada: recurso del que depende',
          color=MUTED, size=11.5, ha='left')
    label(ax, 60, 848, 'Scripts de evaluación en scripts/ (benchmark, prueba ciega, tiempos) y modelos Isolation Forest '
          'y K-Means en models/', color=MUTED, size=11.5, ha='left')
    save(fig, '3_modulos.png')


# ---------------------------------------------------------------------------
# 4. Entidad-relación
# ---------------------------------------------------------------------------
def entidad_relacion():
    fig, ax = canvas('Modelo entidad-relación', 'Base de datos PostgreSQL de CyberGuard · 6 tablas')

    def table(x, y, w, name, fields, dashed=False):
        row_h, head_h = 34, 48
        h = head_h + row_h * len(fields) + 14
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=10', facecolor=CARD,
                                    edgecolor='#8A949C' if dashed else INK, linewidth=1.8,
                                    linestyle='--' if dashed else '-'))
        ax.add_patch(Rectangle((x + 1, y + 1), w - 2, head_h - 1, facecolor=GRAY_T if dashed else INK,
                               edgecolor='none'))
        ax.text(x + 16, y + head_h / 2, name, fontsize=13.5, fontweight='bold', family='Consolas',
                color=INK if dashed else CARD, va='center')
        for i, (key, field) in enumerate(fields):
            yy = y + head_h + 10 + row_h * i + row_h / 2
            if key:
                ax.text(x + 16, yy, key, fontsize=10.5, fontweight='bold', color=TERRA if key == 'PK' else TEAL,
                        va='center')
            ax.text(x + 58, yy, field, fontsize=12, family='Consolas', color=INK, va='center')
        return h

    w = 310
    xs = [60, 455, 850, 1245]
    y0 = 200
    table(xs[0], y0, w, 'repositories', [('PK', 'repo_id'), ('', 'repo_owner'), ('', 'repo_name'),
                                         ('', 'risk_level')])
    hc = table(xs[1], y0, w, 'commits', [('PK', 'commit_id'), ('FK', 'repo_id'), ('', 'commit_sha'),
                                         ('', 'author_name'), ('', 'commit_date')])
    table(xs[2], y0, w, 'credentials_detected', [('PK', 'credential_id'), ('FK', 'commit_id'),
                                                 ('UQ', 'fingerprint'), ('', 'ml_prediction'),
                                                 ('', 'manual_label')])
    table(xs[3], y0, w, 'credential_occurrences', [('PK', 'occurrence_id'), ('FK', 'credential_id'),
                                                   ('FK', 'commit_id'), ('', 'line_number')])
    table(xs[1], 600, w, 'commit_features', [('PK', 'feature_id'), ('FK', 'commit_id'), ('', 'files_modified'),
                                             ('', 'code_additions')])
    table(xs[3], 600, w, 'ml_model_results', [('PK', 'model_id'), ('', 'model_name'), ('', 'f1_score')],
          dashed=True)

    ry = y0 + 24      # las relaciones salen a la altura del encabezado
    for a, b in ((0, 1), (1, 2), (2, 3)):
        x1, x2 = xs[a] + w, xs[b]
        arrow(ax, x1, ry, x2, ry, head=False, lw=1.8)
        label(ax, x1 + 12, ry - 16, '1', color=TERRA, size=12, bold=True, ha='left')
        label(ax, x2 - 12, ry - 16, 'N', color=TERRA, size=12, bold=True, ha='right')
    # commits 1 — 1 commit_features
    cx = xs[1] + w / 2
    arrow(ax, cx, y0 + hc, cx, 600, head=False, lw=1.8)
    label(ax, cx + 12, (y0 + hc + 600) / 2, '1 : 1', color=TERRA, size=12, bold=True, ha='left')
    # credential_occurrences N — 1 commits (por arriba de las tablas)
    top = y0 - 40
    ax.plot([xs[3] + w / 2, xs[3] + w / 2], [y0, top], color=TEAL, lw=1.6)
    ax.plot([xs[3] + w / 2, xs[1] + w / 2], [top, top], color=TEAL, lw=1.6)
    ax.plot([xs[1] + w / 2, xs[1] + w / 2], [top, y0], color=TEAL, lw=1.6)
    label(ax, xs[3] + w / 2 + 12, top + 18, 'N', color=TEAL, size=12, bold=True, ha='left')
    label(ax, xs[1] + w / 2 + 12, top + 18, '1', color=TEAL, size=12, bold=True, ha='left')
    label(ax, (xs[1] + xs[3]) / 2 + w / 2, top - 14, 'cada aparición de un hallazgo en un commit', color=TEAL, size=11)

    label(ax, 850, 640, 'PK llave primaria · FK llave foránea · UQ valor único', color=MUTED, size=11.5, ha='left')
    label(ax, 850, 672, 'Borrar un repositorio elimina en cascada', color=MUTED, size=11.5, ha='left')
    label(ax, 850, 700, 'sus commits, hallazgos y ocurrencias', color=MUTED, size=11.5, ha='left')
    label(ax, 850, 742, 'ml_model_results guarda las métricas', color=MUTED, size=11.5, ha='left')
    label(ax, 850, 770, 'de cada entrenamiento (sin relaciones)', color=MUTED, size=11.5, ha='left')
    save(fig, '4_entidad_relacion.png')


if __name__ == '__main__':
    casos_de_uso()
    arquitectura_capas()
    modulos()
    entidad_relacion()
