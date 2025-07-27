"""
visualization_wood.py
Visualización 2D y 3D del modelo térmico con EVAPORACIÓN
Proyecto: Modelado térmico de biorreactores para fermentación de cacao

"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle
import json
import os

# Para visualización 3D
try:
    import pyvista as pv
    from dolfinx import io
    from dolfinx.io import XDMFFile
    PYVISTA_AVAILABLE = True
except ImportError:
    PYVISTA_AVAILABLE = False
    print("⚠️ PyVista no instalado. Visualización 3D no disponible.")
    print("   Instalar con: pip install pyvista")

class BioreactorVisualizer:
    """
    Visualizador completo con capacidades 2D y 3D
    """
    
    def __init__(self):
        """Inicializa el visualizador"""
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.results_dir = os.path.join(self.script_dir, "results")
        
        # Configurar estilo
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # Colores temáticos
        self.colors = {
            'wood': '#8B4513',
            'cacao': '#D2691E',
            'temperature': 'hot',
            'evaporation': 'Blues_r',
            'heat_gen': 'Reds'
        }
    
    def load_statistics(self, filename):
        """Carga estadísticas de simulación"""
        filepath = os.path.join(self.results_dir, filename)
        if not os.path.exists(filepath):
            print(f"⚠️ No se encontró: {filepath}")
            return None
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def plot_2d_evolution(self, stats_file='stats_box_evaporation_wood.json'):
        """Visualización 2D"""
        stats = self.load_statistics(stats_file)
        if stats is None:
            return
        
        # Crear figura con 4 subplots
        fig = plt.figure(figsize=(16, 12))
        
        # Configurar grid personalizado
        gs = fig.add_gridspec(3, 2, height_ratios=[1.5, 1, 1])
        ax1 = fig.add_subplot(gs[0, :])  # Temperatura (ancho completo)
        ax2 = fig.add_subplot(gs[1, 0])  # Generación de calor
        ax3 = fig.add_subplot(gs[1, 1])  # Enfriamiento evaporativo
        ax4 = fig.add_subplot(gs[2, :])  # Balance térmico
        
        times = np.array(stats['times_hours'])
        T_max = np.array(stats['T_max_celsius'])
        T_min = np.array(stats['T_min_celsius'])
        T_avg = np.array(stats['T_avg_celsius'])
        q_gen = np.array(stats['heat_generation_W_m3'])
        q_evap = np.array(stats['evaporative_cooling_W_m3'])
        
        # GRÁFICO 1: Evolución de temperatura con zonas
        ax1.plot(times, T_max, 'r-', linewidth=2.5, label='T máxima')
        ax1.plot(times, T_avg, 'b-', linewidth=2, label='T promedio')
        ax1.plot(times, T_min, 'g-', linewidth=1.5, label='T mínima')
        
        # Agregar zonas de fermentación
        self._add_fermentation_zones(ax1)
        
        # Límites críticos
        ax1.axhline(y=55, color='darkred', linestyle='--', linewidth=2, 
                   label='Muerte microbiana (55°C)')
        ax1.axhline(y=48, color='orange', linestyle=':', linewidth=1.5,
                   label='T óptima máx (48°C)')
        
        ax1.set_xlabel('Tiempo [horas]', fontsize=12)
        ax1.set_ylabel('Temperatura [°C]', fontsize=12)
        ax1.set_title('Evolución Térmica con Enfriamiento Evaporativo', 
                     fontsize=14, fontweight='bold')
        ax1.legend(loc='upper left', ncol=2)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(0, 168)
        
        # GRÁFICO 2: Generación de calor
        ax2.fill_between(times, 0, q_gen, color='orange', alpha=0.7)
        ax2.plot(times, q_gen, 'darkorange', linewidth=2)
        ax2.set_xlabel('Tiempo [horas]')
        ax2.set_ylabel('Generación [W/m³]')
        ax2.set_title('Calor Metabólico')
        ax2.grid(True, alpha=0.3)
        
        # GRÁFICO 3: Enfriamiento evaporativo
        ax3.fill_between(times, 0, q_evap, color='lightblue', alpha=0.7)
        ax3.plot(times, q_evap, 'darkblue', linewidth=2)
        ax3.set_xlabel('Tiempo [horas]')
        ax3.set_ylabel('Evaporación [W/m³]')
        ax3.set_title('Enfriamiento Evaporativo')
        ax3.grid(True, alpha=0.3)
        
        # GRÁFICO 4: Balance térmico neto
        balance = q_gen - q_evap
        ax4.plot(times, q_gen, 'orange', linewidth=2, label='Generación')
        ax4.plot(times, -q_evap, 'blue', linewidth=2, label='Evaporación')
        ax4.plot(times, balance, 'green', linewidth=3, label='Balance neto')
        ax4.fill_between(times, 0, balance, where=(balance>=0), 
                        color='red', alpha=0.3, label='Calentamiento')
        ax4.fill_between(times, 0, balance, where=(balance<0), 
                        color='blue', alpha=0.3, label='Enfriamiento')
        ax4.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax4.set_xlabel('Tiempo [horas]')
        ax4.set_ylabel('Flujo de calor [W/m³]')
        ax4.set_title('Balance Térmico: Generación - Evaporación')
        ax4.legend(loc='upper right')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Guardar
        output_file = os.path.join(self.results_dir, 'thermal_evolution_2d_wood.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"📊 Gráfico 2D guardado: {output_file}")
        
        plt.show()
    
    def visualize_3d_fields(self, xdmf_file='bioreactor_box_evaporation_wood.xdmf', 
                           time_step=-1):
        """
        Visualización 3D de campos térmicos y evaporación
        
        Parámetros:
        -----------
        xdmf_file : str
            Archivo XDMF con resultados de la simulación
        time_step : int
            Paso temporal a visualizar (-1 para el último)
        """
        if not PYVISTA_AVAILABLE:
            print("❌ PyVista no disponible para visualización 3D")
            return
        
        filepath = os.path.join(self.results_dir, xdmf_file)
        if not os.path.exists(filepath):
            print(f"⚠️ No se encontró archivo XDMF: {filepath}")
            return
        
        print("🔄 Cargando datos 3D...")
        
        # Configurar PyVista
        pv.set_plot_theme("document")
        
        # Crear lector XDMF
        reader = pv.get_reader(filepath)
        reader.set_active_time_value(reader.time_values[time_step])
        mesh = reader.read()
        
        # Convertir temperatura a Celsius
        if 'Temperatura' in mesh.point_data:
            mesh['Temperatura_C'] = mesh['Temperatura'] - 273.15
        
        # Crear visualización
        plotter = pv.Plotter(shape=(2, 2), window_size=[1600, 1200])
        
        # VISTA 1: Campo de temperatura
        plotter.subplot(0, 0)
        plotter.add_text("Campo de Temperatura", font_size=12)
        
        # Crear corte para mostrar interior
        slice_temp = mesh.slice(normal='y', origin=mesh.center)
        plotter.add_mesh(slice_temp, scalars='Temperatura_C', 
                        cmap='hot', clim=[20, 60],
                        scalar_bar_args={'title': 'Temperatura [°C]'})
        
        # Contorno de isotermas
        contours = mesh.contour(isosurfaces=5, scalars='Temperatura_C')
        plotter.add_mesh(contours, opacity=0.3, color='white', line_width=2)
        
        # VISTA 2: Generación de calor
        plotter.subplot(0, 1)
        plotter.add_text("Generación de Calor", font_size=12)
        
        if 'Generacion_calor' in mesh.cell_data:
            slice_gen = mesh.slice(normal='z', origin=mesh.center)
            plotter.add_mesh(slice_gen, scalars='Generacion_calor',
                           cmap='Reds', clim=[0, 400],
                           scalar_bar_args={'title': 'q_gen [W/m³]'})
        
        # VISTA 3: Enfriamiento evaporativo
        plotter.subplot(1, 0)
        plotter.add_text("Enfriamiento Evaporativo", font_size=12)
        
        if 'Enfriamiento_evaporativo' in mesh.cell_data:
            slice_evap = mesh.slice(normal='x', origin=mesh.center)
            plotter.add_mesh(slice_evap, scalars='Enfriamiento_evaporativo',
                           cmap='Blues_r', clim=[0, 150],
                           scalar_bar_args={'title': 'q_evap [W/m³]'})
        
        # VISTA 4: Vista 3D completa con transparencia
        plotter.subplot(1, 1)
        plotter.add_text("Vista 3D Completa", font_size=12)
        
        # Mostrar volumen con transparencia
        plotter.add_mesh(mesh, scalars='Temperatura_C', 
                        opacity=0.8, cmap='hot',
                        show_edges=True, edge_color='gray')
        
        # Agregar caja delimitadora
        plotter.add_mesh(mesh.outline(), color='black', line_width=2)
        
        # Configurar cámaras
        for i in range(4):
            plotter.subplot(i // 2, i % 2)
            plotter.view_isometric()
            plotter.add_axes()
        
        # Información del tiempo
        if hasattr(reader, 'time_values'):
            time_hours = reader.time_values[time_step] / 3600
            plotter.add_text(f"Tiempo: {time_hours:.1f} horas", 
                           position='upper_right', font_size=10)
        
        # Mostrar
        plotter.show()
        
        # Guardar captura
        output_file = os.path.join(self.results_dir, 'thermal_3d_view_wood.png')
        plotter.screenshot(output_file)
        print(f"📸 Vista 3D guardada: {output_file}")
    
    def create_animation_3d(self, xdmf_file='bioreactor_box_evaporation_wood.xdmf',
                           output_gif='thermal_animation_wood.gif'):
        """
        Crea animación 3D de la evolución temporal
        """
        if not PYVISTA_AVAILABLE:
            print("❌ PyVista no disponible para animación")
            return
        
        filepath = os.path.join(self.results_dir, xdmf_file)
        if not os.path.exists(filepath):
            return
        
        print("🎬 Creando animación 3D...")
        
        # Leer datos
        reader = pv.get_reader(filepath)
        
        # Configurar plotter
        plotter = pv.Plotter(off_screen=True, window_size=[800, 600])
        plotter.open_gif(os.path.join(self.results_dir, output_gif))
        
        # Animar cada paso temporal
        for i, time_value in enumerate(reader.time_values[::6]):  # Cada 6 pasos
            reader.set_active_time_value(time_value)
            mesh = reader.read()
            
            if 'Temperatura' in mesh.point_data:
                mesh['Temperatura_C'] = mesh['Temperatura'] - 273.15
            
            plotter.clear()
            
            # Agregar corte animado
            slice_mesh = mesh.slice(normal='y', origin=mesh.center)
            plotter.add_mesh(slice_mesh, scalars='Temperatura_C',
                           cmap='hot', clim=[20, 60])
            
            # Texto temporal
            time_hours = time_value / 3600
            plotter.add_text(f"t = {time_hours:.1f} h", position='upper_left')
            
            plotter.write_frame()
        
        plotter.close()
        print(f"🎬 Animación guardada: {output_gif}")
    
    def plot_3d_mesh_structure(self):
        """
        Visualiza la estructura del mesh 3D con materiales
        """
        if not PYVISTA_AVAILABLE:
            return
        
        print("🔲 Visualizando estructura del mesh...")
        
        # Crear mesh sintético para demostración
        # (En producción, cargar desde archivo real)
        nx, ny, nz = 20, 22, 18
        
        # Dimensiones de la caja
        L_ext, W_ext, H_ext = 0.85, 0.90, 0.74
        
        # Crear grid estructurado
        grid = pv.StructuredGrid()
        x = np.linspace(0, L_ext, nx)
        y = np.linspace(0, W_ext, ny)
        z = np.linspace(0, H_ext, nz)
        
        x, y, z = np.meshgrid(x, y, z, indexing='ij')
        points = np.c_[x.ravel(), y.ravel(), z.ravel()]
        grid.points = points
        grid.dimensions = [nx, ny, nz]
        
        # Asignar materiales (simplificado)
        thickness = 0.03
        materials = np.zeros(grid.n_cells)
        
        for i in range(grid.n_cells):
            center = grid.cell_centers().points[i]
            x, y, z = center
            
            # Interior (cacao) o exterior (madera)
            if (thickness < x < L_ext - thickness and
                thickness < y < W_ext - thickness and
                thickness < z < H_ext - thickness):
                materials[i] = 2  # Cacao
            else:
                materials[i] = 1  # Madera
        
        grid.cell_data['Material'] = materials
        
        # Visualizar
        plotter = pv.Plotter()
        plotter.add_mesh(grid, scalars='Material', 
                        cmap=['white', self.colors['wood'], self.colors['cacao']],
                        show_edges=True, edge_color='gray',
                        opacity=0.8)
        
        # Agregar ventilación
        # Crear cilindros para representar agujeros
        hole_radius = 0.0025
        hole_positions = []
        
        # Agujeros inferiores
        for i in range(8):
            for j in range(10):
                x = 0.1 + i * 0.08
                y = 0.1 + j * 0.07
                z = 0.0
                hole_positions.append([x, y, z])
        
        for pos in hole_positions[:40]:  # Mostrar algunos
            cylinder = pv.Cylinder(center=pos, direction=[0, 0, 1],
                                 radius=hole_radius, height=thickness)
            plotter.add_mesh(cylinder, color='black')
        
        plotter.add_text("Estructura del Biorreactor", font_size=14)
        plotter.add_axes()
        plotter.show_grid()
        plotter.view_isometric()
        plotter.show()
    
    def _add_fermentation_zones(self, ax):
        """Agrega zonas de fermentación al gráfico"""
        phases = [
            (0, 12, 'Inicial\n(Levaduras)', 'lightgreen', 0.2),
            (12, 36, 'Fermentación\nrápida', 'yellow', 0.2),
            (36, 84, 'Pico bacterial\n(BAA)', 'orange', 0.2),
            (84, 168, 'Declive', 'lightcoral', 0.2)
        ]
        
        for t_start, t_end, label, color, alpha in phases:
            ax.axvspan(t_start, t_end, alpha=alpha, color=color)
            t_center = (t_start + t_end) / 2
            ax.text(t_center, ax.get_ylim()[1]*0.95, label, 
                   ha='center', va='top', fontsize=9, fontweight='bold')
    
    def create_summary_report(self, stats_file='stats_box_evaporation_wood.json'):
        """Crea un reporte visual resumido"""
        stats = self.load_statistics(stats_file)
        if stats is None:
            return
        
        fig = plt.figure(figsize=(16, 10))
        
        # Diseño personalizado
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # Panel principal: Resumen
        ax_main = fig.add_subplot(gs[0, :])
        ax_main.axis('off')
        
        # Título y resumen
        ax_main.text(0.5, 0.9, 'RESUMEN DEL MODELO TÉRMICO CON EVAPORACIÓN', 
                    ha='center', fontsize=18, fontweight='bold')
        
        # Información clave
        info_text = f"""
        Biorreactor: Caja de madera 85×90×74 cm
        Capacidad: 400 kg de cacao fresco
        Ventilación: 50% inferior + 25% laterales
        
        RESULTADOS CLAVE:
        • Temperatura máxima: {max(stats['T_max_celsius']):.1f}°C
        • Muerte microbiana: {'SÍ' if stats['thermal_death_occurred'] else 'NO ✓'}
        • Enfriamiento evaporativo máximo: {max(stats['evaporative_cooling_W_m3']):.0f} W/m³
        • Pérdida de humedad final: {stats.get('final_moisture_loss_percent', 0):.1f}%
        """
        
        ax_main.text(0.1, 0.4, info_text, fontsize=12, 
                    verticalalignment='top', fontfamily='monospace')
        
        # Otros paneles con métricas específicas
        # ... (continuar según necesidad)
        
        plt.tight_layout()
        output_file = os.path.join(self.results_dir, 'summary_report_wood.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"📄 Reporte guardado: {output_file}")


# Funciones principales de uso
def visualize_complete_results(include_3d=True):
    """
    Ejecuta visualización completa del modelo
    
    Parámetros:
    -----------
    include_3d : bool
        Si incluir visualizaciones 3D (requiere PyVista)
    """
    print("🎨 Iniciando visualización completa...")
    
    viz = BioreactorVisualizer()
    
    # Visualizaciones 2D
    print("\n📊 Generando gráficos 2D...")
    viz.plot_2d_evolution()
    
    # Visualizaciones 3D
    if include_3d and PYVISTA_AVAILABLE:
        print("\n🔲 Generando visualizaciones 3D...")
        viz.visualize_3d_fields()
        viz.plot_3d_mesh_structure()
        # viz.create_animation_3d()  # Opcional, toma tiempo
    
    # Reporte resumen
    print("\n📄 Generando reporte...")
    viz.create_summary_report()
    
    print("\n✅ Visualización completada!")
    print(f"   Resultados en: {viz.results_dir}/")


if __name__ == "__main__":
    # Verificar disponibilidad de herramientas
    print("🍫 VISUALIZACIÓN DEL MODELO TÉRMICO")
    print("="*50)
    
    if PYVISTA_AVAILABLE:
        print("✓ PyVista disponible - Visualización 3D habilitada")
    else:
        print("✗ PyVista no disponible - Solo visualización 2D")
        print("  Instalar con: pip install pyvista")
    
    # Ejecutar visualización
    visualize_complete_results(include_3d=True)