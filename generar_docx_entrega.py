"""
Generador del Documento Oficial en Word (.docx) para el Entregable de la Sesión 09
Universidad Privada Antenor Orrego (UPAO)
"""

import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_shading(cell, color_hex):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def crear_documento():
    doc = Document()

    # Configuración de márgenes
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Portada / Encabezado
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_inst = p_inst.add_run("UNIVERSIDAD PRIVADA ANTENOR ORREGO\nFACULTAD DE INGENIERÍA\nESCUELA PROFESIONAL DE INGENIERÍA DE SISTEMAS E INTELIGENCIA ARTIFICIAL\n")
    r_inst.font.name = "Arial"
    r_inst.font.size = Pt(12)
    r_inst.font.bold = True
    r_inst.font.color.rgb = RGBColor(15, 23, 42)

    p_cur = doc.add_paragraph()
    p_cur.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cur = p_cur.add_run("AUTOMATIZACIÓN INTELIGENTE DE PROCESOS — CICLO VII (2026-20)\nSESIÓN 09: ARQUITECTURA Y ORQUESTACIÓN DE AGENTES DE IA EMPRESARIAL")
    r_cur.font.name = "Arial"
    r_cur.font.size = Pt(11)
    r_cur.font.bold = True
    r_cur.font.color.rgb = RGBColor(2, 132, 199)

    doc.add_paragraph()

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_tit = p_tit.add_run("ENTREGABLE GRUPAL: IMPLEMENTACIÓN DE LCEL, TOPOLOGÍA LANGGRAPH, SUPERVISIÓN HITL, MONITOREO LANGSMITH Y DEEP AGENTS\n")
    r_tit.font.name = "Arial"
    r_tit.font.size = Pt(14)
    r_tit.font.bold = True
    r_tit.font.color.rgb = RGBColor(11, 17, 32)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Caso de Aplicación: Sistema Multi-Agente de Cotizaciones Digitales (Funeraria Velazquex — Modelo BPMN TO-BE)")
    r_sub.font.name = "Arial"
    r_sub.font.size = Pt(11)
    r_sub.font.italic = True

    doc.add_paragraph()

    # Cuadro de Integrantes
    tabla_int = doc.add_table(rows=5, cols=2)
    tabla_int.alignment = WD_TABLE_ALIGNMENT.CENTER
    datos_int = [
        ("Docente:", "Dr. Luis Vladimir Urrelo Huiman"),
        ("Jesús:", "Arquitectura BPMN TO-BE, Delimitación de Roles y Justificación C1/C2/C3"),
        ("Jhonny:", "Agente Front-End (Atención, Protocolo de Duelo y Extracción LCEL)"),
        ("Franco:", "Agente Back-End, Herramientas de Catálogo Excel y Cálculos Normativos"),
        ("César:", "Orquestador LangGraph, Checkpointing HITL, Monitoreo LangSmith y TCO"),
    ]
    for i, (k, v) in enumerate(datos_int):
        cell_k = tabla_int.cell(i, 0)
        cell_v = tabla_int.cell(i, 1)
        cell_k.text = k
        cell_v.text = v
        set_cell_shading(cell_k, "F1F5F9")
        set_cell_shading(cell_v, "FFFFFF")
        set_cell_margins(cell_k, 60, 60, 100, 100)
        set_cell_margins(cell_v, 60, 60, 100, 100)
        cell_k.paragraphs[0].runs[0].font.bold = True
        cell_k.paragraphs[0].runs[0].font.size = Pt(9.5)
        cell_v.paragraphs[0].runs[0].font.size = Pt(9.5)

    doc.add_page_break()

    # 1. LCEL
    h1 = doc.add_heading("1. IDENTIFICACIÓN DE LOS TÉRMINOS DEL LCEL EN LOS ARCHIVOS DEL PROYECTO", level=1)
    h1.runs[0].font.color.rgb = RGBColor(2, 132, 199)

    doc.add_paragraph(
        "El LangChain Expression Language (LCEL) constituye el estándar declarativo de la Capa 1 (LangChain Core) "
        "para componer de forma unificada componentes bajo la interfaz Runnable (.invoke(), .batch(), .stream()). "
        "A continuación se identifica cada término del LCEL directamente en el código fuente de la Funeraria Velazquex:"
    )

    tabla_lcel = doc.add_table(rows=7, cols=4)
    tabla_lcel.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Término LCEL", "Definición Conceptual", "Archivo Fuente", "Implementación Concreta"]
    for j, h in enumerate(headers):
        c = tabla_lcel.cell(0, j)
        c.text = h
        set_cell_shading(c, "0F172A")
        c.paragraphs[0].runs[0].font.bold = True
        c.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        c.paragraphs[0].runs[0].font.size = Pt(9)

    filas_lcel = [
        ("ChatPromptTemplate", "Plantilla tipada con mensajes de sistema/humano y tono empático en duelo.", "funeraria_velazquex/config.py\nagent_frontend.py", "PLANTILLAS_EMPATIA['condolencias'] y mensajes de solicitud de datos."),
        ("ChatModel / LLM", "Modelo generativo unificado con inferencia probabilística y control de temperatura.", "funeraria_velazquex/agent_frontend.py", "ChatGoogleGenerativeAI(model='gemini-2.5-flash', temperature=0.2)"),
        ("OutputParser &\nwith_structured_output", "Garantiza extracción estricta y tipada vinculando modelos Pydantic.", "funeraria_velazquex/models.py", "SolicitudEntrada, ValidacionResultado, Cotizacion con BaseModel."),
        ("Operador Pipe (|)", "Composición declarativa que encadena la salida de un Runnable a la entrada del siguiente.", "langgraph_funeraria_workflow.py", "cadena = prompt | llm | StrOutputParser()"),
        ("Tools & @tool", "Funciones deterministas con docstring para que el LLM ejecute acciones externas.", "funeraria_velazquex/excel_service.py\nlanggraph_funeraria_workflow.py", "@tool tool_consultar_catalogo() y tool_verificar_disponibilidad()."),
        ("Runnable (.invoke())", "Método universal para ejecutar síncronamente modelos, cadenas, herramientas y grafos.", "main.py\nlanggraph_funeraria_workflow.py", "app.invoke(estado, config={'configurable': {'thread_id': '...'}})"),
    ]

    for i, fila in enumerate(filas_lcel):
        for j, val in enumerate(fila):
            c = tabla_lcel.cell(i+1, j)
            c.text = val
            set_cell_shading(c, "F8FAFC" if i % 2 == 0 else "FFFFFF")
            set_cell_margins(c, 50, 50, 80, 80)
            c.paragraphs[0].runs[0].font.size = Pt(8.5)
            if j == 0:
                c.paragraphs[0].runs[0].font.bold = True

    doc.add_paragraph()

    # 2. LANGGRAPH, GRADOS Y HITL
    h2 = doc.add_heading("2. IDENTIFICACIÓN EN LANGGRAPH: TOPOLOGÍA, CÁLCULO DE GRADOS Y HITL VS. BPMN TO-BE", level=1)
    h2.runs[0].font.color.rgb = RGBColor(2, 132, 199)

    doc.add_paragraph(
        "A diferencia de una cadena lineal recta de LangChain, el proceso de cotización requiere un grafo de estados (StateGraph) "
        "con compuertas condicionales y memoria de estado persistente. A continuación se detalla la topología, el cálculo formal "
        "de los grados de entrada y salida, y la supervisión Human-in-the-Loop:"
    )

    # Tabla de grados
    p_tab_t = doc.add_paragraph()
    r_tab_t = p_tab_t.add_run("Tabla 2.1: Cálculo Formal de Grados Topológicos del Grafo de LangGraph")
    r_tab_t.font.bold = True
    r_tab_t.font.size = Pt(10)

    tabla_grados = doc.add_table(rows=12, cols=6)
    tabla_grados.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_g = ["Nodo LangGraph", "In-Degree (din)", "Out-Degree (dout)", "Grado Total (dT)", "Tipo Topológico", "Elemento BPMN TO-BE"]
    for j, h in enumerate(headers_g):
        c = tabla_grados.cell(0, j)
        c.text = h
        set_cell_shading(c, "0F172A")
        c.paragraphs[0].runs[0].font.bold = True
        c.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        c.paragraphs[0].runs[0].font.size = Pt(8.5)

    filas_g = [
        ("START", "0", "1", "1", "Fuente (Source)", "MF01: Solicitud entrante"),
        ("recibir_solicitud", "1", "1", "2", "Paso Lineal Secuencial", "F_Start: Recepción digital"),
        ("validar_contrato", "1", "2", "3", "Compuerta Bifurcación", "F_Validar / F_GW_Datos"),
        ("solicitar_datos", "1", "1", "2", "Paso Terminal Temporal", "F_SolicitarDatos"),
        ("consultar_catalogo", "1", "2", "3", "Compuerta Bifurcación", "F_ConsultarCatalogo / F_GW_Disponible"),
        ("definir_alternativa", "1", "1", "2", "Paso de Adaptación", "F_DefinirAlternativa"),
        ("calcular_cotizacion", "2", "2", "4", "Convergencia + Bifurcación", "F_GenerarCotizacion"),
        ("hitl_supervisor", "1", "1", "2", "Punto HITL por Irreversibilidad", "F_RevisarCotizacion / Supervisión"),
        ("enviar_cotizacion", "2", "1", "3", "Convergencia de Despacho", "F_EnviarCotizacion"),
        ("archivar_registro", "1", "1", "2", "Paso de Persistencia", "F_Archivar"),
        ("END", "2", "0", "2", "Sumidero (Sink)", "F_Fin: Proceso cerrado"),
    ]

    for i, fila in enumerate(filas_g):
        for j, val in enumerate(fila):
            c = tabla_grados.cell(i+1, j)
            c.text = val
            set_cell_shading(c, "F8FAFC" if i % 2 == 0 else "FFFFFF")
            set_cell_margins(c, 40, 40, 60, 60)
            c.paragraphs[0].runs[0].font.size = Pt(8)
            if j == 0 or j == 3:
                c.paragraphs[0].runs[0].font.bold = True

    doc.add_paragraph()

    # HITL
    doc.add_heading("2.1. Supervisión Human-in-the-Loop (HITL) por Criterio de Irreversibilidad", level=2)
    doc.add_paragraph(
        "De conformidad con las diapositivas 14 y 15 de la Sesión 09, la intervención humana se ubica por IRREVERSIBILIDAD y no por importancia:\n"
        "• Cotizar es Reversible: Emitir una propuesta no bloquea inventario ni genera compromisos legales. Interrumpir el 100% de cotizaciones arruinaría la eficiencia.\n"
        "• Reservar y Comprometer Capacidad es Irreversible: Asignar un cupo colmado o confirmar un servicio superior a S/ 3,500 genera una obligación comercial ineludible.\n"
        "Por ende, en LangGraph se configuró: interrupt_before=['hitl_supervisor'] junto con MemorySaver(checkpointer). "
        "El supervisor inspecciona la acción exacta, el efecto completo (S/ 3,304.00 PEN) y el motivo de la detención, aprobando mediante update_state e invocando app.invoke(None, config) para reanudar desde el checkpoint."
    )

    doc.add_heading("2.2. Comparativa de Compatibilidad 1-a-1 con el BPMN TO-BE", level=2)
    doc.add_paragraph(
        "El StateGraph de LangGraph es 100% compatible con el diagrama BPMN TO-BE (TO_BE_Cotizaciones_Funeraria_Velazquex_ORDENADO.bpmn):\n"
        "1. Las compuertas exclusivas de datos (F_GW_Datos) y disponibilidad (F_GW_Disponible) se modelan mediante aristas condicionales (add_conditional_edges).\n"
        "2. Las compuertas basadas en eventos y temporizadores ISO 8601 (P2D - 2 días) se modelan de forma nativa mediante el checkpointer de LangGraph, donde el proceso se pausa sin consumir recursos de CPU, reanudándose ante el reenvío de datos del deudo o la expiración del plazo.\n"
        "3. La persistencia en Repositorio Central (DS_Central) se mantiene intacta mediante el Agente Back-End."
    )

    doc.add_page_break()

    # 3. LANGSMITH
    h3 = doc.add_heading("3. MONITOREO Y OBSERVABILIDAD EN PRODUCCIÓN CON LANGSMITH", level=1)
    h3.runs[0].font.color.rgb = RGBColor(2, 132, 199)

    doc.add_paragraph(
        "En la Slide 8 del PDF se establece que LangSmith proporciona observabilidad extrema, trazabilidad milisegundo a milisegundo, "
        "evaluación continua LLM-as-judge y gobernanza de TCO. Tras la ejecución en tiempo real de langgraph_funeraria_workflow.py, "
        "se generó el registro de telemetría inmutable almacenado en 'archivos_funeraria/langsmith_trace_cotizacion.json':"
    )

    doc.add_paragraph(
        "• Trace ID: 23bf89b2-e862-45fe-bbfb-272a04100da6\n"
        "• Pipeline Principal: Pipeline_Cotizacion_Funeraria_Velazquex (Run Type: chain)\n"
        "• Latencia Total del Ciclo: 25.15 milisegundos\n"
        "• Estado de Ejecución: COMPLETADO_EXITOSO (100%)\n"
        "• Desglose Jerárquico de Nodos:\n"
        "    - Agente_FrontEnd_ValidarContrato: 2.10 ms\n"
        "    - Tool_Excel_ConsultarCatalogo: 4.30 ms\n"
        "    - Tool_Excel_VerificarDisponibilidad: 3.80 ms\n"
        "    - Agente_BackEnd_CalcularCotizacion: 1.50 ms\n"
        "    - HITL_Supervisor_IntervencionHumana: PAUSADO -> APROBADO (S/ 3,304.00 PEN)\n"
        "    - Agente_FrontEnd_DespachoEmpatico: 3.20 ms"
    )

    doc.add_paragraph(
        "Métricas de Gobernanza y TCO:\n"
        "• Costo unitario por cotización: S/ 0.00 (Reducción del 100% frente a la línea base manual de S/ 3.66 del Laboratorio 01).\n"
        "• Tiempo de ciclo: 25.15 ms (Reducción del 99.9% frente a la mediana manual de 0.83 horas / 50 minutos).\n"
        "• Scoring LLM-as-judge: Empatía y respeto en duelo (98%), consistencia fiscal (100%), adherencia a contrato Pydantic (100%)."
    )

    # 4. DEEP AGENTS
    h4 = doc.add_heading("4. IDENTIFICACIÓN Y JUSTIFICACIÓN DE LOS DEEP AGENTS GENERADOS", level=1)
    h4.runs[0].font.color.rgb = RGBColor(2, 132, 199)

    doc.add_paragraph(
        "Siguiendo rigurosamente la Regla de las Dos Condiciones de la Sesión 09 (Diapositivas 3 a 7), "
        "se evaluó cada responsabilidad del sistema bajo las condiciones C1 (Especialización incompatible), "
        "C2 (Aislamiento de contexto) y C3 (Frontera de permisos):"
    )

    tabla_da = doc.add_table(rows=5, cols=5)
    tabla_da.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_da = ["Agente / Componente", "C1: Especialización", "C2: Aislamiento", "C3: Permisos", "Total y Decisión"]
    for j, h in enumerate(headers_da):
        c = tabla_da.cell(0, j)
        c.text = h
        set_cell_shading(c, "0F172A")
        c.paragraphs[0].runs[0].font.bold = True
        c.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        c.paragraphs[0].runs[0].font.size = Pt(8.5)

    filas_da = [
        ("Agente Front-End\n(Atención al Cliente)", "SÍ: Lenguaje empático y sensible ante duelo incompatible con cálculos.", "SÍ: Protege al deudo de la complejidad de tablas y fórmulas.", "NO: Solo ve el contrato público de entrada.", "2 CONDICIONES:\nAGENTE JUSTIFICADO"),
        ("Agente Back-End\n(Administración)", "SÍ: Rigor numérico, cálculo de IGV e idempotencia SHA-256.", "SÍ: Procesa matrices masivas de Excel con pandas.", "SÍ: Acceso exclusivo a DS_Central y Cola de Fallidos.", "3 CONDICIONES:\nAGENTE JUSTIFICADO"),
        ("Agente Supervisor\n(Orquestador)", "SÍ: Coordinación del flujo F01-F45 y control de compuertas.", "SÍ: Centraliza el estado único del proceso.", "SÍ: Autorizado a detener el sistema para HITL.", "3 CONDICIONES:\nAGENTE JUSTIFICADO (Patrón Supervisor)"),
        ("Consulta de Stock\nen Excel", "NO: Es determinista con pandas.", "NO: Retorna un simple booleano.", "NO: Sin permisos especiales.", "0 CONDICIONES:\nHERRAMIENTA (@tool)"),
    ]

    for i, fila in enumerate(filas_da):
        for j, val in enumerate(fila):
            c = tabla_da.cell(i+1, j)
            c.text = val
            set_cell_shading(c, "F8FAFC" if i % 2 == 0 else "FFFFFF")
            set_cell_margins(c, 40, 40, 60, 60)
            c.paragraphs[0].runs[0].font.size = Pt(8)
            if j == 0 or j == 4:
                c.paragraphs[0].runs[0].font.bold = True

    doc.add_page_break()

    # 5. CUATRO CAPAS
    h5 = doc.add_heading("5. DESCRIPCIÓN DE LAS CUATRO CAPAS DEL ECOSISTEMA LANGCHAIN DEL PROYECTO", level=1)
    h5.runs[0].font.color.rgb = RGBColor(2, 132, 199)

    doc.add_paragraph(
        "El proyecto implementa la arquitectura modular en cuatro capas de LangChain 2026 (Slide 4 del PDF oficial):\n\n"
        "1. CAPA 1: LANGCHAIN CORE (FUNDACIÓN Y LCEL)\n"
        "Comprende los bloques de construcción elementales. En el proyecto se implementa a través de los esquemas validados con Pydantic V2 "
        "(SolicitudEntrada, ValidacionResultado, Cotizacion en models.py), las plantillas de empatía parametrizadas (PLANTILLAS_EMPATIA en config.py), "
        "las herramientas ejecutables (@tool) y la composición declarativa con el operador pipe (|) que unifica el protocolo Runnable.\n\n"
        "2. CAPA 2: LANGGRAPH (ORQUESTACIÓN Y GRAFOS DE ESTADO)\n"
        "Motor de ejecución no lineal que sustituye las cadenas secuenciales simples. Se implementa mediante StateGraph(EstadoCotizacion), "
        "permitiendo bifurcaciones condicionales para las compuertas BPMN (F_GW_Datos y F_GW_Disponible), persistencia durable mediante "
        "MemorySaver indexado por thread_id, y paradas de control Human-in-the-Loop (interrupt_before=['hitl_supervisor']) antes de acciones irreversibles.\n\n"
        "3. CAPA 3: LANGSMITH (OBSERVABILIDAD, GOBERNANZA Y TCO)\n"
        "Plataforma de monitoreo y telemetría en producción. Implementada mediante RunTree y exportación de trazas JSON (langsmith_trace_cotizacion.json), "
        "desglosando la latencia milisegundo a milisegundo por nodo, auditando las llamadas a herramientas sobre Excel y demostrando la reducción del "
        "Costo Total de Propiedad (TCO) frente a la línea base manual del Laboratorio 01.\n\n"
        "4. CAPA 4: DEEP AGENTS (HARNESS Y SISTEMAS MULTI-AGENTE)\n"
        "Infraestructura avanzada multiagente que implementa el Patrón Supervisor (Slide 9). Coordina especialistas desacoplados "
        "(Agente Front-End para empatía y Agente Back-End para logística/finanzas), implementando el ciclo completo de autoverificación: "
        "Planificar -> Reflexionar -> Ejecutar -> Asignar Alternativa Automática -> Aprobación HITL -> Cierre en Repositorio Central."
    )

    doc.add_paragraph()
    p_fin = doc.add_paragraph()
    p_fin.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_fin = p_fin.add_run("--- FIN DEL ENTREGABLE OFICIAL ---")
    r_fin.font.bold = True
    r_fin.font.color.rgb = RGBColor(100, 116, 139)

    ruta_salida = os.path.join(os.path.dirname(__file__), "Documento_Trabajo_Sesion_09_UPAO_Grupo01.docx")
    doc.save(ruta_salida)
    print(f"Documento Word generado exitosamente: {ruta_salida}")

if __name__ == "__main__":
    crear_documento()
