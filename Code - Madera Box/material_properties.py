"""
material_properties.py
Propiedades térmicas
Proyecto: Modelado térmico de biorreactores para fermentación de cacao

"""

import numpy as np
from dolfinx.fem import Function, functionspace
import ufl

class MaterialProperties:
    """
    Clase para gestionar las propiedades térmicas -
    """
    
    def __init__(self):
        """
        Define las propiedades térmicas incluyendo
        """
        
        # MADERA DE CEDRO (sin cambios)
        self.wood = {
            'name': 'Madera de Cedro',
            'k': 0.128,      # Conductividad térmica [W/m·K]
            'rho': 420.0,    # Densidad [kg/m³]
            'cp': 2000.0,    # Calor específico [J/kg·K]
            'alpha': None    # Difusividad térmica [m²/s]
        }
        
        # CACAO EN FERMENTACIÓN - Con propiedades de humedad
        self.cacao = {
            'name': 'Cacao en Fermentación',
            'k': 0.279,      # Conductividad térmica promedio [W/m·K]
            'rho': 910.0,    # Densidad [kg/m³]
            'cp': 920.0,     # Calor específico [J/kg·K]
            'alpha': None,   # Difusividad térmica [m²/s]
            # NUEVO: Propiedades de humedad
            'moisture_content_initial': 0.40,  # 40% contenido inicial de humedad
            'moisture_content_final': 0.07,    # 7% contenido final (después de 7 días)
            'water_activity': 0.95,            # Actividad de agua alta inicialmente
            'porosity': 0.45                   # Porosidad del lecho de cacao
        }
        
        # Calcular difusividades térmicas
        self._calculate_diffusivities()
        
        # Condiciones ambientales - Pueblo Bello, Cesar
        self.ambient = {
            'T_amb': 21.0 + 273.15,  # Temperatura ambiente [K] (21°C)
            'h_conv': 10.0,          # Coeficiente de convección base [W/m²·K]
            'T_variation': 3.0,      # Variación de temperatura [°C]
            'RH': 0.65,              # Humedad relativa ambiente 65%
            'P_atm': 101325,         # Presión atmosférica [Pa]
            'wind_speed': 0.5        # Velocidad del viento natural [m/s]
        }
        
        # LÍMITES TÉRMICOS (sin cambios)
        self.thermal_limits = {
            'T_death_min': 55.0 + 273.15,  # Temperatura de muerte mínima [K] (55°C)
            'T_death_max': 60.0 + 273.15,  # Temperatura de muerte máxima [K] (60°C)
            'T_optimal_min': 40.0 + 273.15, # Temperatura óptima mínima
            'T_optimal_max': 48.0 + 273.15, # Temperatura óptima máxima
            'death_is_permanent': True
        }
        
        # VENTILACIÓN MÚLTIPLE MEJORADA
        self.ventilation = {
            # Geometría actual
            'hole_diameter': 0.005,           # Mantener 5mm
            'bottom_area_fraction': 0.50,     # Mantener 50% inferior
            'lateral_area_fraction': 0.25,    # Mantener 25% lateral
            
            # Convección natural mejorada por evaporación
            'enhanced_h_conv': 80.0,          # Reducido a 80 W/m²·K (más realista sin ventilador)
            'has_bottom_holes': True,
            'has_lateral_holes': True,
            
            # EVAPORACIÓN PASIVA (clave para enfriamiento)
            'evaporation_enabled': True,
            'evaporation_model': 'passive',   # Modo pasivo
            'L_vap': 2.257e6,                 # Calor latente de vaporización [J/kg] a 45°C
            
            # Parámetros de evaporación pasiva
            'vapor_diffusivity': 2.5e-5,      # Difusividad del vapor en aire [m²/s]
            'mass_transfer_coeff_natural': 0.001,  # Coef. transferencia masa natural [m/s]
            'lewis_number': 0.865,            # Número de Lewis para aire-vapor agua
            
            # Factor de mejora por convección natural
            'buoyancy_enhancement': 0.9,      # El aire caliente húmedo sube, mejorando el flujo
        }
        
        # Control de fermentación
        self.fermentation_control = {
            'smart_heat_management': True,
            'heat_reduction_factor': 1.0,    # Aumentar ligeramente la generación
            'evaporative_cooling_feedback': True  # Ajustar fermentación según enfriamiento
        }
        
        # Estado de los microorganismos con control de humedad
        self.microbial_state = {
            'is_alive': True,
            'death_time': None,
            'stress_level': 0.0,
            'activity_factor': 1.0,
            'moisture_stress': 0.0    # Nuevo: estrés por pérdida de humedad
        }
        
    def _calculate_diffusivities(self):
        """Calcula la difusividad térmica α = k/(ρ·cp) para cada material"""
        self.wood['alpha'] = self.wood['k'] / (self.wood['rho'] * self.wood['cp'])
        self.cacao['alpha'] = self.cacao['k'] / (self.cacao['rho'] * self.cacao['cp'])
    
    def get_evaporative_cooling_passive(self, T, t, T_surface=None):
        """
        Calcula el enfriamiento evaporativo PASIVO
        Basado en diferencias de presión de vapor y convección natural
        
        Parámetros:
        -----------
        T : float
            Temperatura del cacao [K]
        t : float
            Tiempo actual [s]
        T_surface : float
            Temperatura de superficie (si es diferente)
            
        Retorna:
        --------
        q_evap : float
            Flujo de calor por evaporación [W/m³] (volumétrico)
        """
        if not self.ventilation['evaporation_enabled']:
            return 0.0
        
        # Usar temperatura de superficie si se proporciona
        T_evap = T_surface if T_surface is not None else T
        T_celsius = T_evap - 273.15
        
        # Contenido de humedad actual (disminuye linealmente con el tiempo)
        t_days = t / (24 * 3600)
        moisture_fraction = (self.cacao['moisture_content_initial'] - 
                           (self.cacao['moisture_content_initial'] - self.cacao['moisture_content_final']) * 
                           min(t_days / 7.0, 1.0))
        
        # Si la humedad es muy baja, reducir evaporación
        if moisture_fraction < 0.10:
            moisture_factor = moisture_fraction / 0.10
        else:
            moisture_factor = 1.0
        
        # Presión de vapor saturado (Magnus-Tetens)
        if T_celsius > 0:
            P_sat = 610.78 * np.exp(17.27 * T_celsius / (T_celsius + 237.3))
        else:
            P_sat = 610.78
        
        # Actividad de agua disminuye con el tiempo
        a_w = self.cacao['water_activity'] * (0.7 + 0.3 * (1 - t_days/7.0))
        
        # Presión de vapor en la superficie del cacao
        P_vapor_surface = a_w * P_sat
        
        # Presión de vapor ambiente
        T_amb_celsius = self.ambient['T_amb'] - 273.15
        P_sat_amb = 610.78 * np.exp(17.27 * T_amb_celsius / (T_amb_celsius + 237.3))
        P_vapor_ambient = self.ambient['RH'] * P_sat_amb
        
        # Gradiente de presión de vapor
        delta_P = P_vapor_surface - P_vapor_ambient
        
        if delta_P <= 0:
            return 0.0
        
        # Coeficiente de transferencia de masa por convección natural
        # Aumenta con la diferencia de temperatura (efecto chimenea)
        delta_T = T_evap - self.ambient['T_amb']
        if delta_T > 0:
            # Número de Grashof para convección natural
            g = 9.81  # gravedad
            beta = 1 / T_evap  # coef. expansión térmica
            L = 0.5  # longitud característica (altura de cacao)
            nu = 1.5e-5  # viscosidad cinemática del aire
            
            Gr = g * beta * delta_T * L**3 / nu**2
            
            # Factor de mejora por convección natural (correlación simplificada)
            if Gr > 1e4:  # Convección natural significativa
                enhancement = 1.0 + 0.5 * np.log10(Gr / 1e4)
                enhancement = min(enhancement, self.ventilation['buoyancy_enhancement'])
            else:
                enhancement = 1.0
        else:
            enhancement = 1.0
        
        # Coeficiente efectivo de transferencia de masa
        h_mass = self.ventilation['mass_transfer_coeff_natural'] * enhancement
        
        # Densidad del aire
        rho_air = self.ambient['P_atm'] / (287.05 * T_evap)
        
        # Tasa de evaporación [kg/m²·s]
        # Usando analogía de Chilton-Colburn
        M_water = 0.018  # kg/mol
        R = 8314  # J/(mol·K)
        
        m_evap = h_mass * (M_water / (R * T_evap)) * delta_P * moisture_factor
        
        # Área específica de evaporación [m²/m³]
        # Basada en el tamaño de los granos y porosidad
        d_bean = 0.01  # diámetro promedio del grano [m]
        a_specific = 6 * (1 - self.cacao['porosity']) / d_bean
        
        # Flujo de calor evaporativo volumétrico [W/m³]
        q_evap = m_evap * self.ventilation['L_vap'] * a_specific
        
        # Límites físicos
        # Máximo basado en la humedad disponible
        max_evap_rate = moisture_fraction * 1000  # kg/m³ de agua disponible
        max_q_evap = (max_evap_rate / (7 * 24 * 3600)) * self.ventilation['L_vap']
        
        q_evap = min(q_evap, max_q_evap)
        q_evap = min(q_evap, 100.0)  # Límite máximo realista [W/m³]
        
        return q_evap
    
    def get_fermentation_heat_profile(self, t, current_T_max=None, evap_cooling=0):
        """
        Perfil de generación de calor con retroalimentación del enfriamiento evaporativo
        """
        # Verificar muerte microbiana
        if current_T_max is not None:
            # Actualizar nivel de estrés térmico
            if current_T_max > self.thermal_limits['T_optimal_max']:
                thermal_stress = (current_T_max - self.thermal_limits['T_optimal_max']) / 10.0
                self.microbial_state['stress_level'] = min(1.0, thermal_stress)
            else:
                self.microbial_state['stress_level'] = 0.0
            
            # Estrés por humedad (si se está evaporando mucho)
            if evap_cooling > 150:  # W/m³
                self.microbial_state['moisture_stress'] = min(1.0, evap_cooling / 300)
            else:
                self.microbial_state['moisture_stress'] = 0.0
            
            # Factor de actividad combinado
            total_stress = max(self.microbial_state['stress_level'], 
                             self.microbial_state['moisture_stress'])
            self.microbial_state['activity_factor'] = 1.0 - 0.6 * total_stress
            
            # Verificar muerte
            if current_T_max >= self.thermal_limits['T_death_min']:
                if self.microbial_state['is_alive']:
                    print(f"⚠️ MUERTE MICROBIANA detectada a t={t/3600:.1f}h, T={current_T_max-273.15:.1f}°C")
                    self.microbial_state['is_alive'] = False
                    self.microbial_state['death_time'] = t
                    self.microbial_state['activity_factor'] = 0.0
        
        # Obtener calor base
        q_base = self._get_base_heat_profile(t)
        
        # Aplicar factor de control inteligente
        if self.fermentation_control['smart_heat_management']:
            q_base *= self.fermentation_control['heat_reduction_factor']
        
        # Aplicar factor de actividad microbiana
        q_base *= self.microbial_state['activity_factor']
        
        # Si están muertos, decaimiento exponencial
        if not self.microbial_state['is_alive'] and self.microbial_state['death_time'] is not None:
            time_since_death = t - self.microbial_state['death_time']
            decay_factor = np.exp(-time_since_death / (6 * 3600))
            q_base *= decay_factor
        
        return q_base
    
    def _get_base_heat_profile(self, t):
        """
        Perfil base de generación de calor
        """
        t_hours = t / 3600.0
        
        # Valores ajustados considerando enfriamiento evaporativo
        if t_hours < 12:
            # Fase inicial (0-12h)
            q = 90.0 + (130.0 - 90.0) * (t_hours / 12.0)
        elif t_hours < 36:
            # Fermentación rápida (12-36h)
            q = 130.0 + (220.0 - 130.0) * ((t_hours - 12.0) / 24.0)
        elif t_hours < 84:
            # Pico bacterial (36-84h)
            q = 220.0 + (320.0 - 220.0) * ((t_hours - 36.0) / 48.0)
        elif t_hours < 168:
            # Declive (84-168h)
            q = 320.0 - (320.0 - 180.0) * ((t_hours - 84.0) / 84.0)
        else:
            # Después de 7 días
            q = 180.0
            
        return q
    
    def create_material_functions(self, domain, material_markers):
        """
        Crea funciones de FEniCSx para las propiedades
        """
        # Crear espacio de funciones DG0
        Q = functionspace(domain, ("DG", 0))
        
        # Crear funciones para cada propiedad
        k_func = Function(Q, name="Conductividad")
        rho_func = Function(Q, name="Densidad")
        cp_func = Function(Q, name="Calor_especifico")
        
        # Obtener array de marcadores
        markers = material_markers.x.array
        
        # Asignar valores: 1 = madera, 2 = cacao
        k_values = np.where(markers == 1, self.wood['k'], self.cacao['k'])
        rho_values = np.where(markers == 1, self.wood['rho'], self.cacao['rho'])
        cp_values = np.where(markers == 1, self.wood['cp'], self.cacao['cp'])
        
        # Asignar a las funciones
        k_func.x.array[:] = k_values
        rho_func.x.array[:] = rho_values
        cp_func.x.array[:] = cp_values
        
        print(f"\n📋 Propiedades de materiales asignadas:")
        print(f"   Paredes: {self.wood['name']}")
        print(f"   Interior: {self.cacao['name']}")
        print(f"   ✨ Con enfriamiento evaporativo pasivo")
        
        return {
            'k': k_func,
            'rho': rho_func,
            'cp': cp_func,
            'wood_material': self.wood,
            'cacao_material': self.cacao
        }
    
    def reset_microbial_state(self):
        """Reinicia el estado microbiano"""
        self.microbial_state = {
            'is_alive': True,
            'death_time': None,
            'stress_level': 0.0,
            'activity_factor': 1.0,
            'moisture_stress': 0.0
        }
    
    def print_summary(self):
        """Imprime resumen de propiedades"""
        print("\n" + "="*60)
        print("PROPIEDADES TÉRMICAS -")
        print("="*60)
        
        print(f"\n{self.wood['name']} (Paredes):")
        print(f"  - Conductividad (k): {self.wood['k']:.3f} W/m·K")
        print(f"  - Densidad (ρ): {self.wood['rho']:.1f} kg/m³")
        print(f"  - Calor específico (cp): {self.wood['cp']:.1f} J/kg·K")
        
        print(f"\n{self.cacao['name']} (Interior):")
        print(f"  - Conductividad (k): {self.cacao['k']:.3f} W/m·K")
        print(f"  - Densidad (ρ): {self.cacao['rho']:.1f} kg/m³")
        print(f"  - Calor específico (cp): {self.cacao['cp']:.1f} J/kg·K")
        print(f"  - Humedad inicial: {self.cacao['moisture_content_initial']*100:.0f}%")
        print(f"  - Humedad final: {self.cacao['moisture_content_final']*100:.0f}%")
        
        print(f"\nCondiciones ambientales (Pueblo Bello):")
        print(f"  - Temperatura: {self.ambient['T_amb']-273.15:.1f}°C")
        print(f"  - Humedad relativa: {self.ambient['RH']*100:.0f}%")
        print(f"  - Coef. convección base: {self.ambient['h_conv']:.1f} W/m²·K")
        
        print(f"\nEnfriamiento evaporativo:")
        print(f"  - Modo: PASIVO (convección natural)")
        print(f"  - Calor latente: {self.ventilation['L_vap']/1e6:.2f} MJ/kg")
        print(f"  - Factor mejora por flotabilidad: {self.ventilation['buoyancy_enhancement']:.1f}x")
        print(f"  - Pérdida de humedad esperada: {(self.cacao['moisture_content_initial']-self.cacao['moisture_content_final'])*100:.0f}%")
        
        print(f"\nVentilación (sin cambios):")
        print(f"  - Inferior: {self.ventilation['bottom_area_fraction']*100:.0f}%")
        print(f"  - Lateral: {self.ventilation['lateral_area_fraction']*100:.0f}%")
        print(f"  - Coef. convección mejorado: {self.ventilation['enhanced_h_conv']:.0f} W/m²·K")


def test_evaporative_cooling():
    """Prueba el enfriamiento evaporativo"""
    props = MaterialProperties()
    props.print_summary()
    
    print("\n💧 Probando enfriamiento evaporativo:")
    temperatures = [30, 40, 45, 50, 55]  # °C
    times = [12, 36, 60, 84]  # horas
    
    for T_c in temperatures:
        T_k = T_c + 273.15
        for t_h in times:
            t_s = t_h * 3600
            q_evap = props.get_evaporative_cooling_passive(T_k, t_s)
            print(f"  T={T_c}°C, t={t_h}h: q_evap = {q_evap:.1f} W/m³")


if __name__ == "__main__":
    test_evaporative_cooling()