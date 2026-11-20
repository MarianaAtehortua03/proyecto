"""
Interfaz Gráfica de Usuario para GitHub Analyzer
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime
import threading
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import GUI_CONFIG
from database.db_manager import db_manager
from utils.github_api import github_analyzer
from utils.credential_detector import credential_detector
from models.credential_classifier import credential_classifier
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np


class GitHubAnalyzerGUI:
    """Interfaz gráfica principal de la aplicación"""
    
    def __init__(self, root):
        """Inicializa la GUI"""
        self.root = root
        self.root.title(GUI_CONFIG['window_title'])
        self.root.geometry(GUI_CONFIG['window_size'])
        
        # Variables
        self.analysis_running = False
        self.current_repo_id = None
        
        # Configurar estilo
        self.setup_style()
        
        # Crear interfaz
        self.create_menu()
        self.create_widgets()
        
        # Verificar conexión inicial
        self.check_connections()

        # El modelo viene entrenado de fábrica (conjunto semilla + correcciones del usuario)
        self.prepare_model()
    
    def setup_style(self):
        """Configura el estilo de la aplicación 'Cyber-Guard'"""
        self.root.configure(bg='#1e1e2e')
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colores Palette (Cyber-Guard)
        self.colors = {
            'bg_dark': '#1e1e2e',
            'bg_sidebar': '#11111b',
            'accent': '#cba6f7',
            'text': '#cdd6f4',
            'critical': '#f38ba8',
            'high': '#fab387',
            'medium': '#f9e2af',
            'success': '#a6e3a1'
        }

        # Estilo de Botones Sidebar
        style.configure('Sidebar.TButton', 
            font=('Segoe UI', 11), 
            padding=10, 
            background=self.colors['bg_sidebar'],
            foreground=self.colors['text']
        )
        
        # Estilo de Labels Dark
        style.configure('Dark.TLabel', background=self.colors['bg_dark'], foreground=self.colors['text'], font=('Segoe UI', 10))
        style.configure('DarkTitle.TLabel', background=self.colors['bg_dark'], foreground=self.colors['accent'], font=('Segoe UI', 18, 'bold'))
        
        # Estilo de Treeview (Resultados)
        style.configure("Treeview", 
            background="#2e2e3e", 
            foreground="white", 
            fieldbackground="#2e2e3e",
            font=('Segoe UI', 9),
            rowheight=25
        )
        style.map("Treeview", background=[('selected', self.colors['accent'])], foreground=[('selected', 'black')])
        style.configure("Treeview.Heading", background="#11111b", foreground=self.colors['accent'], font=('Segoe UI', 10, 'bold'))

        # Listas desplegables (filtros) en modo oscuro
        style.configure('TCombobox', fieldbackground='#2e2e3e', background='#2e2e3e',
                        foreground=self.colors['text'], arrowcolor=self.colors['accent'],
                        bordercolor='#45475a', lightcolor='#2e2e3e', darkcolor='#2e2e3e')
        style.map('TCombobox',
                  fieldbackground=[('readonly', '#2e2e3e')],
                  foreground=[('readonly', self.colors['text'])],
                  selectbackground=[('readonly', '#2e2e3e')],
                  selectforeground=[('readonly', self.colors['text'])])
        self.root.option_add('*TCombobox*Listbox.background', '#2e2e3e')
        self.root.option_add('*TCombobox*Listbox.foreground', self.colors['text'])
        self.root.option_add('*TCombobox*Listbox.selectBackground', self.colors['accent'])
        self.root.option_add('*TCombobox*Listbox.selectForeground', self.colors['bg_dark'])
    
    def create_menu(self):
        """Crea el menú de la aplicación"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menú Archivo
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Exportar Resultados", command=self.export_results)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.quit)
        
