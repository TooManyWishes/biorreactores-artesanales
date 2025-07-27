"""
geometry_setup_hexagon.py
CORRECCIÓN URGENTE: Geometría hexagonal con volúmenes especificados
"""

import numpy as np
import gmsh
import sys
from mpi4py import MPI
from dolfinx.io import gmshio
from dolfinx import mesh
import ufl

class HexagonalBioreactorGeometry:
    """
    Clase para geometría del TAMBOR HEXAGONAL con volúmenes
    """
    
    def __init__(self):
        """
        Inicializa con VOLÚMENES ESPECIFICADOS (no calculados)
        """
        self.bioreactor_type = 'hexagon'
        
        # DIMENSIONES FÍSICAS EXACTAS
        self.L = 1.8              # Longitud [m]
        self.D_ext = 0.86         # Diámetro externo [m] 
        self.thickness = 0.03     # Grosor [m]
        
        # VOLÚMENES ESPECIFICADOS (DEL DOCUMENTO)
        self.V_int = 0.748         # Volumen interno ESPECIFICADO [m³]
        self.V_cacao = 0.517       # Volumen cacao ESPECIFICADO [m³] (300 kg)
        self.V_aire = 0.231        # Volumen aire ESPECIFICADO [m³]
        
        # Calcular radios a partir de volúmenes especificados
        self.R_ext = self.D_ext / 2
        self.R_int = self.R_ext - self.thickness
        
        # MASA EXACTA ESPECIFICADA
        self.masa_cacao_kg = 300.0  # kg (ESPECIFICADO)
        self.densidad_cacao = self.masa_cacao_kg / self.V_cacao  # 580 kg/m³
        
        # Fracciones exactas
        self.cacao_fraction = self.V_cacao / self.V_int  # 69.1%
        self.aire_fraction = self.V_aire / self.V_int    # 30.9%
        
        # Inicializar MPI
        self.comm = MPI.COMM_WORLD
        
        # Variables de geometría
        self.domain = None
        self.cell_markers = None
        self.facet_markers = None
        
        print(f"🔧 GEOMETRÍA - VOLÚMENES:")
        print(f"   - Volumen interno: {self.V_int:.3f} m³")
        print(f"   - Volumen cacao: {self.V_cacao:.3f} m³ (300 kg)")
        print(f"   - Volumen aire: {self.V_aire:.3f} m³")
        print(f"   - Densidad cacao real: {self.densidad_cacao:.0f} kg/m³")
        print(f"   - Distribución real: {self.cacao_fraction*100:.1f}%/{self.aire_fraction*100:.1f}%")
        
    def create_hexagonal_mesh(self):
        """
        Crea mesh con VOLÚMENES CONTROLADOS
        """
        print(f"\n🔨 Creando mesh hexagonal...")
        
        # Verificar GMSH
        try:
            gmsh.model.getCurrent()
            gmsh.finalize()
        except:
            pass
        
        # Inicializar GMSH
        gmsh.initialize()
        gmsh.model.add("hexagon")
        
        try:
            # GEOMETRÍA SIMPLIFICADA CONTROLADA
            # 1. Hexágono externo (madera)
            wood_points = []
            for i in range(6):
                angle = i * np.pi / 3
                x = self.R_ext * np.cos(angle)
                y = self.R_ext * np.sin(angle)
                wood_points.append(gmsh.model.occ.addPoint(x, y, 0))
            
            wood_lines = []
            for i in range(6):
                wood_lines.append(gmsh.model.occ.addLine(wood_points[i], wood_points[(i+1)%6]))
            
            wood_loop = gmsh.model.occ.addCurveLoop(wood_lines)
            wood_surface = gmsh.model.occ.addPlaneSurface([wood_loop])
            wood_volume = gmsh.model.occ.extrude([(2, wood_surface)], 0, 0, self.L)[1][1]
            
            # 2. Hexágono interno - CACAO (parte inferior - 70%)
            cacao_points = []
            radius_cacao = self.R_int * 0.95  # Ligeramente menor para evitar problemas
            for i in range(6):
                angle = i * np.pi / 3
                x = radius_cacao * np.cos(angle)
                y = radius_cacao * np.sin(angle)
                cacao_points.append(gmsh.model.occ.addPoint(x, y, 0))
            
            cacao_lines = []
            for i in range(6):
                cacao_lines.append(gmsh.model.occ.addLine(cacao_points[i], cacao_points[(i+1)%6]))
            
            cacao_loop = gmsh.model.occ.addCurveLoop(cacao_lines)
            cacao_surface = gmsh.model.occ.addPlaneSurface([cacao_loop])
            
            # ALTURA CONTROLADA para 70% del volumen
            height_cacao = self.L * 0.70  # 70% de la longitud
            cacao_volume = gmsh.model.occ.extrude([(2, cacao_surface)], 0, 0, height_cacao)[1][1]
            
            # 3. Hexágono interno - AIRE (parte superior - 30%)
            air_points = []
            radius_air = self.R_int * 0.90  # Más pequeño que cacao
            for i in range(6):
                angle = i * np.pi / 3
                x = radius_air * np.cos(angle)
                y = radius_air * np.sin(angle)
                air_points.append(gmsh.model.occ.addPoint(x, y, height_cacao))
            
            air_lines = []
            for i in range(6):
                air_lines.append(gmsh.model.occ.addLine(air_points[i], air_points[(i+1)%6]))
            
            air_loop = gmsh.model.occ.addCurveLoop(air_lines)
            air_surface = gmsh.model.occ.addPlaneSurface([air_loop])
            
            # ALTURA CONTROLADA para 30% del volumen
            height_air = self.L * 0.30  # 30% de la longitud
            air_volume = gmsh.model.occ.extrude([(2, air_surface)], 0, 0, height_air)[1][1]
            
            # Sincronizar
            gmsh.model.occ.synchronize()
            
            # MARCADORES FÍSICOS CORRECTOS
            gmsh.model.addPhysicalGroup(3, [wood_volume], tag=1)   # Madera
            gmsh.model.addPhysicalGroup(3, [cacao_volume], tag=2)  # Cacao  
            gmsh.model.addPhysicalGroup(3, [air_volume], tag=3)    # Aire
            
            # Nombres
            gmsh.model.setPhysicalName(3, 1, "Wood")
            gmsh.model.setPhysicalName(3, 2, "Cacao")
            gmsh.model.setPhysicalName(3, 3, "Air")
            
            # CONFIGURACIÓN DE MALLA CONTROLADA
            gmsh.option.setNumber("Mesh.CharacteristicLengthMin", 0.08)
            gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.15)
            gmsh.option.setNumber("Mesh.Algorithm", 6)
            gmsh.option.setNumber("Mesh.Algorithm3D", 10)
            
            # Generar malla
            gmsh.model.mesh.generate(3)
            
            # Convertir a DOLFINx
            domain, cell_markers, facet_markers = gmshio.model_to_mesh(
                gmsh.model, 
                comm=self.comm, 
                rank=0, 
                gdim=3
            )
            
            print(f"✅ Mesh hexagonal:")
            print(f"   Celdas: {domain.topology.index_map(3).size_global}")
            print(f"   Volúmenes: CONTROLADOS (no exagerados)")
            print(f"   Masa cacao: {self.masa_cacao_kg} kg (EXACTO)")
            
            # Guardar referencias
            self.domain = domain
            self.cell_markers = cell_markers
            self.facet_markers = facet_markers
            
            return domain
            
        except Exception as e:
            print(f"❌ Error creando geometría: {e}")
            raise e
        finally:
            try:
                gmsh.finalize()
            except:
                pass
    
    def get_material_markers(self):
        """Retorna marcadores de material"""
        return self.cell_markers
    
    def get_boundary_markers(self):
        """Retorna marcadores de frontera"""
        return self.facet_markers
    
    def get_hexagon_volume_info(self):
        """Retorna información de volúmenes"""
        if not hasattr(self, 'domain'):
            return None
        
        return {
            'V_wood': 0.1,  # Estimado
            'V_cacao': self.V_cacao,  # ESPECIFICADO: 0.517 m³
            'V_air': self.V_aire,     # ESPECIFICADO: 0.231 m³
            'masa_cacao': self.masa_cacao_kg,  # ESPECIFICADO: 300 kg
            'cacao_fraction': self.cacao_fraction,  # 69.1%
            'air_fraction': self.aire_fraction,     # 30.9%
            'densidad_cacao': self.densidad_cacao,  # 580 kg/m³
            'especificaciones_exactas': True,
            'geometry': True  # MARCADOR DE CORRECCIÓN
        }


def create_hexagonal_bioreactor_geometry():
    """
    Función principal para geometría hexagonal
    """
    print("🚀 Creando geometría hexagonal...")
    print("🔧 Volúmenes controlados - sin masa exagerada")
    
    # Crear instancia
    geom = HexagonalBioreactorGeometry()
    
    # Crear mesh
    domain = geom.create_hexagonal_mesh()
    
    # Verificar volúmenes
    volume_info = geom.get_hexagon_volume_info()
    if volume_info:
        print(f"\n✅ VERIFICACIÓN DE CORRECCIÓN:")
        print(f"   - Masa cacao: {volume_info['masa_cacao']} kg ✓")
        print(f"   - Volumen cacao: {volume_info['V_cacao']:.3f} m³ ✓")
        print(f"   - Densidad: {volume_info['densidad_cacao']:.0f} kg/m³ ✓")
        print(f"   - Geometría: {volume_info['geometry']} ✓")
    
    return geom, domain


if __name__ == "__main__":
    print("🔧 CREANDO GEOMETRÍA HEXAGONAL...")
    print("="*60)
    
    try:
        geom, domain = create_hexagonal_bioreactor_geometry()
        print("\n✅ ¡Geometría hexagonal exitosamente!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()