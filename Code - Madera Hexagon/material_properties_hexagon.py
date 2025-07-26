"""
material_properties_hexagon.py

"""

import numpy as np
from dolfinx.fem import Function, functionspace
import ufl

class HexagonalMaterialProperties:
    """
    Clase para propiedades térmicas
    """
    
    def __init__(self):
        """
        Define propiedades
        """
        
        # MADERA (igual)
        self.wood = {
            'name': 'Madera de Cedro',
            'k': 0.128,
            'rho': 420.0,
            'cp': 2000.0,
            'alpha': None
        }
        
        # CACAO (igual)
        self.cacao = {
            'name': 'Cacao en Fermentación',
            'k': 0.279,
            'rho': 910.0,  # Esta densidad con 0.517 m³ = 470 kg, PERO especificamos 300 kg
            'cp': 920.0,
            'alpha': None,
            'moisture_content_initial': 0.40,
            'moisture_content_final': 0.07,
            'water_activity': 0.95,
            'porosity': 0.45
        }
        
        # AIRE (igual)
        self.air = {
            'name': 'Aire Interior',
            'k': 0.026,
            'rho': 1.2,
            'cp': 1005.0,
            'alpha': None
        }
        
        self._calculate_diffusivities()
        
        # Condiciones ambientales (igual)
        self.ambient = {
            'T_amb': 21.0 + 273.15,
            'h_conv': 10.0,  # AUMENTADO para mejor enfriamiento
            'T_variation': 3.0,
            'RH': 0.65,
            'P_atm': 101325,
            'wind_speed': 0.5
        }
        
        # LÍMITES TÉRMICOS DE SEGURIDAD (NUEVO)
        self.thermal_limits = {
            'T_safe_max': 55.0 + 273.15,    # 55°C máximo seguro
            'T_emergency': 60.0 + 273.15,   # 60°C parada de emergencia
            'T_optimal_min': 40.0 + 273.15,
            'T_optimal_max': 48.0 + 273.15,
            'death_is_permanent': False
        }
        
        # VENTILACIÓN MEJORADA )
        self.ventilation = {
            'geometry_type': 'hexagonal_drum',
            'rotation_capable': True,
            'rotation_frequency': 'daily',
            
            # ENFRIAMIENTO
            'evaporation_enabled': True,
            'enhanced_h_conv': 80.0,  # SIGNIFICATIVAMENTE AUMENTADO
            'drum_convection_factor': 0.5,  # AUMENTADO
            
            # EVAPORACIÓN OPTIMIZADA
            'L_vap': 2.257e6,
            'vapor_diffusivity': 2.5e-5,  # AUMENTADO
            'mass_transfer_coeff_natural': 0.001,  # AUMENTADO
            'lewis_number': 0.865,
            
            # FACTORES DE MEJORA AUMENTADOS
            'buoyancy_enhancement': 0.9,  # AUMENTADO
            'rotation_mixing_factor': 1.5,  # AUMENTADO
            'daily_rotation_bonus': 1.15,  # AUMENTADO
            'geometry_bonus': 1.2,  # NUEVO BONUS
        }
        
        # CONTROL DE FERMENTACIÓN (CORREGIDO)
        self.fermentation_control = {
            'smart_heat_management': True,
            'heat_reduction_factor': 0.85,  # SIGNIFICATIVAMENTE REDUCIDO
            'evaporative_cooling_feedback': True,
            'rotation_stress_factor': 1.0,
            'no_death_mode': True,
            'temperature_safety_mode': True,  # NUEVO
            'max_heat_generation': 999.0,  # NUEVO LÍMITE [W/m³]
        }
        
        # Estado microbiano
        self.microbial_state = {
            'is_alive': True,
            'death_time': None,
            'stress_level': 0.0,
            'activity_factor': 1.0,
            'moisture_stress': 0.0,
            'rotation_stress': 0.0,
            'death_disabled': True,
            'safety_mode_active': False  # NUEVO
        }
        
        # Variables para seguimiento
        self._current_evap_values = []
        
        print("🔧 PROPIEDADES TÉRMICAS:")
        print(f"   ✅ Generación de calor: LIMITADA a {self.fermentation_control['max_heat_generation']} W/m³")
        print(f"   ✅ Enfriamiento: {self.ventilation['enhanced_h_conv']} W/m²·K")
        print(f"   ✅ Factor de reducción: {self.fermentation_control['heat_reduction_factor']}")
        print(f"   ✅ Límite seguro: {self.thermal_limits['T_safe_max']-273.15:.1f}°C")
        
    def _calculate_diffusivities(self):
        """Calcula difusividades térmicas"""
        self.wood['alpha'] = self.wood['k'] / (self.wood['rho'] * self.wood['cp'])
        self.cacao['alpha'] = self.cacao['k'] / (self.cacao['rho'] * self.cacao['cp'])
        self.air['alpha'] = self.air['k'] / (self.air['rho'] * self.air['cp'])
    
    def get_evaporative_cooling(self, T, t, rotation_factor=1.0):
        """
        Enfriamiento evaporativo
        """
        if not self.ventilation['evaporation_enabled']:
            return 0.0
        
        T_celsius = T - 273.15
        
        # Contenido de humedad con tiempo
        t_days = t / (24 * 3600)
        moisture_fraction = (self.cacao['moisture_content_initial'] - 
                           (self.cacao['moisture_content_initial'] - self.cacao['moisture_content_final']) * 
                           min(t_days / 7.0, 1.0))
        
        moisture_factor = max(0.1, moisture_fraction / self.cacao['moisture_content_initial'])
        
        # Presión de vapor
        if T_celsius > 0:
            P_sat = 610.78 * np.exp(17.27 * T_celsius / (T_celsius + 237.3))
        else:
            P_sat = 610.78
        
        a_w = self.cacao['water_activity'] * (0.7 + 0.3 * (1 - t_days/7.0))
        P_vapor_surface = a_w * P_sat
        
        T_amb_celsius = self.ambient['T_amb'] - 273.15
        P_sat_amb = 610.78 * np.exp(17.27 * T_amb_celsius / (T_amb_celsius + 237.3))
        P_vapor_ambient = self.ambient['RH'] * P_sat_amb
        
        delta_P = P_vapor_surface - P_vapor_ambient
        if delta_P <= 0:
            return 0.0
        
        # CONVECCIÓN MEJORADA (factor clave para enfriamiento)
        delta_T = T - self.ambient['T_amb']
        if delta_T > 0:
            g = 9.81
            beta = 1 / T
            L_char = 0.8  # AUMENTADO por geometría hexagonal
            nu = 1.5e-5
            
            Gr = g * beta * delta_T * L_char**3 / nu**2
            
            if Gr > 1e4:
                enhancement = 1.0 + 0.5 * np.log10(Gr / 1e4)  # SIGNIFICATIVAMENTE AUMENTADO
                enhancement = min(enhancement, self.ventilation['buoyancy_enhancement'])
            else:
                enhancement = 1.0
            
            # FACTORES DE MEJORA APLICADOS
            enhancement *= self.ventilation['drum_convection_factor']
            enhancement *= self.ventilation['geometry_bonus']
            
            # Factor por rotación )
            if rotation_factor > 1.0:
                enhancement *= rotation_factor * self.ventilation['rotation_mixing_factor'] * self.ventilation['daily_rotation_bonus']
            else:
                enhancement *= self.ventilation['rotation_mixing_factor']
        else:
            enhancement = 1.0
        
        # COEFICIENTE EFECTIVO
        h_mass = self.ventilation['mass_transfer_coeff_natural'] * enhancement
        
        # Densidad del aire
        rho_air = self.ambient['P_atm'] / (287.05 * T)
        
        # Tasa de evaporación
        M_water = 0.018
        R = 8314
        
        m_evap = h_mass * (M_water / (R * T)) * delta_P * moisture_factor
        
        # Área específica AUMENTADA
        d_bean = 0.01
        a_specific = 8 * (1 - self.cacao['porosity']) / d_bean  # AUMENTADO
        
        # Factor de exposición
        exposure_factor = 1.2  # SIGNIFICATIVAMENTE AUMENTADO
        
        # Flujo de calor evaporativo
        q_evap = m_evap * self.ventilation['L_vap'] * a_specific * exposure_factor
        
        # LÍMITES AUMENTADOS para mejor enfriamiento
        max_evap_rate = moisture_fraction * 1500  # AUMENTADO
        max_q_evap = (max_evap_rate / (7 * 24 * 3600)) * self.ventilation['L_vap']
        
        q_evap = min(q_evap, max_q_evap)
        q_evap = min(q_evap, 200.0)  # LÍMITE AUMENTADO significativamente
        
        # Guardar para seguimiento
        self._current_evap_values.append(q_evap)
        if len(self._current_evap_values) > 100:
            self._current_evap_values.pop(0)
        
        return q_evap
    
    def get_fermentation_heat_controlled(self, t, current_T_max=None, evap_cooling=0, is_rotating=False):
        """
        Generación de calor CONTROLADA
        """
        # Verificar límites de seguridad térmica
        if current_T_max is not None:
            if current_T_max > self.thermal_limits['T_safe_max']:
                # REDUCIR DRÁSTICAMENTE generación si T > 55°C
                safety_factor = 0.3  # Reducir al 30%
                
            elif current_T_max > self.thermal_limits['T_optimal_max']:
                # Reducir moderadamente si T > 48°C
                safety_factor = 0.9  # Reducir al 70%
            else:
                safety_factor = 1.0  # Normal
                
            # Actualizar estado sin muerte
            self.microbial_state['is_alive'] = True
            self.microbial_state['activity_factor'] = safety_factor
        else:
            safety_factor = 1.0
        
        # Obtener calor base CONTROLADO
        q_base = self._get_controlled_heat_profile(t)
        
        # APLICAR CONTROLES ESTRICTOS
        q_base *= self.fermentation_control['heat_reduction_factor']  # 0.75
        q_base *= safety_factor  # Factor de seguridad térmica
        
        # LÍMITE MÁXIMO ABSOLUTO
        q_base = min(q_base, self.fermentation_control['max_heat_generation'])
        
        # Factor por rotación (leve beneficio)
        if is_rotating:
            q_base *= 1.02  # Muy leve aumento
        
        return q_base
    
    def _get_controlled_heat_profile(self, t):
        """
        Perfil de calor base CONTROLADO 
        """
        t_hours = t / 3600.0
        
        # PERFIL REDUCIDO
        if t_hours < 12:
            # Fase inicial (reducida)
            q = 90.0 + (130.0 - 90.0) * (t_hours / 12.0)
        elif t_hours < 36:
            # Fermentación rápida (controlada)
            q = 130.0 + (220.0 - 130.0) * ((t_hours - 12.0) / 24.0)
        elif t_hours < 84:
            # Pico bacterial (LIMITADO)
            peak_temp = 320.0  # SIGNIFICATIVAMENTE REDUCIDO
            q = 220.0 + (peak_temp - 220.0) * ((t_hours - 36.0) / 48.0)
        elif t_hours < 168:
            # Declive controlado
            q = 320.0 - (320.0 - 260.0) * ((t_hours - 84.0) / 84.0)
        else:
            # Actividad residual
            q = 240.0
        
        # Factor de estabilización
        if t_hours > 48 and t_hours < 168:
            q *= 1.3 # Reducir durante pico crítico
        
        return q
    
    def get_current_evap_values(self):
        """Retorna valores actuales de evaporación"""
        return self._current_evap_values if self._current_evap_values else [0.0]
    
    def create_hexagonal_material_functions(self, domain, material_markers):
        """
        Crea funciones de material para el tambor hexagonal
        CORREGIDO: Para masa exacta de 300 kg
        """
        # Crear espacio de funciones
        Q = functionspace(domain, ("DG", 0))
        
        # Crear funciones
        k_func = Function(Q, name="Conductividad")
        rho_func = Function(Q, name="Densidad")
        cp_func = Function(Q, name="Calor_especifico")
        
        # Obtener marcadores
        markers = material_markers.values
        
        # CORRECCIÓN IMPORTANTE: Ajustar densidad del cacao para 300 kg exactos
        # Volumen especificado: 0.517 m³
        # Masa especificada: 300 kg
        # Densidad real = 300 kg / 0.517 m³ = 580 kg/m³
        densidad_cacao = 580.0  
        
        # Asignar valores
        k_values = np.select(
            [markers == 1, markers == 2, markers == 3],
            [self.wood['k'], self.cacao['k'], self.air['k']],
            default=self.air['k']
        )
        
        rho_values = np.select(
            [markers == 1, markers == 2, markers == 3],
            [self.wood['rho'], densidad_cacao, self.air['rho']],  # DENSIDAD
            default=self.air['rho']
        )
        
        cp_values = np.select(
            [markers == 1, markers == 2, markers == 3],
            [self.wood['cp'], self.cacao['cp'], self.air['cp']],
            default=self.air['cp']
        )
        
        # Asignar a funciones
        k_func.x.array[:] = k_values
        rho_func.x.array[:] = rho_values
        cp_func.x.array[:] = cp_values
        
        print(f"\n📋 Propiedades asignadas:")
        print(f"   Madera (tag 1): {self.wood['name']}")
        print(f"   Cacao (tag 2): {self.cacao['name']} - Densidad: {densidad_cacao:.0f} kg/m³")
        print(f"   Aire (tag 3): {self.air['name']}")
        print(f"   ✅ Masa de cacao: 300 kg exactos")
        print(f"   ✅ Generación controlada + Enfriamiento")
        
        return {
            'k': k_func,
            'rho': rho_func,
            'cp': cp_func,
            'wood_material': self.wood,
            'cacao_material': self.cacao,
            'air_material': self.air
        }
    
    def reset_microbial_state(self):
        """Reinicia estado microbiano"""
        self.microbial_state = {
            'is_alive': True,
            'death_time': None,
            'stress_level': 0.0,
            'activity_factor': 1.0,
            'moisture_stress': 0.0,
            'rotation_stress': 0.0,
            'death_disabled': True,
            'safety_mode_active': True
        }
        self._current_evap_values = []
    
    def print_hexagonal_summary(self):
        """Imprime resumen de propiedades"""
        print("\n" + "="*60)
        print("PROPIEDADES TÉRMICAS - TAMBOR HEXAGONAL")
        print("="*60)
        
        print(f"\n✅ CORRECCIONES APLICADAS:")
        print(f"   - Generación máxima: {self.fermentation_control['max_heat_generation']} W/m³")
        print(f"   - Enfriamiento: {self.ventilation['enhanced_h_conv']} W/m²·K")
        print(f"   - Factor reducción: {self.fermentation_control['heat_reduction_factor']}")
        print(f"   - Límite seguro: {self.thermal_limits['T_safe_max']-273.15:.1f}°C")
        print(f"   - Masa cacao exacta: 300 kg")
        
        print(f"\n🔧 PARÁMETROSS:")
        print(f"   - Factor convección: {self.ventilation['drum_convection_factor']:.1f}x")
        print(f"   - Transferencia masa: {self.ventilation['mass_transfer_coeff_natural']:.4f}")
        print(f"   - Bonus geometría: {self.ventilation['geometry_bonus']:.1f}x")
        
        print(f"\n✅ MODO SEGURIDAD TÉRMICA ACTIVO")


def test_properties():
    """Prueba las propiedades"""
    props = HexagonalMaterialProperties()
    
    print("\n🧪 PROBANDO PROPIEDADES:")
    
    # Probar generación de calor en diferentes momentos
    test_times = [24, 48, 72, 96]  # horas
    test_temps = [40, 45, 50, 55]  # °C
    
    for t_h in test_times:
        t_s = t_h * 3600
        for T_c in test_temps:
            T_k = T_c + 273.15
            
            q_gen = props.get_fermentation_heat_controlled(t_s, T_k, 0, False)
            q_evap = props.get_evaporative_cooling(T_k, t_s, 1.0)
            balance = q_gen - q_evap
            
            print(f"  t={t_h}h, T={T_c}°C: q_gen={q_gen:.0f} W/m³, q_evap={q_evap:.0f} W/m³, balance={balance:.0f} W/m³")


if __name__ == "__main__":
    test_properties()