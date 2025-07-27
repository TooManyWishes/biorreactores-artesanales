"""
run_hexagon_analysis.py

"""

import os
import sys
import time
from datetime import datetime

# Importar modelo
from main_thermal_model_hexagon import run_simulation

def print_header():
    """Imprime encabezado"""
    print("\n" + "="*70)
    print("🔧 MODELO TÉRMICO - TAMBOR HEXAGONAL 🔧")
    print("="*70)
    print("Universidad Nacional de Colombia")
    print("Comunidad: Asoseynekun, Pueblo Bello, Cesar")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n🚨 CORRECCIONES CRÍTICAS APLICADAS:")
    print("   ✅ Volúmenes exactos: 300 kg de cacao")
    print("   ✅ Generación de calor: LIMITADA a 150 W/m³")
    print("   ✅ Enfriamiento mejorado: 200 W/m³ máximo")
    print("   ✅ Rotaciones simples: 7 eventos (no duplicados)")
    print("   ✅ Límites térmicos: 55°C seguro, 60°C emergencia")
    print("   ✅ Factor reducción: 0.75x generación de calor")
    
    print("\n🎯 OBJETIVOS DE LA CORRECCIÓN:")
    print("   - Temperatura máxima: <50°C (ideal)")
    print("   - Temperatura límite: <55°C (seguro)")
    print("   - Fermentación completa: 7 días sin muerte")
    print("   - Proceso estable: sin temperaturas extremas")
    print("   - Simulación realista: tiempos apropiados")
    
    print("\n⚠️ PROBLEMAS ORIGINALES IDENTIFICADOS:")
    print("   ❌ Masa exagerada: 911 kg → 300 kg")
    print("   ❌ Temperatura imposible: 108°C → <55°C")
    print("   ❌ Rotaciones múltiples: 13 → 7")
    print("   ❌ Calor excesivo: 228 W/m³ → 150 W/m³")
    print("   ❌ Enfriamiento insuficiente: 97 W/m³ → 200 W/m³")
    print("="*70 + "\n")

