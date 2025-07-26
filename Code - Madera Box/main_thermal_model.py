"""
main_thermal_model.py
Modelo térmico PASIVO
Proyecto: Modelado térmico de biorreactores para fermentación de cacao

"""

import numpy as np
import os
from mpi4py import MPI
from dolfinx import mesh, fem, io
from dolfinx.fem import functionspace, Function, Constant, assemble_scalar
from dolfinx.fem.petsc import LinearProblem
from dolfinx.io import XDMFFile, VTXWriter
import ufl
from ufl import dx, grad, dot, inner, Measure
from petsc4py import PETSc
from petsc4py.PETSc import ScalarType

# Importar módulos del proyecto
from geometry_setup import create_bioreactor_geometry
from material_properties import MaterialProperties

class BioreactorThermalModel:
    """
    Modelo térmico del biorreactor
    """
    
    def __init__(self, bioreactor_type='box'):
        """
        Inicializa el modelo térmico
        """
        self.bioreactor_type = bioreactor_type
        self.comm = MPI.COMM_WORLD
        
        # Crear directorio de resultados
        if self.comm.rank == 0:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.results_dir = os.path.join(script_dir, "results")
            os.makedirs(self.results_dir, exist_ok=True)
        
        print(f"\n🚀 Inicializando modelo térmico - {bioreactor_type.upper()}")
        print("💧 Enfriamiento evaporativo PASIVO activado")
        print("="*60)
        
        # Configurar geometría
        self.setup_geometry()
        
        # Configurar propiedades de materiales
        self.setup_materials()
        
        # Configurar problema térmico
        self.setup_thermal_problem()
        
    def setup_geometry(self):
        """Configura la geometría del biorreactor"""
        self.geom, self.domain = create_bioreactor_geometry(self.bioreactor_type)
        
    def setup_materials(self):
        """Configura las propiedades de los materiales"""
        self.mat_props = MaterialProperties()
        
        # Crear funciones de propiedades
        self.props = self.mat_props.create_material_functions(
            self.domain, 
            self.geom.material_markers
        )
        
        # Mostrar resumen
        self.mat_props.print_summary()
        
    def setup_thermal_problem(self):
        """Configura el problema de transferencia de calor"""
        print("\n⚙️ Configurando problema térmico...")
        
        # Crear espacio de funciones para temperatura
        self.V = functionspace(self.domain, ("CG", 1))
        
        # Funciones de temperatura
        self.T = Function(self.V, name="Temperatura")
        self.T_n = Function(self.V, name="Temperatura_anterior")
        
        # Condición inicial
        T_inicial = ScalarType(self.mat_props.ambient['T_amb'])
        self.T.x.array[:] = T_inicial
        self.T_n.x.array[:] = T_inicial
        
        print(f"✅ Temperatura inicial: {T_inicial - 273.15:.1f}°C")
        
        # Parámetros temporales
        self.t = 0.0
        self.dt = 300.0  # 5 minutos
        self.t_final = 7 * 24 * 3600  # 7 días
        
        # Variables para control
        self.max_temp_reached = T_inicial
        self.thermal_death_occurred = False
        self.death_time = None
        self.total_moisture_loss = 0.0  # kg/m³
        
        print(f"⏰ Configuración temporal:")
        print(f"   - Paso de tiempo: {self.dt/60:.1f} minutos")
        print(f"   - Tiempo final: {self.t_final/3600/24:.1f} días")
        
    def create_variational_form(self):
        """
        Crea la forma variacional
        
        Ecuación: ρ·cp·∂T/∂t = ∇·(k∇T) + q_gen - q_evap - pérdidas_convección
        """
        print("🔧 Creando forma variacional...")
        
        # Funciones de prueba y trial
        v = ufl.TestFunction(self.V)
        u = ufl.TrialFunction(self.V)
        
        # Propiedades del material
        k = self.props['k']
        rho = self.props['rho'] 
        cp = self.props['cp']
        
        # Condiciones ambientales
        T_amb = Constant(self.domain, PETSc.ScalarType(self.mat_props.ambient['T_amb']))
        
        # Coeficientes de convección
        h_normal = Constant(self.domain, PETSc.ScalarType(self.mat_props.ambient['h_conv']))
        h_ventilated = Constant(self.domain, PETSc.ScalarType(self.mat_props.ventilation['enhanced_h_conv']))
        
        # Constante de tiempo
        dt = Constant(self.domain, PETSc.ScalarType(self.dt))
        
        # Measures
        ds = Measure("ds", domain=self.domain, subdomain_data=self.geom.boundary_markers)
        
        # Crear funciones para generación de calor y evaporación
        Q = functionspace(self.domain, ("DG", 0))
        self.q_function = Function(Q, name="Generacion_calor")
        self.q_evap_function = Function(Q, name="Enfriamiento_evaporativo")
        
        # FORMA VARIACIONAL
        # Término transitorio + conductividad
        a = (rho * cp * u * v * dx + 
             dt * inner(k * grad(u), grad(v)) * dx)
        
        # Convección en fronteras
        normal_markers = [1, 2, 3, 4, 5, 6]
        ventilated_markers = [7, 8, 9]
        
        for marker in normal_markers:
            a += dt * h_normal * u * v * ds(marker)
        
        for marker in ventilated_markers:
            a += dt * h_ventilated * u * v * ds(marker)
        
        # Lado derecho
        L = (rho * cp * self.T_n * v * dx + 
             dt * self.q_function * v * dx -           # Generación de calor
             dt * self.q_evap_function * v * dx)       # RESTA enfriamiento evaporativo
        
        # Términos de frontera
        for marker in normal_markers:
            L += dt * h_normal * T_amb * v * ds(marker)
        
        for marker in ventilated_markers:
            L += dt * h_ventilated * T_amb * v * ds(marker)
        
        print("✅ Forma variacional creada")
        print(f"   💧 Enfriamiento evaporativo: INCLUIDO como término de sumidero")
        
        return a, L, dt, T_amb, h_normal, h_ventilated
    
    def update_heat_generation_and_evaporation(self):
        """
        Actualiza la generación de calor Y el enfriamiento evaporativo
        """
        # Obtener temperatura máxima actual
        current_T_max = np.max(self.T.x.array)
        current_T_avg = np.mean(self.T.x.array)
        
        # Actualizar máxima alcanzada
        if current_T_max > self.max_temp_reached:
            self.max_temp_reached = current_T_max
        
        # Verificar muerte microbiana
        if (not self.thermal_death_occurred and 
            current_T_max >= self.mat_props.thermal_limits['T_death_min']):
            
            self.thermal_death_occurred = True
            self.death_time = self.t
            print(f"\n🦠💀 MUERTE MICROBIANA detectada!")
            print(f"   Tiempo: {self.t/3600:.1f}h")
            print(f"   Temperatura máxima: {current_T_max-273.15:.1f}°C")
        
        # Calcular enfriamiento evaporativo primero
        q_evap_values = np.zeros_like(self.geom.material_markers.x.array)
        
        # Solo en el cacao (marcador = 2)
        cacao_indices = np.where(self.geom.material_markers.x.array == 2)[0]
        
        for idx in cacao_indices:
            # Usar temperatura promedio del cacao para evaporación
            T_local = self.T.x.array[idx]
            q_evap = self.mat_props.get_evaporative_cooling_passive(T_local, self.t)
            q_evap_values[idx] = q_evap
        
        # Promedio de enfriamiento evaporativo
        avg_evap_cooling = np.mean(q_evap_values[cacao_indices]) if len(cacao_indices) > 0 else 0
        
        # Calcular generación de calor con retroalimentación
        q_current = self.mat_props.get_fermentation_heat_profile(
            self.t, current_T_max, avg_evap_cooling
        )
        
        # Aplicar generación solo en el cacao
        q_gen_values = np.where(self.geom.material_markers.x.array == 2, 
                               ScalarType(q_current), ScalarType(0.0))
        
        # Asignar valores a las funciones
        self.q_function.x.array[:] = q_gen_values
        self.q_evap_function.x.array[:] = q_evap_values
        
        # Estimar pérdida de humedad
        if len(cacao_indices) > 0 and avg_evap_cooling > 0:
            # Aproximación: q_evap = m_evap * L_vap
            m_evap_rate = avg_evap_cooling / self.mat_props.ventilation['L_vap']  # kg/(m³·s)
            self.total_moisture_loss += m_evap_rate * self.dt  # kg/m³
        
        return q_current, avg_evap_cooling
    
    def solve_transient(self, save_interval=3600):
        """
        Resuelve el problema térmico transitorio
        """
        print("\n🏃 Iniciando simulación...")
        
        # Reiniciar estado
        self.mat_props.reset_microbial_state()
        
        # Crear forma variacional
        a, L, dt_const, T_amb, h_normal, h_ventilated = self.create_variational_form()
        
        # Configurar problema lineal
        problem = LinearProblem(a, L, bcs=[], 
                               petsc_options={"ksp_type": "preonly", 
                                            "pc_type": "lu"})
        
        # Preparar archivos de salida
        filename = os.path.join(self.results_dir, f"bioreactor_{self.bioreactor_type}_evaporation.xdmf")
        xdmf = XDMFFile(self.domain.comm, filename, "w")
        xdmf.write_mesh(self.domain)
        
        # Arrays para estadísticas
        times = []
        T_max_values = []
        T_min_values = []
        T_avg_values = []
        q_gen_values = []
        q_evap_values = []
        moisture_loss_values = []
        
        # Control de salida
        next_save = 0.0
        step = 0
        
        print(f"🌡️ Configuración inicial:")
        print(f"   - T ambiente: {float(T_amb)-273.15:.1f}°C")
        print(f"   - Humedad inicial cacao: {self.mat_props.cacao['moisture_content_initial']*100:.0f}%")
        print(f"   - Objetivo humedad final: {self.mat_props.cacao['moisture_content_final']*100:.0f}%")
        
        # BUCLE TEMPORAL PRINCIPAL
        while self.t < self.t_final:
            self.t += self.dt
            step += 1
            
            # Actualizar generación de calor Y evaporación
            q_gen, q_evap_avg = self.update_heat_generation_and_evaporation()
            
            # Resolver sistema lineal
            try:
                uh = problem.solve()
                self.T.x.array[:] = uh.x.array[:]
                
                # Calcular estadísticas
                T_array = self.T.x.array
                T_max = np.max(T_array)
                T_min = np.min(T_array)
                T_avg = np.mean(T_array)
                
                # Guardar estadísticas
                times.append(self.t)
                T_max_values.append(T_max - 273.15)
                T_min_values.append(T_min - 273.15)
                T_avg_values.append(T_avg - 273.15)
                q_gen_values.append(q_gen)
                q_evap_values.append(q_evap_avg)
                moisture_loss_values.append(self.total_moisture_loss)
                
                # Verificar estabilidad
                if T_max > 400:
                    print(f"⚠️ ADVERTENCIA: Temperatura excesiva ({T_max-273.15:.1f}°C)")
                    break
                
                # Imprimir progreso cada hora
                if step % (3600 // self.dt) == 0:
                    t_hours = self.t / 3600
                    death_status = "💀" if self.thermal_death_occurred else "🦠"
                    moisture_percent = (self.total_moisture_loss / 
                                      (self.mat_props.cacao['moisture_content_initial'] * 
                                       self.mat_props.cacao['rho'])) * 100
                    
                    print(f"  {death_status} t = {t_hours:6.1f}h | "
                          f"T_max = {T_max-273.15:5.1f}°C | "
                          f"T_avg = {T_avg-273.15:5.1f}°C | "
                          f"q_gen = {q_gen:3.0f} W/m³ | "
                          f"q_evap = {q_evap_avg:3.0f} W/m³ | "
                          f"Humedad perdida: {moisture_percent:4.1f}%")
                
                # Guardar resultados
                if self.t >= next_save:
                    xdmf.write_function(self.T, self.t)
                    next_save += save_interval
                
                # Actualizar solución anterior
                self.T_n.x.array[:] = self.T.x.array
                
            except Exception as e:
                print(f"❌ Error en el paso {step}: {e}")
                break
        
        # Cerrar archivo
        xdmf.close()
        
        # Calcular humedad final
        final_moisture_loss_percent = (self.total_moisture_loss / 
                                     (self.mat_props.cacao['moisture_content_initial'] * 
                                      self.mat_props.cacao['rho'])) * 100
        
        print(f"\n✅ Simulación completada!")
        print(f"   Resultados guardados en: {filename}")
        print(f"\n📊 RESUMEN DE RESULTADOS:")
        print(f"   - Temperatura máxima alcanzada: {self.max_temp_reached-273.15:.1f}°C")
        print(f"   - Pérdida total de humedad: {final_moisture_loss_percent:.1f}%")
        
        if self.thermal_death_occurred:
            print(f"   ⚠️ Muerte microbiana: SÍ (t={self.death_time/3600:.1f}h)")
        else:
            print(f"   ✅ Muerte microbiana: NO")
            print(f"   🎉 ¡ÉXITO! ")

        # Guardar estadísticas extendidas
        self.save_statistics(times, T_max_values, T_min_values, T_avg_values, 
                           q_gen_values, q_evap_values, moisture_loss_values)
        
        return times, T_max_values, T_min_values, T_avg_values
    
    def save_statistics(self, times, T_max, T_min, T_avg, q_gen, q_evap, moisture):
        """Guarda estadísticas extendidas de la simulación"""
        import json
        
        times_hours = [t/3600 for t in times]
        
        stats = {
            'bioreactor_type': self.bioreactor_type,
            'material': 'wood',
            'evaporation': 'passive',
            'times_hours': times_hours,
            'T_max_celsius': T_max,
            'T_min_celsius': T_min,
            'T_avg_celsius': T_avg,
            'heat_generation_W_m3': q_gen,
            'evaporative_cooling_W_m3': q_evap,
            'moisture_loss_kg_m3': [float(m) for m in moisture],
            'max_temp_reached_celsius': float(self.max_temp_reached - 273.15),
            'thermal_death_occurred': self.thermal_death_occurred,
            'death_time_hours': float(self.death_time/3600) if self.death_time else None,
            'final_moisture_loss_percent': float(moisture[-1] / 
                                                (self.mat_props.cacao['moisture_content_initial'] * 
                                                 self.mat_props.cacao['rho']) * 100) if moisture else 0
        }
        
        filename = os.path.join(self.results_dir, f"stats_{self.bioreactor_type}_evaporation.json")
        with open(filename, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"📊 Estadísticas guardadas en: {filename}")


def run_evaporation_simulation(bioreactor_type='box'):
    """
    Ejecuta simulación
    """
    print(f"\n{'='*60}")
    print(f"SIMULACIÓN: BIORREACTOR {bioreactor_type.upper()}")
    print(f"💧 ENFRIAMIENTO EVAPORATIVO PASIVO")
    print(f"{'='*60}")
    
    try:
        # Crear y ejecutar modelo
        model = BioreactorThermalModel(bioreactor_type)
        times, T_max, T_min, T_avg = model.solve_transient(save_interval=3600)
        
        # Resumen final
        print(f"\n📈 ANÁLISIS FINAL:")
        print(f"   - Temperatura máxima: {max(T_max):.1f}°C")
        print(f"   - Gradiente térmico máximo: {max([T_max[i]-T_min[i] for i in range(len(T_max))]):.1f}°C")
        
        return model, times, T_max, T_min, T_avg
        
    except Exception as e:
        print(f"❌ Error en la simulación: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, None


if __name__ == "__main__":
    print("🍫 MODELO TÉRMICO")

    # Ejecutar simulación
    model, times, T_max, T_min, T_avg = run_evaporation_simulation('box')
    
    if model is not None:
        print("\n🎉 ¡Simulación completada!")
        print("\n📊 Para visualizar resultados:")
        print("   python visualization_evaporation.py")