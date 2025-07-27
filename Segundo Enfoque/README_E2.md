# 🍫 Modelado Térmico de Biorreactores de Cacao

## 📋 Descripción del Proyecto

Este proyecto implementa un modelo computacional de transferencia de calor por conducción para optimizar biorreactores de fermentación de cacao en comunidades indígenas de Pueblo Bello, Cesar, Colombia. El modelo compara diferentes materiales y geometrías para minimizar pérdidas térmicas y mejorar la eficiencia del proceso fermentativo.


## 🎯 Objetivos

1. Simular el comportamiento térmico de la **caja de madera** tradicional.  
2. Simular el comportamiento térmico del **tambor hexagonal** rotatorio.  
3. Comparar desempeño térmico y viabilidad de cada diseño.


## 📁 Estructura del Proyecto

```
bioreactor-cacao/
├── geometry_setup_wood.py                # Geometría de la caja de madera
├── material_properties_wood.py           # Propiedades térmicas: madera & cacao
├── main_thermal_model_wood.py            # Modelo térmico con evaporación (caja)
├── run_evaporation_analysis_wood.py      # Ejecución y reporte (caja)
├── visualization_wood.py                 # Visualización 2D/3D (caja)
│
├── geometry_setup_hexagon_.py                 # Geometría del tambor hexagonal rotatorio
├── material_properties_hexagon_.py            # Propiedades térmicas & cacao
├── main_thermal_model_hexagon_.py             # Modelo térmico con evaporación (tambor)
├── run_evaporation_analysis_hexagon_.py       # Ejecución y reporte (tambor)
├── visualization_hexagon_.py                  # Visualización 2D/3D (tambor)
│
├── results/                              # Salidas: XDMF, JSON, PNG, GIF, TXT, H5
│
└── README_E1.md              # Este archivo
```


## 🚀 Inicio Rápido

```bash
# 1. Instalar dependencias
pip install mpi4py dolfinx ufl petsc4py numpy matplotlib pyvista

# 2. Ejecutar simulación de caja de madera
python run_evaporation_analysis_box.py

# 3. Ejecutar simulación de tambor hexagonal
python run_evaporation_analysis_hexagon_.py
```

## 🔧 Parámetros del Sistema

### Caja de madera
- Dimensiones externas: 85 × 90 × 74 cm  
- Espesor de paredes: 3 cm  
- Carga de cacao: 400 kg  
- Volumen interno ocupado por cacao: 97.6 %

### Tambor hexagonal rotatorio
- Longitud: 1.8 m  
- Diámetro (cara a cara): 0.86 m  
- Espesor de paredes: 3 cm  
- Carga de cacao: 300 kg  
- Volumen interno ocupado por cacao: ~70 %

### Propiedades de materiales:

| Material | k [W/m·K] | ρ [kg/m³] | Cp [J/kg·K] |
|----------|-----------|-----------|-------------|
| Madera   | 0.117     | 370       | 2300        |
| Cacao    | 0.279     | 910       | 920         |

## 💻 Requisitos

- Python 3.10+
- FEniCSx 0.9.0
- Librerías: numpy, matplotlib, mpi4py, petsc4py, ufl, pyvista
- ParaView (opcional, para visualización 3D)

## 🎨 Visualización 3D en ParaView

1. Abrir ParaView
2. File → Open → seleccionar `results/bioreactor_*.xdmf`
3. View → Animation View para crear animaciones

## 📈 Interpretación de Resultados

### Criterios de selección:
1. ✅ Eficiencia en retención de calor
2. ✅ Uniformidad térmica
3. ✅ Viabilidad económica
4. ✅ Facilidad de implementación
5. ✅ Disponibilidad local de materiales

## 👥 Equipo y Contexto

- **Universidad**: Universidad Nacional de Colombia
- **Programa**: Ingeniería Biológica
- **Asignatura**: Operaciones de Transferencia de Calor y Movimiento
- **Comunidad beneficiaria**: Asoseynekun, Pueblo Bello, Cesar

## 📝 Notas Adicionales

- El modelo resuelve **conducción térmica** dentro del material (mecanismo principal).
- **Convección externa** como condición de frontera (h = 10 W/m²·K).
- **Ventilación pasiva:** aire fluye por aberturas inferiores y laterales (caja) o ranuras del tambor.
- **Evaporación del contenido:** enfriamiento activo según humedad y área de superficie.
- **Generación de calor de fermentación** variable según cinética enzimática.
- Resultados validados con datos experimentales de fermentación de cacao.

## 🔮 Extensiones Futuras

- [ ] Modelar espacio de aire superior en la caja (actualmente implícito).
- [ ] Incorporar control de temperatura activo (resistencias o refrigeración).
- [ ] Optimización multiobjetivo: uniformidad térmica vs. retención de humedad.
- [ ] Análisis de sensibilidad paramétrica: propiedades térmicas y coeficientes de convección/evaporación.
- [ ] Evaluar efectos de velocidad de rotación y ángulo de tambor en la transferencia de calor.
- [ ] Comparar desempeño ante variaciones de carga y propiedades del grano.

---

**🌿 Promoviendo prácticas sostenibles y respetuosas con la cultura local.**


