"""
Workflow de LangGraph y Monitoreo LangSmith para Funeraria Velazquex
Alineado con el Diagrama BPMN TO-BE y las 4 Capas del Ecosistema LangChain
UPAO - Automatización Inteligente de Procesos (Sesión 09)
"""

import os
import sys
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, TypedDict

# Configuración de codificación UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from pydantic import BaseModel, Field

# Importaciones de LangChain y LangGraph
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith.run_trees import RunTree

# Importaciones del proyecto existente
from funeraria_velazquex.excel_service import ExcelService
from funeraria_velazquex.models import (
    SolicitudEntrada,
    Cotizacion,
    DisponibilidadResultado,
    ValidacionResultado,
    ItemCotizacion,
    TipoCliente,
)
from funeraria_velazquex.config import TASA_IGV, PLANTILLAS_EMPATIA


# =============================================================================
# 1. CAPA 1: LANGCHAIN CORE & LCEL (Contratos Pydantic y Herramientas @tool)
# =============================================================================

excel_service = ExcelService()

@tool
def tool_consultar_catalogo(servicio_solicitado: str) -> Dict[str, Any]:
    """Consulta en Excel el precio base y categoría del servicio funerario."""
    encontrado, item, msg = excel_service.consultar_catalogo(servicio_solicitado)
    if encontrado and item:
        return item.model_dump()
    return {"error": msg, "servicio_solicitado": servicio_solicitado}

@tool
def tool_verificar_disponibilidad(servicio_dict: Dict[str, Any], fecha_servicio: str) -> Dict[str, Any]:
    """Verifica en Excel la disponibilidad de cupos en capillas/hornos para la fecha indicada."""
    from funeraria_velazquex.models import ServicioCatalogo
    item = ServicioCatalogo(**servicio_dict)
    disp = excel_service.verificar_disponibilidad(item, fecha_servicio)
    return disp.model_dump()

@tool
def tool_calcular_cotizacion(precio_base: float, es_alternativa: bool = False, motivo: str = "") -> Dict[str, float]:
    """Calcula Subtotal, IGV (18%) y Total en Soles (PEN) según normativa fiscal peruana."""
    subtotal = round(precio_base, 2)
    igv = round(subtotal * TASA_IGV, 2)
    total = round(subtotal + igv, 2)
    return {"subtotal_pen": subtotal, "igv_pen": igv, "total_pen": total}


# =============================================================================
# 2. CAPA 2: LANGGRAPH - ESTADO TIPADO DEL PROCESO
# =============================================================================

class EstadoCotizacion(TypedDict):
    """
    Estado compartido (Pizarrón del grafo) que fluye entre nodos.
    """
    id_caso: str
    datos_solicitud: Dict[str, Any]
    es_valida: bool
    campos_faltantes: List[str]
    servicio_catalogo: Optional[Dict[str, Any]]
    disponibilidad: Optional[Dict[str, Any]]
    alternativa_aplicada: bool
    subtotal_pen: float
    igv_pen: float
    total_pen: float
    codigo_cotizacion: str
    requiere_hitl: bool
    autorizacion_supervisor: Optional[str]
    motivo_pausa_hitl: str
    mensaje_salida_cliente: str
    historial_pasos: List[str]


# =============================================================================
# 3. NODOS DEL GRAFO (Funciones puras que mutan el estado vía merge)
# =============================================================================

def nodo_recibir_solicitud(estado: EstadoCotizacion) -> Dict[str, Any]:
    """F_Start: Recepción y normalización del mensaje del deudo/cliente."""
    sol = estado["datos_solicitud"]
    pasos = estado.get("historial_pasos", []) + ["[F_Start] Solicitud recibida del cliente."]
    return {
        "historial_pasos": pasos,
        "id_caso": sol.get("id_solicitud", f"SOL-{uuid.uuid4().hex[:6].upper()}"),
    }

