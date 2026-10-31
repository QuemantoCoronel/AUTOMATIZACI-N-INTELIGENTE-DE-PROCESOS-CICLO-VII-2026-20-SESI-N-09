"""
Interfaz de Chat Interactivo en Terminal (CLI)
Funeraria Velazquex - Sistema Multi-Agente de Cotizaciones Digitales
Permite al usuario interactuar en tiempo real simulando ser un cliente deudo.
"""

import sys
from datetime import datetime

# Configuración de codificación para consola Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from funeraria_velazquex import OrquestadorFlujo, EstadoProceso


def imprimir_encabezado():
    print("\n" + "=" * 80)
    print("  🕊️  FUNERARIA VELAZQUEX · CHAT INTERACTIVO MULTI-AGENTE (CLI)")
    print("  Simulador de Atención al Cliente y Cotización Digital (BPMN TO-BE)")
    print("=" * 80)
    print("Comandos disponibles:")
    print("  • Escribe tu mensaje libremente como si fueras un deudo o familiar.")
    print("  • '/reiniciar' : Iniciar una nueva solicitud desde cero.")
    print("  • '/estado'    : Ver el estado de la solicitud y trazas completas.")
    print("  • '/salir'     : Finalizar la sesión de chat.")
    print("-" * 80 + "\n")


def main():
    imprimir_encabezado()
    orquestador = OrquestadorFlujo()
    sesion_id = f"cli_{datetime.now().strftime('%H%M%S')}"

    print("🤖 Front-End (Atención al Cliente):")
    print("   'Buenos días/tardes. Bienvenido a Funeraria Velazquex. ¿En qué podemos acompañarle hoy?'\n")

    while True:
        try:
            mensaje_usuario = input("👤 Tú (Cliente) > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nSesión finalizada. Hasta pronto.")
            break

        if not mensaje_usuario:
            continue

        if mensaje_usuario.lower() in ["/salir", "salir", "exit", "quit"]:
            print("\n🕊️ Gracias por comunicarse con Funeraria Velazquex. Sesión cerrada.\n")
            break

        if mensaje_usuario.lower() in ["/reiniciar", "reiniciar", "reset"]:
            orquestador.reiniciar_sesion(sesion_id)
            print("\n🔄 [Sesión reiniciada. Se ha creado una nueva solicitud en blanco.]\n")
            print("🤖 Front-End (Atención al Cliente):")
            print("   'Bienvenido nuevamente a Funeraria Velazquex. ¿Qué servicio funerario desea consultar?'\n")
            continue

        if mensaje_usuario.lower() in ["/estado", "estado"]:
            sesion = orquestador._sesiones.get(sesion_id, {})
            sol = sesion.get("solicitud")
            cot = sesion.get("cotizacion")
            print("\n" + "-" * 60)
            print("📋 [ESTADO ACTUAL DE LA SESIÓN]")
            if sol:
                print(f"  • ID Solicitud: {sol.id_solicitud}")
                print(f"  • Nombre Cliente: {sol.nombre_cliente or '(Pendiente)'}")
                print(f"  • Teléfono: {sol.telefono or '(Pendiente)'}")
                print(f"  • Servicio: {sol.servicio_solicitado or '(Pendiente)'}")
                print(f"  • Fecha Servicio: {sol.fecha_servicio or '(Pendiente)'}")
            if cot:
                print(f"  • Cotización: {cot.codigo_cotizacion} (Total: S/ {cot.total_pen:,.2f})")
            print("-" * 60 + "\n")
            continue

        # Procesar turno a través del Orquestador
        resultado = orquestador.procesar_mensaje_conversacional(
            mensaje_texto=mensaje_usuario,
            sesion_id=sesion_id,
        )

        # Mostrar respuesta del Agente Front-End
        print("\n" + "─" * 80)
        print("🤖 Front-End (Atención al Cliente):")
        print(resultado["mensaje_asistente"])
        print("─" * 80)

        # Mostrar trazas del Agente Back-End y BPMN ejecutadas en segundo plano
        trazas = resultado.get("trazas_recientes", [])
        if trazas:
            print("\n⚙️  [ACCIONES DEL BACK-END EN SEGUNDO PLANO / BPMN TO-BE]:")
            for t in trazas:
                print(f"   {t}")
            print()


if __name__ == "__main__":
    main()