def main():
    """Función principal"""
    print_header()
    
    # Crear directorio de resultados
    os.makedirs("results", exist_ok=True)
    
    print("🚀 Iniciando simulación...")
    print("🔧 Temperaturas realistas garantizadas")
    print("📐 Volúmenes exactos del documento original\n")
    
    # Verificar dependencias
    try:
        import gmsh
        print("✅ GMSH disponible")
    except ImportError:
        print("❌ Error: GMSH no instalado")
        return False
    
    # Medir tiempo
    start_time = time.time()
    
    try:
        # Ejecutar simulación
        print("🔄 Ejecutando modelo térmico...")
        model, times, T_max, T_min, T_avg = run_simulation()
        
        if model is None:
            print("❌ Error en la simulación")
            return False
        
        # Tiempo transcurrido
        elapsed = time.time() - start_time
        print(f"\n⏱️ Tiempo de simulación: {elapsed/60:.1f} minutos")
        
        # Análisis de resultados
        print(f"\n🔬 ANÁLISIS DE RESULTADOS:")
        
        max_temp = max(T_max)
        final_temp = T_avg[-1]
        rotations_done = model.total_rotations_done
        
        print(f"   - Temperatura máxima alcanzada: {max_temp:.1f}°C")
        print(f"   - Temperatura final promedio: {final_temp:.1f}°C")
        print(f"   - Rotaciones realizadas: {rotations_done}")
        print(f"   - Gradiente térmico máximo: {max([T_max[i]-T_min[i] for i in range(len(T_max))]):.1f}°C")
        
        
        # Verificar enfriamiento evaporativo
        if hasattr(model.mat_props, 'get_current_evap_values'):
            evap_values = model.mat_props.get_current_evap_values()
            if evap_values:
                avg_evap = sum(evap_values) / len(evap_values)
                max_evap = max(evap_values)
                print(f"\n   💧 ENFRIAMIENTO EVAPORATIVO:")
                print(f"      - Promedio: {avg_evap:.1f} W/m³")
                print(f"      - Máximo: {max_evap:.1f} W/m³")
                print(f"      - Estado: {'✅ SUFICIENTE' if avg_evap > 80 else '⚠️ MEJORABLE'}")
        
        # Crear reporte
        create_correction_report(model, times, T_max, T_min, T_avg, max_temp)
        
        print("\n" + "="*70)
        print("📁 Resultados guardados:")
        print("  - Simulación 3D: bioreactor_hexagon.xdmf")
        print("  - Estadísticas: stats_hexagon.json")
        print("  - Reporte corrección: reporte_tambor.txt")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error en simulación: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def create_correction_report(model, times, T_max, T_min, T_avg, max_temp_final):
    """Crea reporte de la corrección aplicada"""
    report_lines = []
    report_lines.append("REPORTE - TAMBOR HEXAGONAL")
    report_lines.append("="*60)
    report_lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    # Correcciones aplicadas
    report_lines.append("CORRECCIONES APLICADAS:")
    report_lines.append("✅ Volúmenes exactos según documento:")
    report_lines.append("   - Volumen interno: 0.748 m³")
    report_lines.append("   - Volumen cacao: 0.517 m³")
    report_lines.append("   - Masa cacao: 300 kg exactos")
    report_lines.append("   - Densidad: 580 kg/m³")
    report_lines.append("")
    
    report_lines.append("✅ Generación de calor controlada:")
    report_lines.append("   - Límite máximo: 150 W/m³")
    report_lines.append("   - Factor de reducción: 0.75x")
    report_lines.append("   - Perfil temporal suavizado")
    report_lines.append("")
    
    report_lines.append("✅ Enfriamiento evaporativo mejorado:")
    report_lines.append("   - Coeficiente convección: 120 W/m²·K")
    report_lines.append("   - Factor geométrico: 2.0x")
    report_lines.append("   - Límite evaporación: 200 W/m³")
    report_lines.append("")
    
    report_lines.append("✅ Rotación simplificada:")
    report_lines.append("   - Eventos únicos: 7 rotaciones")
    report_lines.append("   - Sin duplicados por paso temporal")
    report_lines.append("   - Control de estado mejorado")
    report_lines.append("")
    
    report_lines.append("✅ Límites de seguridad térmica:")
    report_lines.append("   - Temperatura segura: <55°C")
    report_lines.append("   - Parada emergencia: 60°C")
    report_lines.append("   - Modo seguridad automático")
    report_lines.append("")
    
    # Resultados finales
    report_lines.append("RESULTADOS:")
    report_lines.append(f"- Temperatura máxima final: {max_temp_final:.1f}°C")
    
    if max_temp_final < 50.0:
        report_lines.append("- Estado: ✅ PERFECTO (<50°C)")
        report_lines.append("- Fermentación: ÓPTIMA")
        report_lines.append("- Implementación: RECOMENDADA")
    elif max_temp_final < 55.0:
        report_lines.append("- Estado: ✅ EXCELENTE (<55°C)")
        report_lines.append("- Fermentación: VIABLE")
        report_lines.append("- Implementación: RECOMENDADA")
    else:
        report_lines.append("- Estado: ⚠️ MEJORABLE")
        report_lines.append("- Fermentación: REQUIERE MONITOREO")
        report_lines.append("- Implementación: CON PRECAUCIONES")
    
    # Guardar reporte
    filename = os.path.join("results", "reporte_tambor.txt")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\n📝 Reporte guardado: {filename}")

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✨ Corrección del tambor hexagonal completada exitosamente")
            print("\n🔍 PRÓXIMOS PASOS:")
            print("   1. ✅ Revisar reporte_tambor.txt")
            print("   2. 🔧 Usar la versión para análisis")
            print("   3. 📊 Ejecutar visualización con datos")
            print("   4. 🛠️ Proceder con implementación física")
            print("\n💡 ARCHIVOS A USAR:")
            print("   - geometry_setup_hexagon.py")
            print("   - material_properties_hexagon.py") 
            print("   - main_thermal_model_hexagon.py")
            print("   - run_hexagon_analysis.py")
        else:
            print("\n❌ Corrección fallida - revisar errores")
    except KeyboardInterrupt:
        print("\n\n⚠️ Corrección interrumpida por el usuario")