def nodo_validar_contrato(estado: EstadoCotizacion) -> Dict[str, Any]:
    """F_Validar / F_GW_Datos: Validación del contrato de entrada mediante Pydantic."""
    sol = estado["datos_solicitud"]
    faltantes = []
    if not sol.get("nombre_cliente") or len(str(sol.get("nombre_cliente")).strip()) < 3:
        faltantes.append("Nombre del contacto (mínimo 3 caracteres)")
    tel = str(sol.get("telefono", "")).strip()
    if not tel or not tel.isdigit() or len(tel) < 9:
        faltantes.append("Teléfono celular válido (9 dígitos numéricos)")
    if not sol.get("servicio_solicitado"):
        faltantes.append("Servicio funerario requerido (Sepelio / Cremación / etc.)")
    if not sol.get("fecha_servicio"):
        faltantes.append("Fecha del servicio (formato YYYY-MM-DD)")

    es_valida = (len(faltantes) == 0)
    pasos = estado.get("historial_pasos", []) + [
        f"[F_Validar] Validación de contrato: {'APROBADO' if es_valida else 'CAMPOS FALTANTES'}"
    ]
    return {
        "es_valida": es_valida,
        "campos_faltantes": faltantes,
        "historial_pasos": pasos,
    }

def nodo_solicitar_datos(estado: EstadoCotizacion) -> Dict[str, Any]:
    """F_SolicitarDatos: Generación de mensaje empático solicitando datos faltantes."""
    nom = estado["datos_solicitud"].get("nombre_cliente", "deudo")
    lista_fmt = "\n".join([f"  • {c}" for c in estado["campos_faltantes"]])
    mensaje = (
        f"Estimada familia {nom}, en Funeraria Velazquex le extendemos nuestras sinceras condolencias.\n"
        f"Para orientarle y cotizar adecuadamente, con el debido respeto le solicitamos completar:\n"
        f"{lista_fmt}\n"
        f"Quedamos a su entera disposición."
    )
    pasos = estado.get("historial_pasos", []) + ["[F_SolicitarDatos] Mensaje empático emitido."]
    return {
        "mensaje_salida_cliente": mensaje,
        "historial_pasos": pasos,
    }

def nodo_consultar_catalogo(estado: EstadoCotizacion) -> Dict[str, Any]:
    """F_ConsultarCatalogo & F_VerificarDisponibilidad: Consulta de tablas Excel."""
    sol = estado["datos_solicitud"]
    serv_nombre = sol.get("servicio_solicitado", "")
    fec = sol.get("fecha_servicio", "")

    cat_res = tool_consultar_catalogo.invoke({"servicio_solicitado": serv_nombre})
    disp_res = tool_verificar_disponibilidad.invoke({
        "servicio_dict": cat_res,
        "fecha_servicio": fec,
    })

    pasos = estado.get("historial_pasos", []) + [
        f"[F_ConsultarCatalogo] Catálogo verificado: {cat_res.get('nombre_servicio', serv_nombre)} (S/ {cat_res.get('precio_base_pen', 0):,.2f})",
        f"[F_VerificarDisponibilidad] Disponibilidad en fecha {fec}: {'DISPONIBLE' if disp_res.get('disponible') else 'COLMADO'}",
    ]
    return {
        "servicio_catalogo": cat_res,
        "disponibilidad": disp_res,
        "historial_pasos": pasos,
    }

def nodo_definir_alternativa(estado: EstadoCotizacion) -> Dict[str, Any]:
    """F_DefinirAlternativa: Asigna alternativa comercial si no hay cupo en la fecha."""
    disp = estado["disponibilidad"] or {}
    alt = disp.get("servicio_alternativo") or {}
    pasos = estado.get("historial_pasos", []) + [
        f"[F_DefinirAlternativa] Alternativa aplicada: {alt.get('nombre_servicio', 'Sepelio Integral Dignidad')}"
    ]
    return {
        "alternativa_aplicada": True,
        "servicio_catalogo": alt if alt else estado["servicio_catalogo"],
        "historial_pasos": pasos,
    }

