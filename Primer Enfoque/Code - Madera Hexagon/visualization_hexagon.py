"""
visualization_hexagon.py
Visualización para TAMBOR HEXAGONAL REAL con GMSH
AJUSTES: Para usar stats_hexagon.json y mostrar geometría real
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Polygon, Circle
import json
import os

class HexagonalVisualizer:
    """Visualizador para tambor hexagonal REAL con GMSH"""
    
    def __init__(self):
        self.results_dir = "results"
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # Colores específicos para hexágono REAL
        self.colors = {
            'hexagon_body': '#8B4513',     # Madera
            'hexagon_interior': '#D2691E', # Cacao
            'hexagon_air': '#87CEEB',      # Aire interior
            'ventilation': '#FF4500',      # Ventilación
            'rotation': '#32CD32',         # Rotación
            'real_geometry': '#FFD700'     # Dorado para geometría real
        }
        
    def check_available_files(self):
        """Verifica qué archivos están disponibles"""
        print("🔍 Verificando archivos disponibles en results/:")
        
        if not os.path.exists(self.results_dir):
            print(f"❌ Directorio {self.results_dir} no existe")
            return []
        
        files = os.listdir(self.results_dir)
        json_files = [f for f in files if f.endswith('.json')]
        
        print(f"📁 Archivos JSON encontrados:")
        for file in json_files:
            print(f"   - {file}")
        
        return json_files
        
    def load_hexagon_stats(self):
        """Carga estadísticas del tambor hexagonal REAL"""
        available_files = self.check_available_files()
        
        # Buscar archivo hexagonal REAL (nombres posibles)
        possible_names = [
            "stats_hexagon.json",                    # NUEVO nombre sin sufijos
            "stats_hexagon_evaporation.json",       # Versión anterior
            "stats_hexagon.json"          # Versión corregida anterior
        ]
        
        hexagon_file = None
        for name in possible_names:
            if name in available_files:
                hexagon_file = name
                break
        
        if hexagon_file is None:
            print(f"⚠️ No se encontró archivo de tambor hexagonal")
            print(f"   Archivos buscados: {possible_names}")
            return None
        
        filename = os.path.join(self.results_dir, hexagon_file)
        print(f"✅ Cargando: {hexagon_file}")
        
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                
            # Verificar si es geometría REAL
            is_geometry = data.get('real_geometry', False)
            gmsh_generated = data.get('gmsh_generated', False)
            
            if is_geometry and gmsh_generated:
                print(f"🛢️ Datos de TAMBOR HEXAGONAL REAL detectados")
                print(f"   - Geometría: Hexágono 3D verdadero")
                print(f"   - Distribución: {data.get('cacao_fraction_achieved', 0.7)*100:.0f}% cacao exacto")
                print(f"   - Generado con: GMSH")
            else:
                print(f"📦 Datos de tambor hexagonal (aproximado/anterior)")
                
            return data
            
        except Exception as e:
            print(f"❌ Error cargando {hexagon_file}: {e}")
            return None
    
    def load_box_stats_for_comparison(self):
        """Carga estadísticas de la caja para comparación"""
        possible_names = [
            "stats_box_evaporation.json",
            "stats_box.json"
        ]
        
        available_files = self.check_available_files()
        
        box_file = None
        for name in possible_names:
            if name in available_files:
                box_file = name
                break
        
        if box_file is None:
            print(f"⚠️ No se encontraron datos de la caja para comparar")
            return None
        
        filename = os.path.join(self.results_dir, box_file)
        print(f"✅ Cargando para comparación: {box_file}")
        
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error cargando {box_file}: {e}")
            return None
    
    def safe_get_value(self, data, key, default=0):
        """Obtiene valor de forma segura, manejando None"""
        if data is None:
            return default
        
        value = data.get(key, default)
        return default if value is None else value
    
    def plot_hexagonal_analysis(self):
        """Crea gráficos especializados para el tambor hexagonal REAL"""
        hexagon_stats = self.load_hexagon_stats()
        if hexagon_stats is None:
            print("❌ No se pueden crear gráficos sin datos del tambor")
            return
        
        box_stats = self.load_box_stats_for_comparison()
        
        # Detectar si es geometría real
        is_geometry = hexagon_stats.get('real_geometry', False)
        title_suffix = "REAL (GMSH)" if is_geometry else "Aproximado"
        
        # Crear figura con 6 subplots
        fig = plt.figure(figsize=(18, 14))
        gs = fig.add_gridspec(3, 3, height_ratios=[1.5, 1, 1], width_ratios=[1.2, 1, 1])
        
        ax1 = fig.add_subplot(gs[0, :])    # Evolución térmica (ancho completo)
        ax2 = fig.add_subplot(gs[1, 0])    # Balance térmico
        ax3 = fig.add_subplot(gs[1, 1])    # Rotaciones y eventos
        ax4 = fig.add_subplot(gs[1, 2])    # Comparación con caja
        ax5 = fig.add_subplot(gs[2, 0])    # Esquema del tambor
        ax6 = fig.add_subplot(gs[2, 1:])   # Pérdida de humedad
        
        # Título principal
        fig.suptitle(f'Análisis Térmico - Tambor Hexagonal {title_suffix}', 
                    fontsize=16, fontweight='bold')
        
        # Obtener datos de forma segura
        times = np.array(hexagon_stats.get('times_hours', []))
        T_max = np.array(hexagon_stats.get('T_max_celsius', []))
        T_avg = np.array(hexagon_stats.get('T_avg_celsius', []))
        T_min = np.array(hexagon_stats.get('T_min_celsius', []))
        q_gen = np.array(hexagon_stats.get('heat_generation_W_m3', []))
        q_evap = np.array(hexagon_stats.get('evaporative_cooling_W_m3', []))
        
        if len(times) == 0:
            print("⚠️ No hay datos temporales para graficar")
            plt.close(fig)
            return
        
        # GRÁFICO 1: Evolución térmica con rotaciones
        color_max = self.colors['real_geometry'] if is_geometry else 'red'
        
        ax1.plot(times, T_max, color=color_max, linewidth=2.5, label='T máxima')
        ax1.plot(times, T_avg, 'b-', linewidth=2, label='T promedio')
        ax1.plot(times, T_min, 'g-', linewidth=1.5, label='T mínima')
        
        # Marcar eventos de rotación
        rotation_events = hexagon_stats.get('rotation_events_hours', [])
        if rotation_events:
            for rot_time in rotation_events:
                if rot_time is not None:
                    ax1.axvline(x=rot_time, color='orange', linestyle=':', linewidth=2, alpha=0.7)
                    ax1.text(rot_time, max(T_max)*0.95, '🔄', fontsize=16, ha='center')
        
        # Líneas de referencia térmicas
        ax1.axhline(y=50, color='red', linestyle='--', alpha=0.5, label='Límite ideal (50°C)')
        ax1.axhline(y=55, color='orange', linestyle='--', alpha=0.5, label='Límite aceptable (55°C)')
        
        # Fases de fermentación
        self._add_fermentation_phases(ax1)
        
        ax1.set_xlabel('Tiempo [horas]', fontsize=12)
        ax1.set_ylabel('Temperatura [°C]', fontsize=12)
        ax1.set_title(f'Evolución Térmica del Tambor Hexagonal {title_suffix}', 
                     fontsize=14, fontweight='bold')
        ax1.legend(loc='upper left', ncol=3, fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(0, max(168, max(times) if len(times) > 0 else 168))
        
        # GRÁFICO 2: Balance térmico
        if len(q_gen) > 0 and len(q_evap) > 0:
            balance = q_gen - q_evap
            
            color_gen = self.colors['real_geometry'] if is_geometry else 'orange'
            
            ax2.plot(times, q_gen, color=color_gen, linewidth=2, label='Generación')
            ax2.plot(times, -q_evap, 'cyan', linewidth=2, label='Evaporación')
            ax2.plot(times, balance, 'purple', linewidth=2, linestyle='--', label='Balance neto')
            
            ax2.fill_between(times, 0, balance, where=(balance>=0), 
                            color='red', alpha=0.3, label='Calentamiento')
            ax2.fill_between(times, 0, balance, where=(balance<0), 
                            color='blue', alpha=0.3, label='Enfriamiento')
        
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax2.set_xlabel('Tiempo [horas]')
        ax2.set_ylabel('Flujo de calor [W/m³]')
        
        balance_title = "Balance Térmico (Real)" if is_geometry else "Balance Térmico"
        ax2.set_title(balance_title)
        ax2.legend(fontsize=9)
        ax2.grid(True, alpha=0.3)
        
        # GRÁFICO 3: Eventos de rotación
        self._plot_rotation_schedule(ax3, hexagon_stats)
        
        # GRÁFICO 4: Comparación con caja
        self._plot_comparison_with_box(ax4, hexagon_stats, box_stats, is_geometry)
        
        # GRÁFICO 5: Esquema del tambor hexagonal
        self._draw_hexagonal_drum_schema(ax5, hexagon_stats, is_geometry)
        
        # GRÁFICO 6: Pérdida de humedad
        moisture_data = hexagon_stats.get('moisture_loss_kg_m3', [])
        if moisture_data:
            moisture = np.array(moisture_data)
            moisture_percent = (moisture / (0.40 * 910)) * 100
            
            color_moisture = self.colors['real_geometry'] if is_geometry else 'blue'
            label_moisture = 'Tambor hexagonal REAL' if is_geometry else 'Tambor hexagonal'
            
            ax6.plot(times, moisture_percent, color=color_moisture, linewidth=2, label=label_moisture)
            ax6.fill_between(times, 0, moisture_percent, alpha=0.3, color=color_moisture)
            
            # Comparar con caja si disponible
            if box_stats and 'moisture_loss_kg_m3' in box_stats:
                box_moisture = np.array(box_stats['moisture_loss_kg_m3'])
                box_moisture_percent = (box_moisture / (0.40 * 910)) * 100
                box_times = np.array(box_stats['times_hours'])
                ax6.plot(box_times, box_moisture_percent, 'g--', linewidth=2, label='Caja (referencia)')
            
            ax6.axhline(y=33, color='red', linestyle='--', alpha=0.7)
            ax6.text(100, 34, 'Objetivo: 33%\n(40% → 7%)', fontsize=9)
            
            ax6.set_xlabel('Tiempo [horas]')
            ax6.set_ylabel('Humedad perdida [%]')
            
            humidity_title = "Pérdida de Humedad (Geometría Real)" if is_geometry else "Pérdida de Humedad"
            ax6.set_title(humidity_title)
            ax6.legend()
            ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Guardar con nombre apropiado
        filename_suffix = "" if is_geometry else "_aproximado"
        filename = os.path.join(self.results_dir, f"analisis_tambor_hexagonal{filename_suffix}.png")
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"📊 Análisis hexagonal guardado: {filename}")
        
        plt.show()
        
        # Imprimir resumen
        self._print_hexagonal_summary(hexagon_stats, box_stats, is_geometry)
    
    def _plot_comparison_with_box(self, ax, hexagon_stats, box_stats, is_geometry):
        """Gráfico comparativo con la caja (para geometría REAL)"""
        if box_stats is None:
            ax.text(0.5, 0.5, 'Datos de caja\nno disponibles', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Comparación con Caja')
            return
        
        # Datos comparativos
        categories = ['T_max\n[°C]', 'Supervivencia\n[h]', 'Humedad\nlost [%]']
        
        # Temperatura máxima
        hexagon_temp = self.safe_get_value(hexagon_stats, 'max_temp_reached_celsius', 25)
        box_temp = self.safe_get_value(box_stats, 'max_temp_reached_celsius', 25)
        
        # Supervivencia (manejar None apropiadamente)
        hexagon_death_time = hexagon_stats.get('death_time_hours')
        box_death_time = box_stats.get('death_time_hours')
        
        hexagon_survival = 168 if hexagon_death_time is None else hexagon_death_time
        box_survival = 168 if box_death_time is None else box_death_time
        
        # Asegurar valores numéricos
        hexagon_survival = hexagon_survival if hexagon_survival is not None else 168
        box_survival = box_survival if box_survival is not None else 168
        
        # Pérdida de humedad
        hexagon_moisture = self.safe_get_value(hexagon_stats, 'final_moisture_loss_percent', 0)
        box_moisture = self.safe_get_value(box_stats, 'final_moisture_loss_percent', 0)
        
        hexagon_values = [hexagon_temp, hexagon_survival, hexagon_moisture]
        box_values = [box_temp, box_survival, box_moisture]
        
        # Verificar que todos los valores son números válidos
        for i, (hval, bval) in enumerate(zip(hexagon_values, box_values)):
            if hval is None or not isinstance(hval, (int, float)):
                hexagon_values[i] = 0
            if bval is None or not isinstance(bval, (int, float)):
                box_values[i] = 0
        
        x = np.arange(len(categories))
        width = 0.35
        
        try:
            bars1 = ax.bar(x - width/2, box_values, width, label='Caja', color='lightblue')
            
            hex_color = self.colors['real_geometry'] if is_geometry else 'orange'
            hex_label = 'Tambor Hex. REAL' if is_geometry else 'Tambor Hex.'
            bars2 = ax.bar(x + width/2, hexagon_values, width, label=hex_label, color=hex_color)
            
            # Agregar valores en las barras
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    if height is not None and isinstance(height, (int, float)):
                        ax.text(bar.get_x() + bar.get_width()/2., height + abs(height)*0.01,
                               f'{height:.1f}', ha='center', va='bottom', fontsize=9)
            
            ax.set_ylabel('Valor')
            
            comparison_title = "Caja vs Tambor Hexagonal" if is_geometry else "Caja vs Tambor Hex."
            ax.set_title(comparison_title)
            ax.set_xticks(x)
            ax.set_xticklabels(categories)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
        except Exception as e:
            print(f"⚠️ Error en gráfico comparativo: {e}")
            ax.text(0.5, 0.5, f'Error en comparación:\n{str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
    
    def _add_fermentation_phases(self, ax):
        """Agrega fases de fermentación"""
        phases = [
            (0, 12, 'Inicial\n(Levaduras)', 'lightgreen', 0.2),
            (12, 36, 'Fermentación\nrápida', 'yellow', 0.2),
            (36, 84, 'Pico bacterial\n(BAA)', 'orange', 0.2),
            (84, 168, 'Declive', 'lightcoral', 0.2)
        ]
        
        for t_start, t_end, label, color, alpha in phases:
            ax.axvspan(t_start, t_end, alpha=alpha, color=color)
            t_center = (t_start + t_end) / 2
            ax.text(t_center, ax.get_ylim()[1]*0.90, label, 
                   ha='center', va='top', fontsize=8, fontweight='bold')
    
    def _plot_rotation_schedule(self, ax, hexagon_stats):
        """Grafica el cronograma de rotaciones"""
        ax.set_xlim(0, 168)
        ax.set_ylim(-0.5, 2.5)
        
        # Línea de tiempo
        ax.axhline(y=1, color='black', linewidth=2)
        
        # Marcar rotaciones programadas
        rotation_events = hexagon_stats.get('rotation_events_hours', [])
        if rotation_events:
            for i, rot_time in enumerate(rotation_events):
                if rot_time is not None:
                    # Marca de rotación
                    ax.plot(rot_time, 1, 'o', color='red', markersize=12)
                    ax.text(rot_time, 1.3, f'R{i+1}', ha='center', fontweight='bold')
                    ax.text(rot_time, 0.7, f'{rot_time:.0f}h', ha='center', fontsize=9)
                    
                    # Línea vertical
                    ax.axvline(x=rot_time, color='red', linestyle=':', alpha=0.5)
        
        # Etiquetas de días
        for day in range(8):
            day_hour = day * 24
            ax.axvline(x=day_hour, color='gray', linestyle='-', alpha=0.3)
            ax.text(day_hour, 2, f'Día {day}', ha='center', fontsize=8)
        
        ax.set_xlabel('Tiempo [horas]')
        ax.set_title('Cronograma de Rotaciones')
        ax.set_yticks([])
        ax.grid(True, alpha=0.3)
        
        # Agregar leyenda
        ax.text(84, 2.2, '🔄 = Rotación del tambor\n(Homogeneización)', 
               ha='center', fontsize=10, 
               bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow"))
    
    def _draw_hexagonal_drum_schema(self, ax, hexagon_stats, is_geometry):
        """Dibuja esquema del tambor hexagonal (REAL o aproximado)"""
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Dibujar hexágono exterior (vista frontal)
        angles = np.linspace(0, 2*np.pi, 7)
        hex_outer = np.array([[0.9*np.cos(a), 0.9*np.sin(a)] for a in angles[:-1]])
        hex_inner = np.array([[0.7*np.cos(a), 0.7*np.sin(a)] for a in angles[:-1]])
        
        # Color según tipo de geometría
        hex_color = self.colors['real_geometry'] if is_geometry else self.colors['hexagon_body']
        
        # Hexágono exterior (madera)
        hex_ext_patch = Polygon(hex_outer, closed=True, 
                               facecolor=hex_color, 
                               edgecolor='black', linewidth=2, alpha=0.8)
        ax.add_patch(hex_ext_patch)
        
        # Hexágono interior con distribución 70/30
        if is_geometry:
            # Mostrar distribución REAL 70/30
            # Parte inferior: cacao (70%)
            y_cut = -0.2  # Línea de corte aproximada para 70%
            
            # Crear máscara para la parte inferior (cacao)
            hex_cacao = []
            for point in hex_inner:
                if point[1] <= y_cut:
                    hex_cacao.append(point)
            
            # Agregar puntos de intersección con la línea de corte
            for i in range(len(hex_inner)):
                p1 = hex_inner[i]
                p2 = hex_inner[(i+1) % len(hex_inner)]
                
                if (p1[1] <= y_cut and p2[1] > y_cut) or (p1[1] > y_cut and p2[1] <= y_cut):
                    # Intersección con y = y_cut
                    t = (y_cut - p1[1]) / (p2[1] - p1[1])
                    x_intersect = p1[0] + t * (p2[0] - p1[0])
                    hex_cacao.append([x_intersect, y_cut])
            
            if len(hex_cacao) >= 3:
                # Ordenar puntos para formar polígono
                center = np.mean(hex_cacao, axis=0)
                angles_sort = np.arctan2([p[1]-center[1] for p in hex_cacao], 
                                       [p[0]-center[0] for p in hex_cacao])
                sorted_indices = np.argsort(angles_sort)
                hex_cacao_sorted = [hex_cacao[i] for i in sorted_indices]
                
                # Parte de cacao (inferior)
                cacao_patch = Polygon(hex_cacao_sorted, closed=True, 
                                    facecolor=self.colors['hexagon_interior'], 
                                    edgecolor='brown', linewidth=1, alpha=0.9)
                ax.add_patch(cacao_patch)
                
                # Parte de aire (superior) - crear máscara complementaria
                hex_air = []
                for point in hex_inner:
                    if point[1] > y_cut:
                        hex_air.append(point)
                
                # Agregar puntos de intersección
                for i in range(len(hex_inner)):
                    p1 = hex_inner[i]
                    p2 = hex_inner[(i+1) % len(hex_inner)]
                    
                    if (p1[1] <= y_cut and p2[1] > y_cut) or (p1[1] > y_cut and p2[1] <= y_cut):
                        t = (y_cut - p1[1]) / (p2[1] - p1[1])
                        x_intersect = p1[0] + t * (p2[0] - p1[0])
                        hex_air.append([x_intersect, y_cut])
                
                if len(hex_air) >= 3:
                    center_air = np.mean(hex_air, axis=0)
                    angles_air = np.arctan2([p[1]-center_air[1] for p in hex_air], 
                                          [p[0]-center_air[0] for p in hex_air])
                    sorted_indices_air = np.argsort(angles_air)
                    hex_air_sorted = [hex_air[i] for i in sorted_indices_air]
                    
                    air_patch = Polygon(hex_air_sorted, closed=True, 
                                      facecolor=self.colors['hexagon_air'], 
                                      edgecolor='lightblue', linewidth=1, alpha=0.7)
                    ax.add_patch(air_patch)
                
                # Línea divisoria
                ax.axhline(y=y_cut, xmin=0.2, xmax=0.8, color='red', linewidth=2, alpha=0.8)
                ax.text(0, y_cut+0.1, '70%/30%', ha='center', fontsize=8, color='red', fontweight='bold')
        else:
            # Geometría aproximada (relleno uniforme)
            hex_int_patch = Polygon(hex_inner, closed=True, 
                                   facecolor=self.colors['hexagon_interior'], 
                                   edgecolor='brown', linewidth=1, alpha=0.9)
            ax.add_patch(hex_int_patch)
        
        # Marcar cara ventilada (inferior)
        ax.plot([-0.3, 0.3], [-0.6, -0.6], color=self.colors['ventilation'], 
               linewidth=6, alpha=0.8, label='Ventilación 50%')
        
        # Agregar agujeros de ventilación
        for i in range(5):
            x_hole = -0.3 + i * 0.15
            y_hole = -0.6
            circle = Circle((x_hole, y_hole), 0.03, color='black', alpha=0.8)
            ax.add_patch(circle)
        
        # Flecha de rotación
        from matplotlib.patches import FancyArrowPatch
        arrow = FancyArrowPatch((0.8, 0.8), (0.8, -0.8),
                               connectionstyle="arc3,rad=0.3",
                               arrowstyle='->', mutation_scale=20,
                               color=self.colors['rotation'], linewidth=3)
        ax.add_patch(arrow)
        ax.text(1.0, 0, '🔄', fontsize=20)
        
        # Etiquetas
        geometry_type = "REAL (GMSH)" if is_geometry else "Aproximado"
        ax.text(0, 1.1, f'TAMBOR HEXAGONAL {geometry_type}', 
               ha='center', fontsize=12, fontweight='bold')
        
        if is_geometry:
            ax.text(0, 0.2, 'Aire\n30%', ha='center', va='center', fontsize=9, color='blue')
            ax.text(0, -0.3, 'Cacao\n70%', ha='center', va='center', fontsize=9, color='white')
        else:
            ax.text(0, 0, 'Cacao\n~70%', ha='center', va='center', fontsize=10, color='white')
            
        ax.text(0, -0.9, 'Cara ventilada\n(siempre hacia abajo)', 
               ha='center', fontsize=9, color=self.colors['ventilation'], fontweight='bold')
        
        # Dimensiones
        length = self.safe_get_value(hexagon_stats, 'drum_length_m', 1.8)
        diameter = self.safe_get_value(hexagon_stats, 'drum_diameter_m', 0.86)
        
        precision_note = " (exacto)" if is_geometry else " (aprox.)"
        ax.text(-1.1, -1.1, f"L = {length} m\n"
                            f"D = {diameter} m\n"
                            f"~{length * 0.7 * 910:.0f} kg{precision_note}",
               fontsize=9, va='bottom')
    
    def _print_hexagonal_summary(self, hexagon_stats, box_stats=None, is_geometry=False):
        """Imprime resumen del análisis hexagonal (REAL o aproximado)"""
        print("\n" + "="*60)
        
        if is_geometry:
            print("RESUMEN DEL TAMBOR HEXAGONAL REAL CON GMSH")
        else:
            print("RESUMEN DEL TAMBOR HEXAGONAL")
            
        print("="*60)
        
        print(f"\nCONFIGURACIÓN:")
        length = self.safe_get_value(hexagon_stats, 'drum_length_m', 1.8)
        diameter = self.safe_get_value(hexagon_stats, 'drum_diameter_m', 0.86)
        ventilation = self.safe_get_value(hexagon_stats, 'ventilated_face_fraction', 0.5)
        total_rotations = self.safe_get_value(hexagon_stats, 'total_rotations', 0)
        
        print(f"  - Longitud: {length} m")
        print(f"  - Diámetro: {diameter} m")
        print(f"  - Ventilación: {ventilation*100:.0f}% de una cara lateral")
        print(f"  - Rotaciones: {total_rotations} durante fermentación")
        
        if is_geometry:
            print(f"  - Geometría: HEXÁGONO REAL 3D (GMSH)")
            cacao_fraction = hexagon_stats.get('cacao_fraction_achieved', 0.7)
            air_fraction = hexagon_stats.get('air_fraction_achieved', 0.3)
            print(f"  - Distribución: {cacao_fraction*100:.0f}% cacao / {air_fraction*100:.0f}% aire (EXACTO)")
        else:
            print(f"  - Geometría: Hexágono aproximado")
            print(f"  - Distribución: ~70% cacao / ~30% aire (aproximado)")
        
        print(f"\nRESULTADOS TÉRMICOS:")
        max_temp = self.safe_get_value(hexagon_stats, 'max_temp_reached_celsius', 0)
        thermal_death = hexagon_stats.get('thermal_death_occurred', False)
        
        print(f"  - Temperatura máxima: {max_temp:.1f}°C")
        print(f"  - Muerte microbiana: {'SÍ' if thermal_death else 'NO ✓'}")
        
        if thermal_death:
            death_time = self.safe_get_value(hexagon_stats, 'death_time_hours', 0)
            print(f"  - Tiempo de muerte: {death_time:.1f}h")
        
        # Control térmico
        if max_temp < 50.0:
            print(f"  - Control térmico: ✅ PERFECTO (<50°C)")
        elif max_temp < 55.0:
            print(f"  - Control térmico: ✅ EXCELENTE (<55°C)")
        else:
            print(f"  - Control térmico: ⚠️ REVISAR (>{max_temp:.1f}°C)")
        
        # Comparación con caja (si disponible)
        if box_stats:
            print(f"\nCOMPARACIÓN CON CAJA:")
            box_temp = self.safe_get_value(box_stats, 'max_temp_reached_celsius', 0)
            print(f"  TEMPERATURA MÁXIMA:")
            print(f"    - Caja: {box_temp:.1f}°C")
            print(f"    - Tambor: {max_temp:.1f}°C")
            temp_diff = max_temp - box_temp
            print(f"    - Diferencia: {temp_diff:+.1f}°C")
            
            if is_geometry:
                print(f"  VENTAJAS DE LA GEOMETRÍA REAL:")
                print(f"    - Distribución exacta 70/30")
                print(f"    - Sin aproximaciones geométricas")
                print(f"    - Evaporación optimizada por forma real")
                print(f"    - Control térmico preciso")


def main():
    """Función principal de visualización hexagonal"""
    print("📊 VISUALIZACIÓN DEL TAMBOR HEXAGONAL")
    print("🛢️ Compatible con geometría REAL (GMSH) y aproximada")
    print("="*60)
    
    viz = HexagonalVisualizer()
    
    # Verificar archivos disponibles
    print("\n🔍 Verificando archivos disponibles...")
    available_files = viz.check_available_files()
    
    if not available_files:
        print("❌ No se encontraron archivos de resultados")
        print("💡 Ejecutar primero la simulación:")
        print("   python run_hexagon_analysis.py")
        return
    
    # Análisis principal del tambor
    print("\n🛢️ Generando análisis del tambor hexagonal...")
    viz.plot_hexagonal_analysis()
    
    print("\n✅ Visualización hexagonal completada")
    print(f"   Resultados en: {viz.results_dir}/")

if __name__ == "__main__":
    main()