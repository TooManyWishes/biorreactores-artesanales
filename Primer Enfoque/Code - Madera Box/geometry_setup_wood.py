"""
geometry_setup_box.py
Configuración de la geometría 3D del biorreactor de cacao
Proyecto: Modelado térmico de biorreactores para fermentación de cacao

"""

import numpy as np
from mpi4py import MPI
from dolfinx import mesh, fem, plot
from dolfinx.mesh import create_box, CellType, locate_entities_boundary, meshtags
from dolfinx.fem import functionspace, Function
import ufl

class BioreactorGeometry:
    """
    Clase para crear y gestionar la geometría del biorreactor
    """
    
    def __init__(self, bioreactor_type='box'):
        """
        Inicializa la geometría del biorreactor
        
        Parámetros:
        -----------
        bioreactor_type : str
            Tipo de biorreactor ('box' para caja)
        """
        self.bioreactor_type = bioreactor_type
        
        if bioreactor_type == 'box':
            self._setup_box_dimensions()
        else:
            raise ValueError("Tipo de biorreactor no válido. Use 'box'")
        
        # Inicializar MPI
        self.comm = MPI.COMM_WORLD
        
    def _setup_box_dimensions(self):
        """
        Configura las dimensiones para la caja biorreactor
        """
        print("📦 Configurando geometría de CAJA...")
        
        # Dimensiones externas de la caja (medidas actuales)
        self.L_ext = 0.85  # Largo externo (m)
        self.W_ext = 0.90  # Ancho externo (m)
        self.H_ext = 0.74  # Alto externo (m)
        
        # Espesor de las paredes (madera)
        self.thickness = 0.03  # 3 cm
        
        # Dimensiones internas calculadas
        self.L_int = self.L_ext - 2 * self.thickness
        self.W_int = self.W_ext - 2 * self.thickness
        self.H_int = self.H_ext - 2 * self.thickness
        
        # Altura del cacao dentro de la caja
        self.H_cacao = 0.663  # 66.3 cm (97.6% del volumen interno)
        
        # Resolución del mesh
        self.nx = 20
        self.ny = 22
        self.nz = 18
        
        # PARÁMETROS PARA
        self.ventilation = {
            'has_bottom_holes': True,
            'has_lateral_holes': True,      # Ventilación lateral
            'hole_diameter': 0.005,         # 5 mm
            'bottom_area_fraction': 0.50,   # 50% del área inferior
            'lateral_area_fraction': 0.25,  # 25% de cada lado lateral
            'num_holes_approx': None        # Se calculará
        }
        
        self._calculate_ventilation_parameters()
        
        
    def _calculate_ventilation_parameters(self):
        """
        Calcula los parámetros de para la caja
        """
        if self.bioreactor_type == 'box':
            # Áreas de las superficies
            bottom_area = self.L_int * self.W_int
            left_area = self.W_int * self.H_int  
            right_area = self.W_int * self.H_int
            
            # Áreas de ventilación
            bottom_vent_area = bottom_area * self.ventilation['bottom_area_fraction']
            lateral_vent_area_each = left_area * self.ventilation['lateral_area_fraction']
            total_vent_area = bottom_vent_area + 2 * lateral_vent_area_each
            
            # Área de un agujero
            hole_area = np.pi * (self.ventilation['hole_diameter'] / 2)**2
            
            # Número aproximado de agujeros
            bottom_holes = int(bottom_vent_area / hole_area)
            lateral_holes_each = int(lateral_vent_area_each / hole_area)
            total_holes = bottom_holes + 2 * lateral_holes_each
            
            # Actualizar parámetros
            self.ventilation['num_holes_approx'] = total_holes
            self.ventilation['bottom_holes'] = bottom_holes
            self.ventilation['lateral_holes_each'] = lateral_holes_each
            
            print(f"🕳️ Parámetros de calculados:")
            print(f"   SUPERFICIES DE VENTILACIÓN:")
            print(f"   - Área inferior total: {bottom_area:.4f} m²")
            print(f"   - Área inferior ventilada: {bottom_vent_area:.6f} m² ({self.ventilation['bottom_area_fraction']*100:.0f}%)")
            print(f"   - Agujeros en inferior: ~{bottom_holes}")
            print(f"   ")
            print(f"   - Área lateral total (c/lado): {left_area:.4f} m²")
            print(f"   - Área lateral ventilada (c/lado): {lateral_vent_area_each:.6f} m² ({self.ventilation['lateral_area_fraction']*100:.0f}%)")
            print(f"   - Agujeros en cada lateral: ~{lateral_holes_each}")
            print(f"   ")
            print(f"   TOTALES:")
            print(f"   - Área total ventilada: {total_vent_area:.6f} m²")
            print(f"   - Número total de agujeros: ~{total_holes}")
            print(f"   - Superficies con ventilación: 3 (inferior + 2 laterales)")
    
    def create_full_mesh(self):
        """
        Crea el mesh 3D completo del biorreactor
        """
        print(f"🔨 Creando geometría del biorreactor tipo '{self.bioreactor_type}'...")
        
        if self.bioreactor_type == 'box':
            return self._create_box_mesh()
    
    def _create_box_mesh(self):
        """
        Crea el mesh para la caja biorreactor
        """
        # Crear mesh de la caja completa
        self.domain = create_box(
            self.comm,
            [np.array([0.0, 0.0, 0.0]), 
             np.array([self.L_ext, self.W_ext, self.H_ext])],
            [self.nx, self.ny, self.nz],
            cell_type=CellType.hexahedron
        )
        
        print(f"✅ Mesh de caja creado con {self.domain.topology.index_map(3).size_global} celdas")
        
        # Crear marcadores de materiales
        self.create_material_markers()
        
        return self.domain
    
    
    def create_material_markers(self):
        """
        Crea marcadores para distinguir entre madera (paredes) y cacao (interior)

        """
        print("🏷️ Marcando regiones de materiales (madera + cacao)...")
        
        # Dimensión del mesh
        tdim = self.domain.topology.dim
        
        # Crear espacio de funciones DG0 para los marcadores
        Q = functionspace(self.domain, ("DG", 0))
        self.material_markers = Function(Q)
        
        # Obtener coordenadas de centros de celdas
        num_cells = self.domain.topology.index_map(tdim).size_local
        midpoints = mesh.compute_midpoints(self.domain, tdim, np.arange(num_cells, dtype=np.int32))
        
        # Marcar celdas: 1 = madera, 2 = cacao
        markers = np.zeros(num_cells, dtype=np.int32)
        
        for i, point in enumerate(midpoints):
            x, y, z = point
            
            # Verificar si está en el interior (cacao)
            if (self.thickness < x < self.L_ext - self.thickness and
                self.thickness < y < self.W_ext - self.thickness and
                self.thickness < z < self.H_cacao + self.thickness):
                markers[i] = 2  # Cacao
            else:
                markers[i] = 1  # Madera
        
        # Asignar marcadores
        self.material_markers.x.array[:] = markers.astype(np.float64)
        
        # Contar regiones
        cacao_cells = np.sum(markers == 2)
        wood_cells = np.sum(markers == 1)
        
        print(f"✅ Regiones marcadas:")
        print(f"   - Celdas de madera: {wood_cells}")
        print(f"   - Celdas de cacao: {cacao_cells}")
        
    def mark_boundaries(self):
        """
        Marca las fronteras del dominio para condiciones de frontera
        : Implementación de (inferior + laterales)
        """
        print("🎯 Marcando fronteras (con)...")
        
        fdim = self.domain.topology.dim - 1
        
        # Localizar entidades de frontera
        def left_boundary(x):
            return np.isclose(x[0], 0.0)
        
        def right_boundary(x):
            return np.isclose(x[0], self.L_ext)
        
        def front_boundary(x):
            return np.isclose(x[1], 0.0)
        
        def back_boundary(x):
            return np.isclose(x[1], self.W_ext)
        
        def bottom_boundary(x):
            return np.isclose(x[2], 0.0)
        
        def top_boundary(x):
            return np.isclose(x[2], self.H_ext)
        
        # Recopilar todas las facetas e índices
        facet_indices = []
        facet_markers = []
        
        # PASO 1: Marcar fronteras normales (sin ventilación)
        boundaries_normal = [
            (3, front_boundary),    # Frente - sin ventilación
            (4, back_boundary),     # Atrás - sin ventilación  
            (6, top_boundary)       # Superior - sin ventilación
        ]
        
        for (marker, boundary_func) in boundaries_normal:
            facets = locate_entities_boundary(self.domain, fdim, boundary_func)
            facet_indices.extend(facets)
            facet_markers.extend([marker] * len(facets))
        
        # PASO 2: Procesar inferior con ventilación parcial
        bottom_facets = locate_entities_boundary(self.domain, fdim, bottom_boundary)
        if len(bottom_facets) > 0:
            num_bottom_ventilated = max(1, int(len(bottom_facets) * self.ventilation['bottom_area_fraction']))
            
            # Dividir facetas del fondo
            bottom_ventilated = bottom_facets[:num_bottom_ventilated]  # 50% ventiladas
            bottom_normal = bottom_facets[num_bottom_ventilated:]      # 50% normales
            
            # Agregar a las listas
            facet_indices.extend(bottom_normal)
            facet_markers.extend([5] * len(bottom_normal))  # Marcador 5: inferior normal
            
            facet_indices.extend(bottom_ventilated)  
            facet_markers.extend([7] * len(bottom_ventilated))  # Marcador 7: inferior ventilado
        
        # PASO 3: Procesar izquierda con ventilación parcial
        left_facets = locate_entities_boundary(self.domain, fdim, left_boundary)
        if len(left_facets) > 0:
            num_left_ventilated = max(1, int(len(left_facets) * self.ventilation['lateral_area_fraction']))
            
            # Dividir facetas izquierdas
            left_ventilated = left_facets[:num_left_ventilated]  # 25% ventiladas
            left_normal = left_facets[num_left_ventilated:]      # 75% normales
            
            # Agregar a las listas
            facet_indices.extend(left_normal)
            facet_markers.extend([1] * len(left_normal))  # Marcador 1: izquierda normal
            
            facet_indices.extend(left_ventilated)
            facet_markers.extend([8] * len(left_ventilated))  # Marcador 8: izquierda ventilada
        
        # PASO 4: Procesar derecha con ventilación parcial
        right_facets = locate_entities_boundary(self.domain, fdim, right_boundary)
        if len(right_facets) > 0:
            num_right_ventilated = max(1, int(len(right_facets) * self.ventilation['lateral_area_fraction']))
            
            # Dividir facetas derechas
            right_ventilated = right_facets[:num_right_ventilated]  # 25% ventiladas
            right_normal = right_facets[num_right_ventilated:]      # 75% normales
            
            # Agregar a las listas
            facet_indices.extend(right_normal)
            facet_markers.extend([2] * len(right_normal))  # Marcador 2: derecha normal
            
            facet_indices.extend(right_ventilated)
            facet_markers.extend([9] * len(right_ventilated))  # Marcador 9: derecha ventilada
        
        # Ordenar facetas por índice (requerido por FEniCSx)
        facet_indices = np.array(facet_indices, dtype=np.int32)
        facet_markers = np.array(facet_markers, dtype=np.int32) 
        
        sorted_facets = np.argsort(facet_indices)
        
        # Crear MeshTags con los índices ordenados
        self.boundary_markers = meshtags(
            self.domain, 
            fdim, 
            facet_indices[sorted_facets], 
            facet_markers[sorted_facets]
        )
        
        print("✅ Fronteras marcadas con:")
        print("   SUPERFICIES NORMALES:")
        print("   1: Izquierda normal, 2: Derecha normal")
        print("   3: Frente, 4: Atrás") 
        print("   5: Inferior normal, 6: Superior")
        print("   SUPERFICIES VENTILADAS:")
        print("   7: Inferior ventilado (50%)")
        print("   8: Izquierda ventilada (25%)")  
        print("   9: Derecha ventilada (25%)")
        
        # Verificar marcadores
        unique_markers = np.unique(facet_markers)
        for marker in unique_markers:
            count = np.sum(facet_markers == marker)
            marker_names = {
                1: "Izquierda normal", 2: "Derecha normal", 3: "Frente", 4: "Atrás",
                5: "Inferior normal", 6: "Superior", 
                7: "Inferior VENTILADO", 8: "Izquierda VENTILADA", 9: "Derecha VENTILADA"
            }
            name = marker_names.get(marker, f"Desconocido({marker})")
            print(f"   Marcador {marker} ({name}): {count} facetas")
        
    def get_volume_info(self):
        """
        Calcula y muestra información sobre los volúmenes
        """
        print(f"\\n📊 Información de volúmenes ({self.bioreactor_type}):")
        
        if self.bioreactor_type == 'box':
            # Volúmenes para caja
            V_ext = self.L_ext * self.W_ext * self.H_ext
            V_int = self.L_int * self.W_int * self.H_int
            V_cacao = self.L_int * self.W_int * self.H_cacao
            V_madera = V_ext - V_int
            
            print(f"   Volumen externo total: {V_ext:.4f} m³")
            print(f"   Volumen interno total: {V_int:.4f} m³")
            print(f"   Volumen de cacao: {V_cacao:.4f} m³")
            print(f"   Volumen de madera: {V_madera:.4f} m³")
            
            # Masa de cacao
            rho_cacao = 910  # kg/m³
            masa_cacao = V_cacao * rho_cacao
            print(f"   Masa de cacao calculada: {masa_cacao:.1f} kg")
            print(f"   (Objetivo: 400 kg)")
            
            return {
                'V_ext': V_ext,
                'V_int': V_int,
                'V_cacao': V_cacao,
                'V_madera': V_madera,
                'masa_cacao': masa_cacao
            }
        
        else:  # hexagon (futuro)
            print("   Cálculo de volúmenes hexagonales pendiente")
            return {}


def create_bioreactor_geometry(bioreactor_type='box'):
    """
    Función principal para crear la geometría del biorreactor
    
    Parámetros:
    'box'
    """
    # Crear instancia de la geometría
    geom = BioreactorGeometry(bioreactor_type)
    
    # Crear el mesh
    domain = geom.create_full_mesh()
    
    # Marcar las fronteras
    geom.mark_boundaries()
    
    # Mostrar información de volúmenes
    geom.get_volume_info()
    
    return geom, domain


# Para pruebas directas del módulo
if __name__ == "__main__":
    print("🚀 Creando geometría del biorreactor -...")
    print("=" * 60)
    
    # Probar geometría de caja
    geom, domain = create_bioreactor_geometry('box')
    
    print("\\n✅ ¡Geometría de caja creada exitosamente!")
    print(f"   Total de nodos: {domain.geometry.x.shape[0]}")
    print(f"   Dimensiones: {domain.geometry.dim}D")