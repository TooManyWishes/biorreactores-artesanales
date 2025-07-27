"""
run_evaporation_analysis_box.py
Script principal para ejecutar simulación

"""

import os
import sys
import time
from datetime import datetime

# Importar el modelo
from main_thermal_model_box import run_evaporation_simulation
from visualization_box import BioreactorVisualizer

def print_header():
    """Imprime el encabezado del proyecto"""
    print("\n" + "="*70)
    print("🍫 MODELADO TÉRMICO - ENFRIAMIENTO EVAPORATIVO PASIVO 🍫")
    print("="*70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

def main():
    """Función principal"""
    print_header()
    
    # Crear directorio de resultados
    os.makedirs("results", exist_ok=True)
    
    print("🚀 Iniciando simulación...")
    print("💧 Aprovechando la humedad natural del cacao\n")
    
    # Medir tiempo
    start_time = time.time()
    
    try:
        # Ejecutar simulación
        model, times, T_max, T_min, T_avg = run_evaporation_simulation('box')
        
        if model is None:
            print("❌ Error en la simulación")
            return False
        
        # Tiempo transcurrido
        elapsed = time.time() - start_time
        print(f"\n⏱️ Tiempo de simulación: {elapsed/60:.1f} minutos")
        
        # Análisis de resultados
        print(f"\n🔬 ANÁLISIS DE RESULTADOS:")
        
        max_temp = max(T_max)
        print(f"   - Temperatura máxima: {max_temp:.1f}°C")
        
        if not model.thermal_death_occurred:
            print(f"   🎉 ¡ÉXITO TOTAL!")
            print(f"   ✅ Los microorganismos sobrevivieron")
            print(f"   ✅ La evaporación pasiva fue suficiente")
            print(f"\n   💡 RECOMENDACIONES PARA SU USO:")
            print(f"      1. Mantener la humedad inicial del cacao (~40%)")
            print(f"      2. No cubrir herméticamente durante fermentación")
            print(f"      3. Permitir flujo de aire natural por los agujeros")
            print(f"      4. En días muy secos, rociar ligeramente con agua")
            
        else:
            print(f"   ⚠️ Muerte microbiana a las {model.death_time/3600:.1f}h")
            if model.death_time/3600 > 80:
                print(f"   ✅ MEJORA SIGNIFICATIVA")
                print(f"   📈 Extensión de vida: +{model.death_time/3600-53:.1f}h")
            else:
                print(f"   🔧 Necesita optimización adicional")
        
        # Crear reporte detallado
        create_evaporation_report(model, times, T_max, T_min, T_avg)
        
        print("\n" + "="*70)
        print("📁 Resultados guardados en la carpeta 'results/':")
        print("  - Datos 3D: bioreactor_box_evaporation_box.xdmf")
        print("  - Estadísticas: stats_box_evaporation_box.json")
        print("  - Reporte: reporte_evaporacion_box.txt")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def create_evaporation_report(model, times, T_max, T_min, T_avg):
    """Crea un reporte detallado de la evaporación"""
    
    # Cargar estadísticas
    import json
    stats_file = os.path.join(model.results_dir, f"stats_{model.bioreactor_type}_evaporation_box.json")
    with open(stats_file, 'r') as f:
        stats = json.load(f)
    
    report_lines = []
    report_lines.append("REPORTE DE SIMULACIÓN - ENFRIAMIENTO EVAPORATIVO")
    report_lines.append("="*60)
    report_lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    # Configuración
    report_lines.append("CONFIGURACIÓN:")
    report_lines.append("- Tipo: Caja de madera 85×90×74 cm")
    report_lines.append("- Capacidad: 400 kg de cacao")
    report_lines.append("- Ventilación: 50% inferior + 25% laterales")
    report_lines.append("- EVAPORACIÓN: Pasiva (convección natural)")
    report_lines.append("")
    
    # Resultados térmicos
    report_lines.append("RESULTADOS TÉRMICOS:")
    report_lines.append(f"- Temperatura máxima: {max(T_max):.1f}°C")
    report_lines.append(f"- Temperatura promedio final: {T_avg[-1]:.1f}°C")
    report_lines.append(f"- Gradiente máximo: {max([T_max[i]-T_min[i] for i in range(len(T_max))]):.1f}°C")
    report_lines.append("")
    
    # Evaporación
    report_lines.append("ENFRIAMIENTO EVAPORATIVO:")
    if 'evaporative_cooling_W_m3' in stats:
        max_evap = max(stats['evaporative_cooling_W_m3'])
        avg_evap = sum(stats['evaporative_cooling_W_m3'])/len(stats['evaporative_cooling_W_m3'])
        report_lines.append(f"- Enfriamiento máximo: {max_evap:.0f} W/m³")
        report_lines.append(f"- Enfriamiento promedio: {avg_evap:.0f} W/m³")
    
    if 'final_moisture_loss_percent' in stats:
        report_lines.append(f"- Pérdida de humedad: {stats['final_moisture_loss_percent']:.1f}%")
    report_lines.append("")
    
    # Estado microbiano
    report_lines.append("ESTADO MICROBIANO:")
    if model.thermal_death_occurred:
        report_lines.append(f"- Estado: MUERTE DETECTADA")
        report_lines.append(f"- Tiempo: {model.death_time/3600:.1f} horas")
    else:
        report_lines.append("- Estado: MICROORGANISMOS VIABLES ✅")
        report_lines.append("- Fermentación: COMPLETA")
    report_lines.append("")
    
    # Conclusiones
    report_lines.append("CONCLUSIONES:")
    if not model.thermal_death_occurred:
        report_lines.append("✅ La evaporación pasiva es SUFICIENTE")
        report_lines.append("✅ Solución viable para la comunidad")
    else:
        report_lines.append("⚠️ Se requiere optimización adicional")
    
    # Guardar reporte
    filename = os.path.join(model.results_dir, "reporte_evaporacion_box.txt")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\n📝 Reporte guardado en: {filename}")

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✨ Análisis completado exitosamente")
    except KeyboardInterrupt:
        print("\n\n⚠️ Análisis interrumpido por el usuario")
    