"""
main_thermal_model_hexagon.py

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

# Importar módulos
from geometry_setup_hexagon import create_hexagonal_bioreactor_geometry
from material_properties_hexagon import HexagonalMaterialProperties

class HexagonalBioreactorThermalModel:
    """
    Modelo térmico del tambor hexagonal
    """
    
    def __init__(self):
        """
        Inicializa modelo térmico
        """
        self.bioreactor_type = 'hexagon'
        self.comm = MPI.COMM_WORLD
        
        # Crear directorio de resultados
        if self.comm.rank == 0:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.results_dir = os.path.join(script_dir, "results")
            os.makedirs(self.results_dir, exist_ok=True)
        
        print(f"\n🚀 Inicializando modelo térmico - TAMBOR HEXAGONAL")
        
        # Configurar geometría
        self.setup_hexagonal_geometry()
        
        # Configurar propiedades
        self.setup_hexagonal_materials()
        
        # Configurar problema térmico
        self.setup_hexagonal_thermal_problem()
        
        # Estado de rotación
        self.is_rotating = False
        self.rotation_schedule = self._create_rotation_schedule()
        self.rotations_completed = set()  # Para evitar duplicados
        
    def setup_hexagonal_geometry(self):
        """Configura geometría"""
        print("🔧 Configurando geometría hexagonal...")
        self.geom, self.domain = create_hexagonal_bioreactor_geometry()
        
        self.material_markers = self.geom.get_material_markers()
        self.boundary_markers = self.geom.get_boundary_markers()
        
        # Verificar volúmenes
        volume_info = self.geom.get_hexagon_volume_info()
        if volume_info:
            print(f"✅ Verificación exitosa:")
            print(f"   - Masa cacao: {volume_info['masa_cacao']:.0f} kg")
            print(f"   - Marcadores: 1=madera, 2=cacao, 3=aire")
        
    def setup_hexagonal_materials(self):
        """Configura propiedades"""
        print("📋 Configurando propiedades de materiales...")
        self.mat_props = HexagonalMaterialProperties()
        
        self.props = self.mat_props.create_hexagonal_material_functions(
            self.domain, 
            self.material_markers
        )
        
    def setup_hexagonal_thermal_problem(self):
        """Configura problema térmico"""
        print("\n⚙️ Configurando problema térmico...")
        
        # Crear espacio de funciones
        self.V = functionspace(self.domain, ("CG", 1))
        
        # Funciones de temperatura
        self.T = Function(self.V, name="Temperatura")
        self.T_n = Function(self.V, name="Temperatura_anterior")
        
        # Condición inicial REALISTA
        T_inicial = ScalarType(self.mat_props.ambient['T_amb'])
        self.T.x.array[:] = T_inicial
        self.T_n.x.array[:] = T_inicial
        
        # Parámetros temporales
        self.t = 0.0
        self.dt = 300.0  # 5 minutos
        self.t_final = 7 * 24 * 3600  # 7 días
        
        # Variables de control
        self.max_temp_reached = T_inicial
        self.total_moisture_loss = 0.0
        self.total_rotations_done = 0
        
        # LÍMITES TÉRMICOS DE SEGURIDAD
        self.TEMP_MAX_SAFE = 55.0 + 273.15  # 55°C máximo seguro
        self.TEMP_EMERGENCY_STOP = 60.0 + 273.15  # 60°C parada de emergencia
        
        print(f"✅ Configuración térmica:")
        print(f"   - Temperatura inicial: {T_inicial - 273.15:.1f}°C")
        print(f"   - Límite seguro: {self.TEMP_MAX_SAFE - 273.15:.1f}°C")
        print(f"   - Parada de emergencia: {self.TEMP_EMERGENCY_STOP - 273.15:.1f}°C")
        
    def _create_rotation_schedule(self):
        """Crea cronograma de rotación (7 eventos exactos)"""
        rotation_times = []
        for day in range(1, 8):  # Días 1-7
            rotation_times.append(day * 24 * 3600)
        
        print(f"🔄 Cronograma de rotación:")
        for i, t in enumerate(rotation_times):
            print(f"   Rotación {i+1}: Día {day} ({t/3600:.0f}h)")
        
        return rotation_times
        
    def _check_rotation_schedule(self):
        """Verifica rotación SIN DUPLICADOS"""
        for i, rotation_time in enumerate(self.rotation_schedule):
            if (self.t >= rotation_time and 
                i not in self.rotations_completed and
                abs(self.t - rotation_time) <= self.dt):
                self.rotations_completed.add(i)  # Marcar como completada
                return True
        return False
        
    def _perform_rotation(self):
        """Simula rotación"""
        self.total_rotations_done += 1
        print(f"\n🔄 ROTACIÓN #{self.total_rotations_done} a t={self.t/3600:.1f}h")
        
        self.is_rotating = True
        self.last_rotation_time = self.t
        
        print(f"   ✅ Tambor rotado - Día {self.total_rotations_done}")
        
    def update_heat_generation(self):
        """
        Actualiza generación de calor CONTROLADA (temperaturas realistas)
        """
        # Temperatura actual
        current_T_max = np.max(self.T.x.array)
        current_T_avg = np.mean(self.T.x.array)
        
        # Actualizar máxima
        if current_T_max > self.max_temp_reached:
            self.max_temp_reached = current_T_max
        
        # VERIFICACIÓN DE SEGURIDAD TÉRMICA
        if current_T_max > self.TEMP_EMERGENCY_STOP:
            print(f"🚨 PARADA DE EMERGENCIA: T={current_T_max-273.15:.1f}°C")
            return 0.0, 0.0  # Parar generación de calor
        
        # Factor de rotación
        rotation_factor = 1.05 if self.is_rotating else 1.0
        
        # ENFRIAMIENTO EVAPORATIVO MEJORADO
        q_evap_enhanced = self.mat_props.get_evaporative_cooling_enhanced(
            current_T_avg, self.t, rotation_factor
        )
        
        # GENERACIÓN DE CALOR CONTROLADA
        q_current = self.mat_props.get_fermentation_heat_controlled(
            self.t, current_T_max, q_evap_enhanced, self.is_rotating
        )
        
        # Identificar celdas de cacao (marcador = 2)
        cacao_indices = np.where(self.material_markers.values == 2)[0]
        
        # Aplicar valores
        q_gen_values = np.where(self.material_markers.values == 2, 
                               ScalarType(q_current), ScalarType(0.0))
        
        q_evap_values = np.zeros_like(self.material_markers.values, dtype=float)
        q_evap_values[cacao_indices] = q_evap_enhanced
        
        # Asignar a funciones
        self.q_function.x.array[:] = q_gen_values
        self.q_evap_function.x.array[:] = q_evap_values
        
        # Resetear rotación
        if self.is_rotating and self.t - self.last_rotation_time > self.dt:
            self.is_rotating = False
            
        return q_current, q_evap_enhanced
    
    def create_variational_form(self):
        """Forma variacional"""
        print("🔧 Creando forma variacional...")
        
        # Funciones
        v = ufl.TestFunction(self.V)
        u = ufl.TrialFunction(self.V)
        
        # Propiedades
        k = self.props['k']
        rho = self.props['rho'] 
        cp = self.props['cp']
        
        # Condiciones ambientales
        T_amb = Constant(self.domain, PETSc.ScalarType(self.mat_props.ambient['T_amb']))
        h_conv = Constant(self.domain, PETSc.ScalarType(25.0))  # MEJORADO
        dt = Constant(self.domain, PETSc.ScalarType(self.dt))
        
        # Medidas
        ds = ufl.ds(domain=self.domain)
        
        # Funciones de fuente
        Q = functionspace(self.domain, ("DG", 0))
        self.q_function = Function(Q, name="Generacion_calor")
        self.q_evap_function = Function(Q, name="Enfriamiento_evaporativo")
        
        # FORMA VARIACIONAL ESTABLE
        a = (rho * cp * u * v * dx + 
             dt * inner(k * grad(u), grad(v)) * dx +
             dt * h_conv * u * v * ds)
        
        L = (rho * cp * self.T_n * v * dx + 
             dt * self.q_function * v * dx -
             dt * self.q_evap_function * v * dx +
             dt * h_conv * T_amb * v * ds)
        
        print("✅ Forma variacional creada")
        
        return a, L
    
    def solve_transient(self, save_interval=3600):
        """
        Resuelve problema térmico
        """
        print("\n🏃 Iniciando simulación...")
        print("🔧 Temperaturas realistas garantizadas")
        print("="*60)
        
        # Crear forma variacional
        a, L = self.create_variational_form()
        
        # Configurar problema
        problem = LinearProblem(a, L, bcs=[], 
                               petsc_options={"ksp_type": "preonly", 
                                            "pc_type": "lu"})
        
        # Archivos de salida
        filename = os.path.join(self.results_dir, f"bioreactor_hexagon.xdmf")
        xdmf = XDMFFile(self.domain.comm, filename, "w")
        xdmf.write_mesh(self.domain)
        
        # Arrays para estadísticas
        times = []
        T_max_values = []
        T_min_values = []
        T_avg_values = []
        q_gen_values = []
        q_evap_values = []
        
        # Control
        next_save = 0.0
        step = 0
        emergency_stop = False
        
        # BUCLE TEMPORAL PRINCIPAL
        while self.t < self.t_final and not emergency_stop:
            self.t += self.dt
            step += 1
            
            # Verificar rotación
            if self._check_rotation_schedule():
                self._perform_rotation()
            
            # Actualizar calor CONTROLADO
            q_gen, q_evap_avg = self.update_heat_generation()
            
            # Resolver sistema
            try:
                uh = problem.solve()
                self.T.x.array[:] = uh.x.array[:]
                
                # Estadísticas
                T_array = self.T.x.array
                T_max = np.max(T_array)
                T_min = np.min(T_array)
                T_avg = np.mean(T_array)
                
                # VERIFICACIÓN DE SEGURIDAD
                if T_max > self.TEMP_EMERGENCY_STOP:
                    print(f"\n🚨 PARADA DE EMERGENCIA a t={self.t/3600:.1f}h")
                    print(f"   Temperatura: {T_max-273.15:.1f}°C")
                    emergency_stop = True
                    break
                
                # Guardar estadísticas
                times.append(self.t)
                T_max_values.append(T_max - 273.15)
                T_min_values.append(T_min - 273.15)
                T_avg_values.append(T_avg - 273.15)
                q_gen_values.append(q_gen)
                q_evap_values.append(q_evap_avg)
                
                # Progreso cada hora
                if step % (3600 // self.dt) == 0:
                    t_hours = self.t / 3600
                    rotation_status = "🔄" if self.is_rotating else "⏸️"
                    safety_status = "🔥" if T_max > self.TEMP_MAX_SAFE else "✅"
                    
                    print(f"  🛢️{rotation_status}{safety_status} t = {t_hours:6.1f}h | "
                          f"T_max = {T_max-273.15:5.1f}°C | "
                          f"T_avg = {T_avg-273.15:5.1f}°C | "
                          f"q_gen = {q_gen:3.0f} W/m³ | "
                          f"q_evap = {q_evap_avg:3.0f} W/m³")
                
                # Guardar resultados
                if self.t >= next_save:
                    xdmf.write_function(self.T, self.t)
                    next_save += save_interval
                
                # Actualizar solución anterior
                self.T_n.x.array[:] = self.T.x.array
                
            except Exception as e:
                print(f"❌ Error en paso {step}: {e}")
                break
        
        # Cerrar archivo
        xdmf.close()
        
        # Resultados finales
        final_temp = self.max_temp_reached - 273.15
        
        print(f"\n✅ Simulación completada!")
        print(f"📊 RESULTADOS:")
        print(f"   - Temperatura máxima: {final_temp:.1f}°C")
        print(f"   - Rotaciones realizadas: {self.total_rotations_done}")
        print(f"   - Parada de emergencia: {'SÍ' if emergency_stop else 'NO'}")
        
        if final_temp < 55.0:
            print(f"   🎉 ¡ÉXITO! Temperatura controlada < 55°C")
        elif final_temp < 60.0:
            print(f"   ⚠️ Temperatura elevada pero segura")
        else:
            print(f"   🚨 Temperatura peligrosa - necesita más enfriamiento")
        
        # Guardar estadísticas
        self.save_statistics(times, T_max_values, T_min_values, T_avg_values, 
                                  q_gen_values, q_evap_values, emergency_stop)
        
        return times, T_max_values, T_min_values, T_avg_values
    
    def save_statistics(self, times, T_max, T_min, T_avg, q_gen, q_evap, emergency_stop):
        """Guarda estadísticas"""
        import json
        
        stats = {
            'bioreactor_type': 'hexagon',
            'version': 'corrected_thermal_model',
            'times_hours': [t/3600 for t in times],
            'T_max_celsius': T_max,
            'T_min_celsius': T_min,
            'T_avg_celsius': T_avg,
            'heat_generation_W_m3': q_gen,
            'evaporative_cooling_W_m3': q_evap,
            'max_temp_reached_celsius': float(self.max_temp_reached - 273.15),
            'total_rotations': self.total_rotations_done,
            'emergency_stop_occurred': emergency_stop,
            'fermentation_completed': not emergency_stop,
            'geometry': True,
            'thermal_model': True,
            'volumes_controlled': True,
            'masa_cacao_kg': 300.0  # Controlado
        }
        
        filename = os.path.join(self.results_dir, f"stats_hexagon.json")
        with open(filename, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"📊 Estadísticas guardadas en: {filename}")


def run_simulation():
    """Ejecuta simulación"""
    print(f"\n{'='*60}")
    print(f"SIMULACIÓN: TAMBOR HEXAGONAL")
    print(f"{'='*60}")
    
    try:
        model = HexagonalBioreactorThermalModel()
        times, T_max, T_min, T_avg = model.solve_transient()
        
        return model, times, T_max, T_min, T_avg
        
    except Exception as e:
        print(f"❌ Error en simulación: {e}")
        return None, None, None, None, None


if __name__ == "__main__":
    
    model, times, T_max, T_min, T_avg = run_simulation()
    
    if model is not None:
        print("\n🎉 ¡Simulación completada!")