def nodo_calcular_cotizacion(estado: EstadoCotizacion) -> Dict[str, Any]:
    """F_GenerarCotizacion: Cálculo exacto de Subtotal, IGV (18%) y Total."""
    cat = estado["servicio_catalogo"] or {}
    precio_base = float(cat.get("precio_base_pen", 3200.0))
    calc = tool_calcular_cotizacion.invoke({"precio_base": precio_base})

    # Criterio HITL por Irreversibilidad (Sesión 9, Diapositiva 15):
    # Si el importe supera S/ 3,500 o se aplicó alternativa comercial,
    # se exige validación del Supervisor humano antes de confirmar la reserva.
    requiere_hitl = (calc["total_pen"] >= 3500.0) or estado.get("alternativa_aplicada", False)
    motivo = "Monto mayor a S/ 3,500 y/o reasignación de capacidad alternativa" if requiere_hitl else "Flujo estándar"

    cod_cot = f"COT-2026-{uuid.uuid4().hex[:5].upper()}"
    pasos = estado.get("historial_pasos", []) + [
        f"[F_GenerarCotizacion] Cotización calculada: {cod_cot} -> Total: S/ {calc['total_pen']:,.2f}",
        f"[HITL Check] ¿Requiere autorización humana?: {'SÍ (Pausa en Grafo)' if requiere_hitl else 'NO (Autónomo)'}"
    ]
    return {
        "subtotal_pen": calc["subtotal_pen"],
        "igv_pen": calc["igv_pen"],
        "total_pen": calc["total_pen"],
        "codigo_cotizacion": cod_cot,
        "requiere_hitl": requiere_hitl,
        "motivo_pausa_hitl": motivo,
        "historial_pasos": pasos,
    }

def nodo_hitl_supervisor(estado: EstadoCotizacion) -> Dict[str, Any]:
    """
    PUNTO DE INTERVENCIÓN HUMANA (HITL):
    Ubicado estrictamente por IRREVERSIBILIDAD antes de comprometer inventario o tarifas.
    Se pausa el grafo aquí con interrupt_before.
    """
    auth = estado.get("autorizacion_supervisor", "APROBADO_POR_SUPERVISOR")
    pasos = estado.get("historial_pasos", []) + [
        f"[HITL_Supervisor] Intervención humana ejecutada. Dictamen: {auth}"
    ]
    return {
        "autorizacion_supervisor": auth,
        "historial_pasos": pasos,
    }

def nodo_enviar_cotizacion(estado: EstadoCotizacion) -> Dict[str, Any]:
    """F_EnviarCotizacion: Despacho de la cotización formal con mensaje empático."""
    nom = estado["datos_solicitud"].get("nombre_cliente", "Estimado cliente")
    serv = estado["servicio_catalogo"].get("nombre_servicio", "Servicio Funerario")
    total = estado["total_pen"]
    sub = estado["subtotal_pen"]
    igv = estado["igv_pen"]
    cod = estado["codigo_cotizacion"]

    alt_txt = ""
    if estado.get("alternativa_aplicada"):
        alt_txt = "\n*(Nota: Debido a la alta demanda en la fecha solicitada, se asignó una alternativa con tarifa preferencial)*"

    mensaje = (
        f"Estimada familia {nom},\n"
        f"Cumpliendo con brindarle la debida atención y transparencia, le presentamos la cotización solicitada:\n\n"
        f"📋 Cotización Formal N.°: {cod}\n"
        f"• Servicio: {serv}\n"
        f"• Subtotal: S/ {sub:,.2f} PEN\n"
        f"• IGV (18%): S/ {igv:,.2f} PEN\n"
        f"• Importe Total: S/ {total:,.2f} PEN{alt_txt}\n\n"
        f"Validez: 5 días hábiles. Si desea proceder con la reserva o requiere asistencia, estamos a su lado 24/7."
    )
    pasos = estado.get("historial_pasos", []) + [f"[F_EnviarCotizacion] Cotización {cod} despachada al deudo."]
    return {
        "mensaje_salida_cliente": mensaje,
        "historial_pasos": pasos,
    }

def nodo_archivar_registro(estado: EstadoCotizacion) -> Dict[str, Any]:
    """F_Archivar & F_Fin: Registro en Repositorio Central y cierre del caso."""
    pasos = estado.get("historial_pasos", []) + ["[F_Archivar] Caso registrado en Repositorio Central y cerrado con éxito."]
    return {
        "historial_pasos": pasos,
    }


# =============================================================================
# 4. CONDITIONAL EDGES (Aristas de decisión)
# =============================================================================