# Menú Ayuda
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
        help_menu.add_command(label="Información del modelo ML", command=self.show_model_info)
        help_menu.add_command(label="Acerca de", command=self.show_about)
    
    def create_widgets(self):
        """Crea los widgets de la interfaz con Sidebar"""
        # --- Sidebar (Izquierda) ---
        self.sidebar = tk.Frame(self.root, bg=self.colors['bg_sidebar'], width=200)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        # Título en Sidebar
        tk.Label(self.sidebar, text="CYBER\nGUARD", bg=self.colors['bg_sidebar'], fg=self.colors['accent'], 
                 font=('Impact', 22), pady=20).pack()
        
        tk.Frame(self.sidebar, bg=self.colors['accent'], height=2).pack(fill='x', padx=20, pady=10)

        # Botones de Navegación
        nav_items = [
            ("🔍 Escáner", "scanner"),
            ("📋 Hallazgos", "results"),
            ("📊 Dashboard", "stats")
        ]
        
        self.nav_buttons = {}
        for text, screen in nav_items:
            btn = tk.Button(self.sidebar, text=text, bg=self.colors['bg_sidebar'], fg=self.colors['text'],
                            font=('Segoe UI', 11), bd=0, activebackground=self.colors['accent'], 
                            activeforeground=self.colors['bg_dark'], anchor='w', padx=20, pady=10,
                            command=lambda s=screen: self.show_screen(s))
            btn.pack(fill='x')
            self.nav_buttons[screen] = btn

        # --- Contenedor Principal (Derecha) ---
        self.main_container = tk.Frame(self.root, bg=self.colors['bg_dark'])
        self.main_container.pack(side='right', fill='both', expand=True)

        # Crear todas las pantallas (ocultas)
        self.screens = {}
        self.create_analysis_screen()
        self.create_results_screen()
        self.create_stats_screen()

        # Mostrar pantalla inicial
        self.show_screen("scanner")

        # Barra de estado
        self.create_status_bar()

    def show_screen(self, screen_name):
        """Alterna entre las pantallas de la interfaz"""
        for name, frame in self.screens.items():
            frame.pack_forget()
            self.nav_buttons[name].config(bg=self.colors['bg_sidebar'], fg=self.colors['text'])
        
        self.screens[screen_name].pack(fill='both', expand=True)
        self.nav_buttons[screen_name].config(bg=self.colors['accent'], fg=self.colors['bg_dark'])

        if screen_name == 'stats':
            self.update_statistics()

    
    def create_analysis_screen(self):
        """Crea la pantalla de escaneo"""
        screen = tk.Frame(self.main_container, bg=self.colors['bg_dark'])
        self.screens['scanner'] = screen
        
        header = tk.Frame(screen, bg=self.colors['bg_dark'], pady=20)
        header.pack(fill='x', padx=20)
        ttk.Label(header, text="Escáner de Seguridad de GitHub", style='DarkTitle.TLabel').pack(side='left')

        # Panel de Entrada Estilizado
        input_frame = tk.LabelFrame(screen, text=' Configuración de Análisis ', bg=self.colors['bg_dark'], 
                                   fg=self.colors['accent'], font=('Segoe UI', 10, 'bold'), padx=20, pady=20)
        input_frame.pack(fill='x', padx=20, pady=10)
        
        # Helper para labels e inputs en dark mode
        def create_field(row, label_text, default=''):
            tk.Label(input_frame, text=label_text, bg=self.colors['bg_dark'], fg=self.colors['text'], font=('Segoe UI', 10)).grid(row=row, column=0, sticky='w', pady=8)
            entry = tk.Entry(input_frame, bg='#2e2e3e', fg='white', insertbackground='white', bd=1, relief='flat', width=35)
            entry.insert(0, default)
            entry.grid(row=row, column=1, padx=20, pady=8, sticky='w')
            return entry

        self.owner_entry = create_field(0, "Propietario / Organización (Ej: Google)")
        self.repo_entry = create_field(1, "Nombre del Repositorio")
        self.branch_entry = create_field(2, "Rama (Branch)", "main")
        self.max_commits_entry = create_field(3, "Límite de Commits", "100")
        
        # Botón de Inicio con estilo neón
        self.analyze_btn = tk.Button(input_frame, text="🚀 INICIAR ESCANEO", bg=self.colors['accent'], fg=self.colors['bg_dark'],
                                    font=('Segoe UI', 11, 'bold'), bd=0, padx=30, pady=10, cursor='hand2',
                                    command=self.start_analysis)
        self.analyze_btn.grid(row=4, column=0, columnspan=2, pady=20)
        
        # Progress bar dark
        self.progress = ttk.Progressbar(screen, mode='indeterminate')
        self.progress.pack(fill='x', padx=25, pady=5)
        
        # Área de Terminal de Log
        log_frame = tk.LabelFrame(screen, text=' Terminal de Operaciones ', bg=self.colors['bg_dark'], 
                                 fg=self.colors['accent'], font=('Segoe UI', 10, 'bold'), padx=10, pady=10)
        log_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, bg='#11111b', fg='#a6e3a1', font=('Consolas', 10),
                                               insertbackground='white', bd=0, padx=10, pady=10)
        self.log_text.pack(fill='both', expand=True)
    
    def create_results_screen(self):
        """Crea la pantalla de resultados"""
        screen = tk.Frame(self.main_container, bg=self.colors['bg_dark'])
        self.screens['results'] = screen
        
        header = tk.Frame(screen, bg=self.colors['bg_dark'], pady=20)
        header.pack(fill='x', padx=20)
        ttk.Label(header, text="Hallazgos de Seguridad", style='DarkTitle.TLabel').pack(side='left')
        
        # Controles
        control_frame = tk.Frame(screen, bg=self.colors['bg_dark'])
        control_frame.pack(fill='x', padx=20, pady=10)
        
        def create_action_btn(text, cmd):
            return tk.Button(control_frame, text=text, bg='#2e2e3e', fg=self.colors['text'],
                            font=('Segoe UI', 10), bd=0, padx=15, pady=5, cursor='hand2',
                            activebackground=self.colors['accent'], command=cmd)

        create_action_btn("🔄 Actualizar Tabla", self.load_results).pack(side='left', padx=5)
        create_action_btn("📥 Exportar a CSV", self.export_to_csv).pack(side='left', padx=5)

        # Filtro por estado de revisión
        tk.Label(control_frame, text="Mostrar:", bg=self.colors['bg_dark'], fg=self.colors['text'],
                 font=('Segoe UI', 10)).pack(side='left', padx=(20, 5))
        self.results_filter = ttk.Combobox(
            control_frame, state='readonly', width=24,
            values=['Todos', 'Credenciales reales', 'Falsos positivos', 'Corregidos por mí']
        )
        self.results_filter.current(0)
        self.results_filter.pack(side='left')
        self.results_filter.bind('<<ComboboxSelected>>', lambda e: self.load_results())

        # Corrección del veredicto (el modelo se reentrena con ella)
        label_frame = tk.LabelFrame(screen, text=' ¿Algún veredicto es incorrecto? Selecciona la fila y corrígelo ',
                                    bg=self.colors['bg_dark'], fg=self.colors['accent'],
                                    font=('Segoe UI', 10, 'bold'), padx=10, pady=8)
        label_frame.pack(fill='x', padx=20, pady=5)

        def create_label_btn(text, color, label):
            return tk.Button(label_frame, text=text, bg=color, fg=self.colors['bg_dark'],
                             font=('Segoe UI', 10, 'bold'), bd=0, padx=15, pady=5, cursor='hand2',
                             command=lambda: self.label_selected(label))

        create_label_btn("🚨 Es una credencial real", self.colors['critical'], 1).pack(side='left', padx=5)
        create_label_btn("✅ Es un falso positivo", self.colors['success'], 0).pack(side='left', padx=5)
        self.correction_status = tk.Label(label_frame, text='', bg=self.colors['bg_dark'], fg=self.colors['text'],
                                          font=('Segoe UI', 10))
        self.correction_status.pack(side='left', padx=20)

        # Tabla de resultados
        table_frame = tk.Frame(screen, bg=self.colors['bg_dark'])
        table_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        vsb = ttk.Scrollbar(table_frame, orient="vertical")
        vsb.pack(side='right', fill='y')
        hsb = ttk.Scrollbar(table_frame, orient="horizontal")
        hsb.pack(side='bottom', fill='x')
        
        columns = ('ID', 'Veredicto', 'Confianza', 'Tipo', 'Repositorio', 'Archivo', 'Línea',
                   'Severidad', 'Commit SHA', 'Autor', 'Fecha')
        self.results_tree = ttk.Treeview(table_frame, columns=columns, show='headings', selectmode='extended',
                                       yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.config(command=self.results_tree.yview)
        hsb.config(command=self.results_tree.xview)
        
        widths = {'ID': 50, 'Línea': 55, 'Severidad': 80, 'Confianza': 90, 'Archivo': 220,
                  'Veredicto': 190}
        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=widths.get(col, 110))

        self.results_tree.pack(fill='both', expand=True)
        self.results_tree.bind('<<TreeviewSelect>>', self.show_finding_detail)

        # Detalle del hallazgo seleccionado (contexto para decidir la etiqueta)
        self.finding_detail = tk.Label(screen, text='Selecciona un hallazgo para ver la línea donde se encontró.',
                                       bg='#11111b', fg='#f5c2e7', font=('Consolas', 10), anchor='w',
                                       justify='left', wraplength=1100, padx=10, pady=8)
        self.finding_detail.pack(fill='x', padx=20, pady=(0, 10))
        self.findings_by_id = {}

        # Tags (Adaptados a Dark Mode)
        self.results_tree.tag_configure('CRITICAL', background='#4a1414', foreground='#ffcccc')
        self.results_tree.tag_configure('HIGH', background='#4a2b10', foreground='#ffe6cc')
        self.results_tree.tag_configure('MEDIUM', background='#4a4a10', foreground='#ffffcc')
        self.results_tree.tag_configure('FALSE_POSITIVE', background='#2e2e3e', foreground='#7f849c')

    def create_stats_screen(self):
        """Crea la pantalla de Dashboard: KPIs + embudo, tipos, repositorios y archivos"""
        screen = tk.Frame(self.main_container, bg=self.colors['bg_dark'])
        self.screens['stats'] = screen

        header = tk.Frame(screen, bg=self.colors['bg_dark'], pady=20)
        header.pack(fill='x', padx=20)
        ttk.Label(header, text="Dashboard de Seguridad", style='DarkTitle.TLabel').pack(side='left')

        # Filtro: todos los repositorios o uno en específico
        self.ALL_REPOS = 'Todos los repositorios'
        self.dashboard_repo_ids = {}
        # Borrar el repositorio seleccionado (con sus commits y hallazgos)
        tk.Button(header, text="🗑 Borrar repositorio", bg='#45475a', fg=self.colors['critical'],
                  font=('Segoe UI', 10, 'bold'), bd=0, padx=14, pady=4, cursor='hand2',
                  activebackground=self.colors['critical'], activeforeground=self.colors['bg_dark'],
                  command=self.delete_selected_repository).pack(side='right', padx=(10, 0))
        self.dashboard_repo_filter = ttk.Combobox(header, state='readonly', width=40, values=[self.ALL_REPOS])
        self.dashboard_repo_filter.current(0)
        self.dashboard_repo_filter.pack(side='right')
        self.dashboard_repo_filter.bind('<<ComboboxSelected>>', lambda e: self.update_statistics())
        tk.Label(header, text="Repositorio:", bg=self.colors['bg_dark'], fg=self.colors['text'],
                 font=('Segoe UI', 10)).pack(side='right', padx=(0, 8))

        # KPIs
        kpi_frame = tk.Frame(screen, bg=self.colors['bg_dark'])
        kpi_frame.pack(fill='x', padx=20, pady=(0, 10))

        self.stats_labels = {}
        self.stats_sublabels = {}
        self.stats_titles = {}
        kpis = [
            ('Repositorios', 'repos', 'analizados', self.colors['text']),
            ('Hallazgos únicos', 'unique', 'tras fingerprinting', self.colors['text']),
            ('Credenciales reales', 'real', 'según el modelo ML', self.colors['critical']),
            ('Falsos positivos descartados', 'fp_pct', '', self.colors['success']),
        ]
        card_bg = '#24273a'
        for label, key, sub, color in kpis:
            card = tk.Frame(kpi_frame, bg=card_bg, padx=18, pady=12)
            card.pack(side='left', expand=True, fill='both', padx=5)
            title = tk.Label(card, text=label, bg=card_bg, fg=self.colors['accent'],
                             font=('Segoe UI', 10, 'bold'), anchor='w')
            title.pack(fill='x')
            self.stats_titles[key] = title
            value = tk.Label(card, text='0', bg=card_bg, fg=color, font=('Segoe UI', 24, 'bold'), anchor='w')
            value.pack(fill='x')
            sub_label = tk.Label(card, text=sub, bg=card_bg, fg='#7f849c', font=('Segoe UI', 9), anchor='w')
            sub_label.pack(fill='x')
            self.stats_labels[key] = value
            self.stats_sublabels[key] = sub_label

        # Gráficos en cuadrícula 2x2
        charts = tk.Frame(screen, bg=self.colors['bg_dark'])
        charts.pack(fill='both', expand=True, padx=20, pady=(0, 15))
        charts.columnconfigure((0, 1), weight=1, uniform='col')
        charts.rowconfigure((0, 1), weight=1, uniform='row')

        self.chart_frames = {}
        titles = [
            ('funnel', ' Embudo de detección '),
            ('types', ' Credenciales reales por tipo '),
            ('repos', ' Por repositorio '),
            ('files', ' Dónde se filtran (tipo de archivo) '),
        ]
        for idx, (key, title) in enumerate(titles):
            frame = tk.LabelFrame(charts, text=title, bg=self.colors['bg_dark'], fg=self.colors['accent'],
                                  font=('Segoe UI', 10, 'bold'), padx=5, pady=5)
            frame.grid(row=idx // 2, column=idx % 2, sticky='nsew', padx=5, pady=5)
            self.chart_frames[key] = frame

    def create_status_bar(self):
        """Crea la barra de estado con estilo Cyber"""
        self.status_bar = tk.Label(
            self.root, 
            text=' 🛡️ Sistema Cyber-Guard Operativo | Listo para Escaneo', 
            bg=self.colors['bg_sidebar'],
            fg=self.colors['accent'],
            font=('Segoe UI', 9),
            relief=tk.FLAT, 
            anchor='w',
            padx=10,
            pady=5
        )
        # Antes del sidebar para que ocupe todo el ancho inferior de la ventana
        self.status_bar.pack(side='bottom', fill='x', before=self.sidebar)
    
    def log(self, message):
        """Agrega un mensaje al log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert('end', f'[{timestamp}] {message}\n')
        self.log_text.see('end')
        self.root.update_idletasks()
    
    def update_status(self, message):
        """Actualiza la barra de estado"""
        self.status_bar.config(text=message)
        self.root.update_idletasks()
    
    def check_connections(self):
        """Verifica las conexiones iniciales"""
        try:
            # Verificar base de datos
            repos = db_manager.get_repository_summary()
            self.log(f"✓ Conexión a PostgreSQL exitosa ({len(repos)} repositorios)")
            
            # Verificar GitHub API
            if github_analyzer.validate_token():
                rate_limit = github_analyzer.get_rate_limit()
                self.log(f"✓ Token de GitHub válido ({rate_limit['remaining']} requests disponibles)")
            else:
                self.log("⚠ Token de GitHub no configurado o inválido")
            
            self.update_status("Conexiones verificadas")
            
        except Exception as e:
            self.log(f"✗ Error verificando conexiones: {str(e)}")
            messagebox.showerror("Error", f"Error de conexión: {str(e)}")
    
    def start_analysis(self):
        """Inicia el análisis del repositorio"""
        if self.analysis_running:
            messagebox.showwarning("Advertencia", "Ya hay un análisis en ejecución")
            return
        
        owner = self.owner_entry.get().strip()
        repo = self.repo_entry.get().strip()
        branch = self.branch_entry.get().strip() or 'main'
        
        if not owner or not repo:
            messagebox.showerror("Error", "Debe ingresar propietario y repositorio")
            return
        
        try:
            max_commits = int(self.max_commits_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Máx. commits debe ser un número")
            return
        
        # Ejecutar en thread separado
        self.analysis_running = True
        self.analyze_btn.config(state='disabled')
        self.progress.start()
        
        thread = threading.Thread(
            target=self.run_analysis,
            args=(owner, repo, branch, max_commits),
            daemon=True
        )
        thread.start()
    
    def run_analysis(self, owner, repo, branch, max_commits):
        """Ejecuta el análisis completo"""
        try:
            self.log(f"\n{'='*60}")
            self.log(f"Iniciando análisis de {owner}/{repo}")
            self.log(f"{'='*60}\n")
            
            # 1. Obtener información del repositorio
            self.log("📦 Obteniendo información del repositorio...")
            repo_info = github_analyzer.get_repository_info(owner, repo)
            
            if not repo_info:
                self.log("✗ No se pudo obtener información del repositorio")
                return
            
            self.log(f"✓ Repositorio: {repo_info['full_name']}")
            self.log(f"  Lenguaje: {repo_info['language']}")
            self.log(f"  Estrellas: {repo_info['stars']}")
            
            # Guardar en BD
            repo_id = db_manager.insert_repository(
                repo_info['name'],
                repo_info['owner'],
                repo_info['url']
            )
            self.current_repo_id = repo_id
            self.log(f"✓ Repositorio guardado (ID: {repo_id})")
            
            # 2. Obtener commits
            self.log(f"\n📝 Obteniendo commits (máx: {max_commits})...")
            commits = github_analyzer.get_commits(owner, repo, branch, max_commits)
            self.log(f"✓ Obtenidos {len(commits)} commits")
            
            # 3. Analizar cada commit
            self.log(f"\n🔍 Analizando commits...")
            total_credentials = 0
            repeated_credentials = 0
            unique_fingerprints = set()  # Hallazgos únicos encontrados en este análisis
            new_credential_ids = []

            for idx, commit in enumerate(commits, 1):
                self.log(f"  Analizando commit {idx}/{len(commits)}: {commit['sha'][:7]}...")
                
                # Obtener detalles del commit
                commit_details = github_analyzer.get_commit_details(
                    owner, repo, commit['sha']
                )
                
                if not commit_details:
                    continue
                
                # Detectar credenciales
                commit['files_changed'] = commit_details['files_changed']
                commit['additions'] = commit_details['additions']
                commit['deletions'] = commit_details['deletions']
                
                credentials_found = []
                
                # Analizar diff de cada archivo (ya viene en los detalles del commit,
                # así se evita una segunda petición a la API por commit)
                for file_data in commit_details.get('files', []):
                    patch = file_data.get('patch', '')
                    if patch:
                        detections = credential_detector.detect_in_commit_diff(patch, file_data['filename'])
                        credentials_found.extend(detections)
                
                # Calcular riesgo
                has_credentials = len(credentials_found) > 0
                risk_score = self.calculate_risk_score(
                    has_credentials, 
                    len(credentials_found),
                    commit_details
                )
                
                commit['has_credentials'] = has_credentials
                commit['risk_score'] = risk_score
                
                # Guardar commit en BD
                commit_id = db_manager.insert_commit(repo_id, commit)
                
                # Guardar credenciales detectadas (sin duplicar por fingerprint)
                for cred in credentials_found:
                    cred['fingerprint'] = credential_detector.compute_fingerprint(
                        repo_info['owner'], repo_info['name'], cred['file_path'], cred['secret']
                    )
                    credential_id, is_new = db_manager.insert_credential(commit_id, cred)
                    unique_fingerprints.add(cred['fingerprint'])
                    if is_new:
                        total_credentials += 1
                        new_credential_ids.append(credential_id)
                    else:
                        repeated_credentials += 1
                
                # Extraer y guardar características para ML
                features = self.extract_commit_features(commit, commit_details)
                db_manager.insert_commit_features(commit_id, features)
            
            # Clasificar los hallazgos nuevos con el modelo, si ya está entrenado
            if new_credential_ids and credential_classifier.is_trained:
                self.predict_credentials(new_credential_ids)
                self.log(f"🧠 {len(new_credential_ids)} hallazgos nuevos clasificados por el modelo ML")

            # 4. Actualizar estadísticas del repositorio
            risk_level = self.determine_risk_level(len(unique_fingerprints), len(commits))
            db_manager.update_repository_stats(
                repo_id, 
                len(commits), 
                len(unique_fingerprints),
                risk_level
            )
            
            # Resumen
            self.log(f"\n{'='*60}")
            self.log(f"✓ ANÁLISIS COMPLETADO")
            self.log(f"{'='*60}")
            self.log(f"  Total commits analizados: {len(commits)}")
            self.log(f"  Credenciales nuevas: {total_credentials}")
            self.log(f"  Ya registradas (fingerprint repetido): {repeated_credentials}")
            self.log(f"  Nivel de riesgo: {risk_level}")
            self.log(f"{'='*60}\n")
            
            # Cargar resultados en la tabla
            self.root.after(0, self.load_results)
            self.root.after(0, self.update_statistics)
            
            self.root.after(
                0, 
                messagebox.showinfo, 
                "Análisis Completado", 
                f"Se analizaron {len(commits)} commits.\n"
                f"Hallazgos únicos: {len(unique_fingerprints)} "
                f"({total_credentials} nuevos, {len(unique_fingerprints) - total_credentials} ya registrados)."
            )
            
        except Exception as e:
            self.log(f"\n✗ ERROR: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            self.root.after(
                0, 
                messagebox.showerror, 
                "Error", 
                f"Error durante el análisis: {str(e)}"
            )
        
        finally:
            self.analysis_running = False
            self.root.after(0, self.analyze_btn.config, {'state': 'normal'})
            self.root.after(0, self.progress.stop)
            self.root.after(0, self.update_status, "Análisis completado")
    
    def calculate_risk_score(self, has_credentials, num_credentials, commit_details):
        """Calcula el score de riesgo de un commit"""
        score = 0.0
        
        if has_credentials:
            score += 0.5 + (num_credentials * 0.1)
        
        # Factores adicionales
        if commit_details['additions'] > 100:
            score += 0.1
        
        if commit_details['files_changed'] > 10:
            score += 0.1
        
        return min(score, 1.0)
    
    def determine_risk_level(self, total_credentials, total_commits):
        """Determina el nivel de riesgo del repositorio"""
        if total_credentials == 0:
            return 'LOW'
        
        ratio = total_credentials / total_commits
        
        if ratio > 0.1:
            return 'CRITICAL'
        elif ratio > 0.05:
            return 'HIGH'
        elif ratio > 0.01:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def extract_commit_features(self, commit, commit_details):
        """Extrae características de un commit para ML"""
        message = commit.get('message', '')
        
        # --- INTEGRACIÓN REGEX + ML ---
        regex_detections = credential_detector.detect_in_text(message)
        regex_count = len(regex_detections)
        
        # Mapear severidad máxima a valor numérico
        severity_map = {'CRITICAL': 3, 'HIGH': 2, 'MEDIUM': 1, 'NONE': 0}
        max_severity = 0
        for det in regex_detections:
            sev_val = severity_map.get(det['severity'], 0)
            if sev_val > max_severity:
                max_severity = sev_val
        
        # Verificar archivos sensibles
        is_sens_file = any(
            credential_detector.is_sensitive_file(f['filename']) 
            for f in commit_details.get('files', [])
        )

        return {
            'has_suspicious_keywords': credential_detector.has_suspicious_keywords(message),
            'regex_detected_count': regex_count,
            'max_regex_severity': max_severity,
            'is_sensitive_file': is_sens_file,
            'commit_hour': commit['date'].hour,
            'commit_day_of_week': commit['date'].weekday(),
            'message_length': len(message),
            'files_modified': commit_details['files_changed'],
            'code_additions': commit_details['additions'],
            'code_deletions': commit_details['deletions'],
            'has_config_files': any(
                credential_detector.is_sensitive_file(f['filename']) 
                for f in commit_details.get('files', [])
            ),
            'has_env_files': any(
                '.env' in f['filename'].lower() 
                for f in commit_details.get('files', [])
            ),
            # El clasificador de commits no predice durante el análisis
            'prediction_label': None,
            'prediction_confidence': None
        }
    
    def load_results(self):
        """Carga los resultados en la tabla"""
        try:
            # Limpiar tabla
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            
            # Obtener datos
            df = db_manager.get_credentials_dataframe()
            self.findings_by_id = {int(r['credential_id']): r for _, r in df.iterrows()}

            if df.empty:
                self.update_status("No hay credenciales detectadas")
                return

            # Veredicto final: la corrección del usuario manda sobre la predicción del modelo
            df['verdict'] = self.final_verdict(df)

            # Aplicar filtro
            selected_filter = self.results_filter.get()
            if selected_filter == 'Credenciales reales':
                df = df[df['verdict'] == 1]
            elif selected_filter == 'Falsos positivos':
                df = df[df['verdict'] == 0]
            elif selected_filter == 'Corregidos por mí':
                df = df[df['manual_label'].notna()]

            # Insertar en tabla
            for idx, row in df.iterrows():
                corrected = pd.notna(row.get('manual_label'))
                if pd.isna(row['verdict']):
                    verdict = "⏳ Analizando..."
                else:
                    verdict = "🚨 Credencial real" if int(row['verdict']) == 1 else "✅ Falso positivo"
                if corrected:
                    verdict += " (corregido)"
                confidence = row.get('ml_confidence')
                if corrected:
                    confidence_text = "Revisado"
                else:
                    confidence_text = '' if pd.isna(confidence) else f"{confidence:.0%}"
                values = (
                    row['credential_id'],
                    verdict,
                    confidence_text,
                    row['credential_type'],
                    f"{row['repo_owner']}/{row['repo_name']}",
                    row['file_path'][:60] if row['file_path'] else '',
                    row['line_number'],
                    row['severity'],
                    row['commit_sha'][:7],
                    (row.get('author_name') or '')[:30],
                    row['commit_date'].strftime('%Y-%m-%d') if pd.notna(row.get('commit_date')) else ''
                )

                # Los falsos positivos se muestran atenuados
                tag = row['severity'] if row['verdict'] != 0 else 'FALSE_POSITIVE'
                self.results_tree.insert('', 'end', iid=str(row['credential_id']), values=values, tags=(tag,))

            self.update_status(f"Mostrando {len(df)} hallazgos")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error cargando resultados: {str(e)}")

    def show_finding_detail(self, event=None):
        """Muestra la línea de código del hallazgo seleccionado"""
        selection = self.results_tree.selection()
        if not selection:
            return
        row = self.findings_by_id.get(int(selection[0]))
        if row is None:
            return
        line = row.get('line_content') or row.get('matched_pattern') or ''
        detail = (f"{row['repo_owner']}/{row['repo_name']} · {row['file_path']}:{row['line_number']}\n"
                  f"› {line}")
        if len(selection) > 1:
            detail += f"\n({len(selection)} hallazgos seleccionados)"
        self.finding_detail.config(text=detail)

    @staticmethod
    def final_verdict(df):
        """1 credencial real / 0 falso positivo: la corrección del usuario manda sobre el modelo"""
        return df['manual_label'].where(df['manual_label'].notna(), df['ml_prediction'])

    def prepare_model(self):
        """Entrena el modelo (conjunto semilla + correcciones) y clasifica todos los hallazgos"""
        try:
            try:
                user_labels = db_manager.get_credentials_dataframe()
            except Exception:
                user_labels = None  # Sin BD: se entrena solo con el conjunto semilla
            metrics = credential_classifier.train_default(user_labels)
            if user_labels is None:
                self.log(f"✓ Modelo ML listo (F1 {metrics['f1']:.2f})")
                return
            classified = self.predict_credentials()
            self.log(f"✓ Modelo ML listo: {metrics['algorithm_name']} (F1 {metrics['f1']:.2f}). "
                     f"{classified} hallazgos clasificados")
        except Exception as e:
            self.log(f"⚠ No se pudo preparar el modelo ML: {e}")

    def label_selected(self, label):
        """Guarda la corrección del usuario y reentrena el modelo en segundo plano"""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Selecciona al menos un hallazgo en la tabla")
            return
        try:
            ids = [int(iid) for iid in selection]
            db_manager.set_manual_label(ids, label)
            self.load_results()
            for iid in selection:
                if self.results_tree.exists(iid):
                    self.results_tree.selection_add(iid)
            name = 'credencial real' if label == 1 else 'falso positivo'
            self.correction_status.config(text=f"✓ {len(ids)} corregido(s) como {name}. Aprendiendo...")
            threading.Thread(target=self.retrain_after_correction, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Error guardando la corrección: {str(e)}")

    def retrain_after_correction(self):
        """Reentrena con la nueva corrección y vuelve a clasificar los hallazgos"""
        try:
            credential_classifier.train_default(db_manager.get_credentials_dataframe())
            self.predict_credentials()
            message = "✓ El modelo aprendió de tu corrección"
        except Exception as e:
            message = f"⚠ No se pudo reentrenar: {e}"
        self.root.after(0, self.correction_status.config, {'text': message})
        self.root.after(0, self.load_results)

    def predict_credentials(self, credential_ids=None):
        """Clasifica hallazgos con el modelo entrenado y guarda la predicción en la BD"""
        df = db_manager.get_credentials_dataframe(credential_ids)
        if df.empty:
            return 0
        predictions, confidence = credential_classifier.predict(df)
        db_manager.update_ml_predictions(list(zip(df['credential_id'], predictions, confidence)))
        return len(df)

    @staticmethod
    def file_category(file_path):
        """Agrupa un archivo en la categoría que usa el dashboard"""
        path = (file_path or '').lower()
        name = path.rsplit('/', 1)[-1]
        if '.env' in name or name == 'dockerfile' or 'docker-compose' in name:
            return '.env / Docker'
        if path.endswith(('.json', '.yml', '.yaml', '.ini', '.toml', '.properties', '.xml', '.cfg', '.conf')):
            return 'Configuración'
        if path.endswith(('.md', '.txt', '.rst', '.adoc', '.html')):
            return 'Documentación'
        if path.endswith(('.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.sh', '.go', '.rb', '.php',
                          '.cs', '.kt', '.swift', '.c', '.cpp', '.rs', '.ps1')):
            return 'Código fuente'
        return 'Otros'

    def update_statistics(self):
        """Actualiza los KPIs y los gráficos del Dashboard"""
        try:
            summary = db_manager.get_repository_summary()
            creds = db_manager.get_credentials_dataframe()

            # Refrescar la lista del filtro (puede haber repositorios nuevos)
            summary = summary.sort_values(['repo_owner', 'repo_name']) if not summary.empty else summary
            self.dashboard_repo_ids = {f"{r.repo_owner}/{r.repo_name}": int(r.repo_id)
                                       for r in summary.itertuples()}
            self.dashboard_repo_filter['values'] = [self.ALL_REPOS] + list(self.dashboard_repo_ids)
            selected = self.dashboard_repo_filter.get()
            if selected not in self.dashboard_repo_ids:
                selected = self.ALL_REPOS
                self.dashboard_repo_filter.set(selected)

            repo_id = self.dashboard_repo_ids.get(selected)
            if repo_id is not None:
                summary = summary[summary['repo_id'] == repo_id]
                owner, name = selected.split('/', 1)
                if not creds.empty:
                    creds = creds[(creds['repo_owner'] == owner) & (creds['repo_name'] == name)]
            detections = db_manager.get_detection_count(repo_id)
        except Exception as e:
            self.update_status(f"No se pudo actualizar el dashboard: {e}")
            return

        verdict = self.final_verdict(creds) if not creds.empty else pd.Series(dtype=float)
        unique = len(creds)
        real = int((verdict == 1).sum())
        false_pos = int((verdict == 0).sum())

        # KPIs (con un repositorio seleccionado, la primera tarjeta muestra sus commits)
        if repo_id is None:
            self.stats_titles['repos'].config(text='Repositorios')
            self.stats_labels['repos'].config(text=str(len(summary)))
            self.stats_sublabels['repos'].config(text='analizados')
        else:
            commits = int(summary['commits_analyzed'].iloc[0]) if not summary.empty else 0
            self.stats_titles['repos'].config(text='Commits analizados')
            self.stats_labels['repos'].config(text=str(commits))
            self.stats_sublabels['repos'].config(text=selected)
        self.stats_labels['unique'].config(text=str(unique))
        self.stats_labels['real'].config(text=str(real))
        self.stats_labels['fp_pct'].config(text=f"{false_pos / unique:.0%}" if unique else '0%')
        self.stats_sublabels['fp_pct'].config(text=f"{false_pos} de {unique} hallazgos")

        colors_real = self.colors['critical']
        colors_fp = '#585b70'

        # Embudo: detecciones regex -> únicos -> reales
        note = None
        if detections and unique:
            note = (f"-{1 - unique / detections:.0%} por duplicados  ·  "
                    f"-{false_pos / unique:.0%} por falsos positivos")
        self.draw_hbar(
            'funnel',
            ['Apariciones en commits', 'Únicos (fingerprint)', 'Reales (ML)'],
            [([detections, unique, real], ['#7f849c', '#89b4fa', colors_real], None)],
            note=note
        )

        real_df = creds[verdict == 1] if not creds.empty else creds
        fp_df = creds[verdict == 0] if not creds.empty else creds

        # Credenciales reales por tipo
        by_type = real_df['credential_type'].value_counts().head(6) if not real_df.empty else pd.Series(dtype=int)
        self.draw_hbar('types', list(by_type.index), [(list(by_type.values), colors_real, None)])

        # Por repositorio (real vs falso positivo), incluidos los repos sin hallazgos
        repos = list(summary['repo_name']) if not summary.empty else []
        real_counts = real_df['repo_name'].value_counts() if not real_df.empty else pd.Series(dtype=int)
        fp_counts = fp_df['repo_name'].value_counts() if not fp_df.empty else pd.Series(dtype=int)
        repos.sort(key=lambda r: -(real_counts.get(r, 0) + fp_counts.get(r, 0)))
        repos = repos[:6]
        self.draw_hbar('repos', repos, [
            ([int(real_counts.get(r, 0)) for r in repos], colors_real, 'Real'),
            ([int(fp_counts.get(r, 0)) for r in repos], colors_fp, 'Falso positivo'),
        ])

        # Tipo de archivo (real vs falso positivo)
        order = ['Código fuente', '.env / Docker', 'Configuración', 'Documentación', 'Otros']
        real_cat = real_df['file_path'].map(self.file_category).value_counts() if not real_df.empty else pd.Series(dtype=int)
        fp_cat = fp_df['file_path'].map(self.file_category).value_counts() if not fp_df.empty else pd.Series(dtype=int)
        cats = [c for c in order if real_cat.get(c, 0) + fp_cat.get(c, 0) > 0]
        self.draw_hbar('files', cats, [
            ([int(real_cat.get(c, 0)) for c in cats], colors_real, 'Real'),
            ([int(fp_cat.get(c, 0)) for c in cats], colors_fp, 'Falso positivo'),
        ])

        self.update_status("Dashboard actualizado")

    def delete_selected_repository(self):
        """Borra el repositorio elegido en el filtro del Dashboard, tras confirmarlo"""
        selected = self.dashboard_repo_filter.get()
        repo_id = self.dashboard_repo_ids.get(selected)
        if repo_id is None:
            messagebox.showinfo("Borrar repositorio",
                                "Elige primero un repositorio en la lista \"Repositorio:\".")
            return
        try:
            counts = db_manager.get_repository_counts(repo_id)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo consultar el repositorio: {e}")
            return

        message = (f"¿Borrar {selected}?\n\n"
                   f"Se eliminarán {counts['commits']} commits y {counts['credentials']} hallazgos.")
        if counts['labeled']:
            message += (f"\nTambién se perderán {counts['labeled']} correcciones tuyas "
                        f"y el modelo se reentrenará sin ellas.")
        message += "\n\nEsta acción no se puede deshacer."
        if not messagebox.askyesno("Borrar repositorio", message, icon='warning', default='no'):
            return

        try:
            db_manager.delete_repository(repo_id)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo borrar el repositorio: {e}")
            return

        self.log(f"🗑 Repositorio borrado: {selected} ({counts['credentials']} hallazgos)")
        self.dashboard_repo_filter.set(self.ALL_REPOS)
        self.update_statistics()
        self.load_results()
        self.update_status(f"Repositorio {selected} borrado")
        if counts['labeled']:
            threading.Thread(target=self.retrain_after_correction, daemon=True).start()

    def draw_hbar(self, key, labels, series, note=None):
        """
        Dibuja barras horizontales (apiladas si hay varias series) en el recuadro `key`.

        Args:
            labels (list): categorías, de arriba hacia abajo
            series (list): tuplas (valores, color o lista de colores, nombre para la leyenda)
            note (str): texto opcional debajo del gráfico
        """
        frame = self.chart_frames[key]
        for widget in frame.winfo_children():
            widget.destroy()

        if not labels or not any(sum(values) for values, _, _ in series):
            tk.Label(frame, text="Sin datos todavía. Analiza un repositorio en el Escáner.",
                     bg=self.colors['bg_dark'], fg='#7f849c', font=('Segoe UI', 10)).pack(expand=True)
            return

        bg = self.colors['bg_dark']
        fig = Figure(figsize=(5, 2.4), dpi=100, facecolor=bg)
        ax = fig.add_subplot(111, facecolor=bg)

        y = np.arange(len(labels))
        left = np.zeros(len(labels))
        for values, color, name in series:
            values = np.array(values, dtype=float)
            ax.barh(y, values, left=left, height=0.55, color=color, label=name,
                    edgecolor=bg, linewidth=1.5)
            left += values

        max_total = left.max() or 1
        for i, total in enumerate(left):
            ax.text(total + max_total * 0.02, i, f"{int(total)}", va='center',
                    color=self.colors['text'], fontsize=9)

        ax.set_yticks(y)
        ax.set_yticklabels(labels, color=self.colors['text'], fontsize=9)
        # Al menos 4 espacios para que las barras tengan el mismo grosor con pocas categorías
        # (eje invertido: la primera categoría queda arriba)
        ax.set_ylim(max(len(labels), 4) - 0.5, -0.5)
        ax.set_xlim(0, max_total * 1.15)
        ax.xaxis.set_visible(False)
        ax.tick_params(axis='y', length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)

        if len(series) > 1:
            ax.legend(loc='lower right', bbox_to_anchor=(1.0, 1.0), ncol=2, frameon=False, fontsize=8, labelcolor=self.colors['text'])
        if note:
            fig.text(0.02, 0.03, note, color='#7f849c', fontsize=8)
            fig.tight_layout(rect=(0, 0.08, 1, 1))
        else:
            fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def show_model_info(self):
        """Muestra información del modelo"""
        if not credential_classifier.is_trained:
            messagebox.showinfo("Información", "El modelo se está preparando, intenta de nuevo en unos segundos")
            return

        config = credential_classifier.config
        metrics = credential_classifier.last_metrics
        info = f"""
CLASIFICADOR DE HALLAZGOS

Algoritmo en uso: {credential_classifier.last_metrics.get('algorithm_name', 'CART')}
(elegido entre CART y Random Forest por validación cruzada)
Criterio: Índice de Gini
Balanceo: SMOTE dentro del pipeline + class_weight='balanced'
Biblioteca: scikit-learn / imbalanced-learn

Configuración:
- Max Depth: {config['max_depth']}
- Min Samples Split: {config['min_samples_split']}
- Prueba: {config['test_size']:.0%} de los datos etiquetados
- Random State: {config['random_state']}

Características utilizadas: {len(credential_classifier.feature_names)}

Entrenamiento: {metrics['total_samples']} ejemplos
  {metrics['total_samples'] - metrics['user_samples'] - metrics['apps_samples']} del conjunto semilla sintético
  {metrics['apps_samples']} de aplicaciones vulnerables (etiquetados a mano)
  {metrics['user_samples']} correcciones tuyas

Métricas en datos de prueba no vistos:
  Accuracy {metrics['accuracy']:.4f} · Precision {metrics['precision']:.4f}
  Recall {metrics['recall']:.4f} · F1 {metrics['f1']:.4f}

Clasifica cada hallazgo de las regex como "credencial real" o
"falso positivo" a partir de:
- Forma del valor (entropía, longitud, secuencias, palabras de ejemplo)
- Tipo de archivo (documentación, pruebas, configuración, .env)
- Contexto de la línea (comentario, variable de entorno)
        """
        
        messagebox.showinfo("Información del Modelo", info)
    
    def export_results(self):
        """Exporta los resultados"""
        try:
            df = db_manager.get_credentials_dataframe()
            
            if df.empty:
                messagebox.showwarning("Advertencia", "No hay datos para exportar")
                return
            
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if filepath:
                df.to_csv(filepath, index=False)
                messagebox.showinfo("Éxito", f"Datos exportados a:\n{filepath}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error exportando: {str(e)}")
    
    def export_to_csv(self):
        """Exporta la tabla actual a CSV"""
        self.export_results()
    
    def show_about(self):
        """Muestra información sobre la aplicación"""
        about_text = """
GitHub Repository Analyzer - ML

Herramienta de análisis de repositorios GitHub
que detecta credenciales expuestas y analiza
commits usando Machine Learning.

Características:
• Detección de credenciales con regex
• Análisis de commits de GitHub
• Clasificación ML con árboles CART
• Índice de Gini para pureza de nodos
• Base de datos PostgreSQL
• Interfaz gráfica con tkinter

Tecnologías:
- Python 3.x
- PostgreSQL
- scikit-learn (CART)
- pandas
- GitHub API
- tkinter

Proyecto de Grado 2024
        """
        messagebox.showinfo("Acerca de", about_text)


def main():
    """Función principal"""
    root = tk.Tk()
    app = GitHubAnalyzerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()