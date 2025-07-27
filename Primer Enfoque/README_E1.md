# 🍫 Modelado Térmico de Biorreactores para Fermentación de Cacao

## 📋 Descripción del Proyecto

Este proyecto implementa un modelo computacional de transferencia de calor por conducción para optimizar biorreactores de fermentación de cacao en comunidades indígenas de Pueblo Bello, Cesar, Colombia. El modelo compara diferentes materiales y geometrías para minimizar pérdidas térmicas y mejorar la eficiencia del proceso fermentativo.

## 🎯 Objetivos

1. **Simular** el comportamiento térmico de cajones de madera tradicionales
2. **Comparar** distintas geometrías y materiales (madera, plástico, acero)
3. **Seleccionar** el diseño más adecuado considerando eficiencia térmica y viabilidad

## 📁 Estructura del Proyecto

``` 
bioreactor-cacao/
├── geometry_setup_<material>.py        # Configuración de geometría 3D para <material>
├── material_properties_<material>.py   # Propiedades térmicas de <material> y cacao
├── main_thermal_model_<material>.py    # Ensamble y solución del modelo térmico con evaporación
├── run_evaporation_analysis_<material>.py  # Script principal de ejecución y reporte
├── visualization_<material>.py         # Visualización 2D/3D y reportes
├── results/                            # Carpeta de resultados (XDMF, JSON, PNG, GIF)
└── README_E1.md              # Este archivo
```

## 🚀 Inicio Rápido

### 1. Verificar instalación
```bash
python test_quick_simulation_[].py
```

### 2. Ejecutar análisis completo
```bash
python run_complete_analysis_[].py
```

### 3. Opciones de análisis:
- **Opción 1**: Análisis individual (solo madera)
- **Opción 2**: Comparación completa (madera, plástico, acero)
- **Opción 3**: Análisis personalizado

## 📊 Resultados Generados

### Archivos de salida:
- `*.xdmf` - Datos 3D para visualización en ParaView
- `stats_*.json` - Estadísticas de temperatura por material
- `*.png` - Gráficos de evolución temporal y comparaciones
- `reporte_analisis_termico_[].txt` - Resumen completo

### Visualizaciones:
1. **Evolución temporal** de temperaturas (máx, mín, promedio)
2. **Comparación de materiales** con métricas de rendimiento
3. **Perfil de fermentación** (generación de calor vs tiempo)
4. **Gradientes térmicos** para evaluar uniformidad

## 🔧 Parámetros del Sistema

### Geometría del biorreactor:
- Dimensiones externas: 85×90×74 cm
- Espesor de paredes: 3 cm
- Capacidad: 400 kg de cacao
- Volumen interno: 97.6% ocupado por cacao

### Propiedades de materiales:

| Material | k [W/m·K] | ρ [kg/m³] | Cp [J/kg·K] |
|----------|-----------|-----------|-------------|
| Madera   | 0.117     | 370       | 2300        |
| Cacao    | 0.279     | 910       | 920         |
| Plástico | 0.22      | 910       | 2000        |
| Acero    | 16.0      | 8000      | 500         |

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

- El modelo considera conducción térmica dentro del material (mecanismo principal).
- Convección externa modelada como condición de frontera (h = 10 W/m²·K).
- Ventilación pasiva: flujo de aire a través de agujeros inferiores y laterales de la caja, afectando el intercambio de calor.
- Evaporación del contenido: enfriamiento evaporativo activo según la humedad y la superficie de contacto, calculado en cada paso de tiempo.
- Generación de calor variable según cinética de fermentación enzimática.
- Resultados propuestos a ser comparados con datos experimentales de fermentación de cacao.

## 🔮 Extensiones Futuras

- [ ] Modelar espacio de aire superior (1.7 cm)
- [ ] Agregar control de temperatura activo
- [ ] Optimización multiobjetivo (maximizar uniformidad térmica vs mínima pérdida de humedad)
- [ ] Análisis de sensibilidad paramétrica
- [ ] Comparar diferencias de desempeño entre variantes (_wood, _plastic, _steel) y diseñar recomendaciones de material.
- [ ] Integrar modelado de convección interna inducida por ventilación (más allá de la convección pasiva).

---

**🌿 Por un desarrollo sostenible y culturalmente apropiado 🌿**