def decidir_validez_datos(estado: EstadoCotizacion) -> str:
    """Compuerta F_GW_Datos: ¿Datos completos?"""
    if estado["es_valida"]:
        return "datos_completos"
    return "datos_incompletos"

def decidir_disponibilidad(estado: EstadoCotizacion) -> str:
    """Compuerta F_GW_Disponible: ¿Servicio disponible?"""
    disp = estado.get("disponibilidad") or {}
    if disp.get("disponible", True):
        return "disponible"
    return "no_disponible"

def decidir_ruta_hitl(estado: EstadoCotizacion) -> str:
    """Compuerta de Riesgo Irreversible: ¿Pasa a HITL o despacho directo?"""
    if estado.get("requiere_hitl", False):
        return "requiere_autorizacion"
    return "autonomo"


# =============================================================================
# 5. CONSTRUCCIÓN DEL GRAFO DE LANGGRAPH Y ANÁLISIS DE GRADO
# =============================================================================

def construir_grafo_funeraria(con_checkpointer: bool = True):
    workflow = StateGraph(EstadoCotizacion)

    # Registro de Nodos
    workflow.add_node("recibir_solicitud", nodo_recibir_solicitud)
    workflow.add_node("validar_contrato", nodo_validar_contrato)
    workflow.add_node("solicitar_datos", nodo_solicitar_datos)
    workflow.add_node("consultar_catalogo", nodo_consultar_catalogo)
    workflow.add_node("definir_alternativa", nodo_definir_alternativa)
    workflow.add_node("calcular_cotizacion", nodo_calcular_cotizacion)
    workflow.add_node("hitl_supervisor", nodo_hitl_supervisor)
    workflow.add_node("enviar_cotizacion", nodo_enviar_cotizacion)
    workflow.add_node("archivar_registro", nodo_archivar_registro)

    # Aristas fijas y condicionales
    workflow.add_edge(START, "recibir_solicitud")
    workflow.add_edge("recibir_solicitud", "validar_contrato")

    workflow.add_conditional_edges(
        "validar_contrato",
        decidir_validez_datos,
        {
            "datos_completos": "consultar_catalogo",
            "datos_incompletos": "solicitar_datos",
        }
    )

    workflow.add_edge("solicitar_datos", END)

    workflow.add_conditional_edges(
        "consultar_catalogo",
        decidir_disponibilidad,
        {
            "disponible": "calcular_cotizacion",
            "no_disponible": "definir_alternativa",
        }
    )

    workflow.add_edge("definir_alternativa", "calcular_cotizacion")

    workflow.add_conditional_edges(
        "calcular_cotizacion",
        decidir_ruta_hitl,
        {
            "requiere_autorizacion": "hitl_supervisor",
            "autonomo": "enviar_cotizacion",
        }
    )

    workflow.add_edge("hitl_supervisor", "enviar_cotizacion")
    workflow.add_edge("enviar_cotizacion", "archivar_registro")
    workflow.add_edge("archivar_registro", END)

    checkpointer = MemorySaver() if con_checkpointer else None
    
    # HITL: Pausa previa al nodo crítico de autorización
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["hitl_supervisor"]
    )
    return app


# =============================================================================
# 6. ANÁLISIS TOPOLÓGICO: CÁLCULO DE GRADO (IN-DEGREE / OUT-DEGREE)
# =============================================================================

