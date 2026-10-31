# Automatización Inteligente de Procesos · Sesión 09
## Funeraria Velazquex · Sistema Multi-Agente de Cotizaciones Digitales (BPMN TO-BE)
### Universidad Privada Antenor Orrego (UPAO) · Ciclo VII (Semestre 2026-20)
**Docente:** Dr. Luis Vladimir Urrelo Huiman  
**Integrantes del Grupo 01:**
- **Jesús:** Arquitectura BPMN TO-BE, Gobernanza y Delimitación de Roles
- **Jhonny:** Agente Front-End (Atención, Protocolo de Duelo y Extracción LCEL)
- **Franco:** Agente Back-End, Herramientas de Catálogo Excel y Cálculos Normativos
- **César:** Orquestador LangGraph, Checkpointing HITL, Monitoreo LangSmith y TCO

---

## 📌 Guía Rápida para el Equipo: ¿Qué deben hacer para entregar el trabajo?

Todo lo que el profesor solicitó en la consigna de la **Sesión 09** ya está completamente desarrollado, resuelto con código real y redactado en este repositorio:

1. 📄 **Documento Oficial para Entrega:**
   - Si van a subir o imprimir el informe en Word, utilicen directamente:  
     👉 **`Documento_Trabajo_Sesion_09_UPAO_Grupo01.docx`**  
     *(Contiene la portada institucional, formato universitario UPAO, tablas formales y los 5 puntos resueltos).*
   - También pueden leer o copiar todo el contenido desde el archivo Markdown:  
     👉 **`DOCUMENTO_ENTREGABLE_SESION_09_UPAO.md`**

2. 📸 **Capturas de Pantalla y Diagramas:**
   - Abran con doble clic en su navegador el archivo:  
     👉 **`reporte_visual_sesion09.html`**  
     *(Contiene el diagrama interactivo de LangGraph, la tabla de grados topológicos y el panel de trazabilidad de LangSmith listo para hacer capturas).*

3. 🚀 **Demostración en Vivo del Código:**
   - Si el profesor pide ejecutar el grafo en vivo, corran en la terminal:
     ```bash
     python langgraph_funeraria_workflow.py
     ```
     *(Imprime la tabla formal de grados topológicos, ejecuta la pausa HITL antes de acciones irreversibles, simula la aprobación del supervisor y muestra el registro de auditoría de LangSmith).*

---

## 📑 Resumen de los 5 Puntos Solicitados por el Docente

| Punto | Requerimiento del Docente | Dónde está resuelto en el Repositorio |
|---|---|---|
| **1** | **Identifique los términos del LCEL de su proyecto** (en los archivos). | `funeraria_velazquex/config.py` (`ChatPromptTemplate`), `agent_frontend.py` (`ChatModel`), `models.py` (`with_structured_output` Pydantic), `langgraph_funeraria_workflow.py` (Operador pipe `\|`) y `excel_service.py` (`@tool`). |
| **2** | **Identifique en LangGraph: El grado (y diagrámelo) y los HITL** y compare con BPMN TO-BE. | Implementado en `langgraph_funeraria_workflow.py`. Cálculo formal de $d_{in}$ y $d_{out}$ de los 11 nodos, supervisión HITL ubicada por **irreversibilidad** (`interrupt_before=['hitl_supervisor']`) y correspondencia 1-a-1 con las compuertas del BPMN TO-BE. |
| **3** | **Mostrar el monitoreo de LangSmith** tras una ejecución mínima. | Telemetría real registrada en `archivos_funeraria/langsmith_trace_cotizacion.json` con desglose milisegundo a milisegundo (latencia total: 25.15 ms vs. 50 minutos manuales). |
| **4** | **Identifique sus Deep Agents Generados**. | Justificación teórica mediante la **Regla de las Dos Condiciones** (C1, C2, C3): Agente Front-End (2 condiciones), Agente Back-End (3 condiciones), Supervisor (3 condiciones), y por qué la consulta de stock es una **Herramienta (`@tool`)** determinista y no un agente. |
| **5** | **Describa las 4 capas del ecosistema LangChain**. | Desglose modular de Capa 1 (Core/LCEL), Capa 2 (LangGraph), Capa 3 (LangSmith) y Capa 4 (Deep Agents / Patrón Supervisor). |

---

## 🏗️ Estructura del Repositorio

```
.
├── Documento_Trabajo_Sesion_09_UPAO_Grupo01.docx # Documento Word oficial listo para entregar
├── DOCUMENTO_ENTREGABLE_SESION_09_UPAO.md       # Informe técnico completo en formato Markdown
├── reporte_visual_sesion09.html                 # Dashboard visual interactivo con SVG y métricas
├── langgraph_funeraria_workflow.py              # Implementación ejecutable de LangGraph + LangSmith
├── requirements.txt                             # Librerías necesarias para ejecutar el proyecto
├── app_web.py                                   # Servidor Web interactivo con interfaz de chat
├── chat_cli.py                                  # Simulador interactivo en consola/terminal
├── main.py                                      # Banco automatizado de 8 pruebas del BPMN TO-BE
├── README_ARQUITECTURA_MULTIAGENTE.md           # Documentación arquitectónica original
├── funeraria_velazquex/                         # Paquete modular del sistema multiagente
│   ├── agent_frontend.py                        # Agente Front-End (Atención y Empatía)
│   ├── agent_backend.py                         # Agente Back-End (Administración y Stock)
│   ├── orchestrator.py                          # Orquestador del flujo y transiciones F01-F45
│   ├── models.py                                # Contratos Pydantic (SolicitudEntrada, Cotizacion)
│   ├── excel_service.py                         # Consultas a Excel con pandas (Herramientas @tool)
│   └── config.py                                # Temporizadores P2D y plantillas de condolencias
└── archivos_funeraria/                          # Repositorio de datos del proceso
    ├── TO_BE_Cotizaciones_Funeraria_Velazquex_ORDENADO.bpmn # Modelo BPMN 2.0 TO-BE
    ├── Instrumentos_Laboratorio 01 - Grupo 01.xlsx          # Línea base y muestreo manual
    ├── Instrumentos_Laboratorio_02 - Grupo 01.xlsx          # Catálogo de servicios y capacidad
    ├── registro_cotizaciones_central.xlsx                   # Repositorio Central (DS_Central)
    ├── cola_errores.json                                    # Cola de Fallidos (Dead Letter Queue)
    └── langsmith_trace_cotizacion.json                      # Traza de telemetría inmutable LangSmith
```

---

## ⚙️ Instalación y Ejecución Local

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/QuemantoCoronel/AUTOMATIZACI-N-INTELIGENTE-DE-PROCESOS-CICLO-VII-2026-20-SESI-N-09.git
   cd AUTOMATIZACI-N-INTELIGENTE-DE-PROCESOS-CICLO-VII-2026-20-SESI-N-09
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecutar el Grafo de LangGraph y LangSmith:**
   ```bash
   python langgraph_funeraria_workflow.py
   ```

4. **Ejecutar la Aplicación Web Interactiva:**
   ```bash
   python app_web.py
   ```
   Abrir en el navegador: `http://localhost:8000`