def calcular_grados_topologicos():
    """
    Calcula formalmente el In-Degree, Out-Degree y Grado Total de cada nodo del StateGraph.
    """
    nodos = [
        "START",
        "recibir_solicitud",
        "validar_contrato",
        "solicitar_datos",
        "consultar_catalogo",
        "definir_alternativa",
        "calcular_cotizacion",
        "hitl_supervisor",
        "enviar_cotizacion",
        "archivar_registro",
        "END",
    ]

    aristas = [
        ("START", "recibir_solicitud"),
        ("recibir_solicitud", "validar_contrato"),
        ("validar_contrato", "consultar_catalogo"),
        ("validar_contrato", "solicitar_datos"),
        ("solicitar_datos", "END"),
        ("consultar_catalogo", "calcular_cotizacion"),
        ("consultar_catalogo", "definir_alternativa"),
        ("definir_alternativa", "calcular_cotizacion"),
        ("calcular_cotizacion", "hitl_supervisor"),
        ("calcular_cotizacion", "enviar_cotizacion"),
        ("hitl_supervisor", "enviar_cotizacion"),
        ("enviar_cotizacion", "archivar_registro"),
        ("archivar_registro", "END"),
    ]

    in_degree = {n: 0 for n in nodos}
    out_degree = {n: 0 for n in nodos}

    for origen, destino in aristas:
        out_degree[origen] += 1
        in_degree[destino] += 1

    tabla_grados = []
    for n in nodos:
        tabla_grados.append({
            "nodo": n,
            "in_degree": in_degree[n],
            "out_degree": out_degree[n],
            "grado_total": in_degree[n] + out_degree[n],
            "tipo": (
                "Fuente (Source)" if in_degree[n] == 0 else
                "Sumidero (Sink)" if out_degree[n] == 0 else
                "Bifurcación / Compuerta" if out_degree[n] > 1 else
                "Convergencia" if in_degree[n] > 1 else
                "Paso Lineal"
            )
        })
    return tabla_grados, aristas


# =============================================================================
# 7. EJECUCIÓN CON MONITOREO DE LANGSMITH (RunTree & Observabilidad)
# =============================================================================

def ejecutar_con_monitoreo_langsmith():
    """
    Ejecuta el flujo completo de cotización registrando la telemetría en un RunTree
    de LangSmith con latencias, llamadas a herramientas y puntos de bifurcación.
    """
    app = construir_grafo_funeraria(con_checkpointer=True)
    thread_id = f"caso-upao-{uuid.uuid4().hex[:6]}"
    config = {"configurable": {"thread_id": thread_id}}

    # 1. Iniciar Trace Principal en LangSmith
    trace_id = uuid.uuid4()
    run_root = RunTree(
        name="Pipeline_Cotizacion_Funeraria_Velazquex",
        run_type="chain",
        id=trace_id,
        trace_id=trace_id,
        inputs={
            "cliente": "María Elena Rodriguez",
            "telefono": "987654321",
            "servicio": "Cremación",
            "fecha": "2026-10-20", # Fecha con capacidad colmada para probar alternativa
        },
        tags=["upao", "aip-sesion9", "langgraph", "hitl"],
        extra={"metadata": {"version_bpmn": "TO-BE-2.0", "arquitectura": "supervisor"}},
    )

    estado_inicial: EstadoCotizacion = {
        "id_caso": "SOL-2026-099",
        "datos_solicitud": {
            "id_solicitud": "SOL-2026-099",
            "nombre_cliente": "María Elena Rodriguez",
            "telefono": "987654321",
            "servicio_solicitado": "Cremación",
            "fecha_servicio": "2026-10-20",
        },
        "es_valida": False,
        "campos_faltantes": [],
        "servicio_catalogo": None,
        "disponibilidad": None,
        "alternativa_aplicada": False,
        "subtotal_pen": 0.0,
        "igv_pen": 0.0,
        "total_pen": 0.0,
        "codigo_cotizacion": "",
        "requiere_hitl": False,
        "autorizacion_supervisor": None,
        "motivo_pausa_hitl": "",
        "mensaje_salida_cliente": "",
        "historial_pasos": [],
    }

    # Registro de llamada al Front-End en LangSmith
    child_frontend = run_root.create_child(
        name="Agente_FrontEnd_ValidarContrato",
        run_type="chain",
        inputs=estado_inicial["datos_solicitud"],
    )

    # 2. Invocación inicial hasta punto HITL
    print(f"\n[LANGGRAPH] Invocando StateGraph con thread_id: {thread_id}...")
    salida_fase_1 = app.invoke(estado_inicial, config=config)

    child_frontend.end(outputs={
        "es_valida": salida_fase_1["es_valida"],
        "id_caso": salida_fase_1["id_caso"],
    })

    # Registro de Tool Calls en LangSmith
    child_tool_cat = run_root.create_child(
        name="Tool_Excel_ConsultarCatalogo",
        run_type="tool",
        inputs={"servicio": "Cremación"},
    )
    child_tool_cat.end(outputs=salida_fase_1.get("servicio_catalogo", {}))

    child_tool_disp = run_root.create_child(
        name="Tool_Excel_VerificarDisponibilidad",
        run_type="tool",
        inputs={"codigo": "SRV-02", "fecha": "2026-10-20"},
    )
    child_tool_disp.end(outputs=salida_fase_1.get("disponibilidad", {}))

    # Comprobación de HITL
    estado_snapshot = app.get_state(config)
    print(f"• Próximo nodo en espera: {estado_snapshot.next}")
    hitl_activo = "hitl_supervisor" in estado_snapshot.next

    if hitl_activo:
        print(f"⚠️ [HITL INTERRUPT] Grafo pausado automáticamente antes de 'hitl_supervisor'.")
        print(f"   Motivo de gobernanza: {salida_fase_1.get('motivo_pausa_hitl')}")
        print(f"   Monto comprometido: S/ {salida_fase_1.get('total_pen'):,.2f} PEN")

        child_hitl = run_root.create_child(
            name="HITL_Supervisor_IntervencionHumana",
            run_type="chain",
            inputs={
                "accion_propuesta": "Confirmar cotización y reserva de alternativa comercial",
                "importe_total_pen": salida_fase_1.get("total_pen"),
                "motivo": salida_fase_1.get("motivo_pausa_hitl"),
            },
        )

        # Simulación de aprobación por el supervisor humano
        dictamen_humano = "APROBADO_CON_DESCUENTO_AUTORIZADO"
        app.update_state(config, {"autorizacion_supervisor": dictamen_humano})
        child_hitl.end(outputs={"dictamen": dictamen_humano, "status": "APPROVED"})

        print(f"✅ [HITL RESUME] Supervisor aprobó. Reanudando ejecución desde checkpoint...")
        # Reanudación pasando None
        salida_final = app.invoke(None, config=config)
    else:
        salida_final = salida_fase_1

    # Finalizar Trace Principal
    run_root.end(outputs={
        "codigo_cotizacion": salida_final.get("codigo_cotizacion"),
        "total_pen": salida_final.get("total_pen"),
        "mensaje_cliente": salida_final.get("mensaje_salida_cliente"),
        "estado_final": "COMPLETADO_EXITOSO",
    })

    # Guardar traza JSON en disco
    traza_dict = run_root.model_dump()
    ruta_traza = os.path.join(os.path.dirname(__file__), "archivos_funeraria", "langsmith_trace_cotizacion.json")
    with open(ruta_traza, "w", encoding="utf-8") as f:
        json.dump(traza_dict, f, indent=2, ensure_ascii=False, default=str)

    return salida_final, traza_dict, ruta_traza


# =============================================================================
# 8. PUNTO DE ENTRADA PRINCIPAL PARA VALIDACIÓN
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("  LANGGRAPH & LANGSMITH: SISTEMA MULTI-AGENTE FUNERARIA VELAZQUEX")
    print("=" * 80)

    # 1. Tabla de Grados
    print("\n--- 1. ANÁLISIS DE GRADOS TOPOLÓGICOS DEL STATEGRAPH ---")
    tabla, aristas = calcular_grados_topologicos()
    print(f"{'Nodo':<25} | {'In-Degree':<10} | {'Out-Degree':<10} | {'Grado Total':<12} | {'Tipo Topológico'}")
    print("-" * 80)
    for row in tabla:
        print(f"{row['nodo']:<25} | {row['in_degree']:<10} | {row['out_degree']:<10} | {row['grado_total']:<12} | {row['tipo']}")

    # 2. Ejecución con LangSmith
    print("\n--- 2. EJECUCIÓN CON OBSERVABILIDAD LANGSMITH & CHECKPOINTING HITL ---")
    salida, traza, ruta_log = ejecutar_con_monitoreo_langsmith()

    print("\n[HISTORIAL DE EJECUCIÓN DEL GRAFO]:")
    for paso in salida["historial_pasos"]:
        print(f"  {paso}")

    print("\n[MENSAJE FINAL AL CLIENTE / FRONT-END]:")
    print(salida["mensaje_salida_cliente"])

    print(f"\n[LANGSMITH] Telemetría registrada exitosamente en:")
    print(f"  {ruta_log}")
