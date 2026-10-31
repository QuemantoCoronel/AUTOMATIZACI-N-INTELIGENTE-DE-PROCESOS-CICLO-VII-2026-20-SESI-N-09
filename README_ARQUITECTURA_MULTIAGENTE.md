# Arquitectura del Sistema Multi-Agente de Cotizaciones Digitales
## Funeraria Velazquex · Automatización Inteligente de Procesos (TO-BE)

Este proyecto implementa el código base en Python para un **Sistema Multi-Agente** que automatiza integralmente el flujo de cotizaciones digitales de la **Funeraria Velazquex**, estructurado a partir del modelado BPMN 2.0 TO-BE (`TO_BE_Cotizaciones_Funeraria_Velazquex_ORDENADO.bpmn`) y los instrumentos de campo de los Laboratorios 01 y 02 (UPAO).

---

## 1. Arquitectura Lógica de Componentes

El sistema se compone de tres piezas fundamentales desacopladas y coordinadas mediante paso de mensajes y eventos:

```
                                    +-----------------------------+
                                    |    CLIENTE (WhatsApp / Web)  |
                                    +--------------+--------------+
                                                   | MF01: Solicitud digital
                                                   v
+------------------------------------------------------------------------------------------------------+
| FUNERARIA VELAZQUEX                                                                                  |
|                                                                                                      |
|  [LANE 1: ATENCIÓN AL CLIENTE]                                                                      |
|  +------------------------------------------------------------------------------------------------+  |
|  |                                  AGENTE FRONT-END                                              |  |
|  |  • Recepción y normalización de solicitud digital (F_Start)                                    |  |
|  |  • Compuerta de validación de datos según Contrato de Entrada (F_GW_Datos)                        |  |
|  |  • Solicitud de datos faltantes con protocolo de empatía en duelo (F_SolicitarDatos)           |  |
|  |  • Gestión de temporizadores de espera y timeout de 2 días (F_TimeoutDatos / P2D)               |  |
|  |  • Formateo y despacho de cotización digital transparente (F_EnviarCotizacion)                 |  |
|  |  • Envío de recordatorio respetuoso tras plazo vencido de 2 días (F_Recordatorio)              |  |
|  +-----------------------------------+------------------------------------------------------------+  |
|                                      |                                                               |
|                                      | Coordinación de Eventos / Mensajes                            |
|                                      v                                                               |
|  +------------------------------------------------------------------------------------------------+  |
|  |                                ORQUESTADOR DE FLUJO                                            |  |
|  |  • Coordinador central que rige las secuencias F01 a F45 del BPMN TO-BE                        |  |
|  |  • Control de compuertas exclusivas y de eventos (F_GW_EsperaDatos, F_GW_EsperaDecision)       |  |
|  |  • Trazabilidad y observabilidad de cada nodo en tiempo real                                   |  |
|  +-----------------------------------+------------------------------------------------------------+  |
|                                      |                                                               |
|                                      v                                                               |
|  [LANE 2: ADMINISTRACIÓN]                                                                           |
|  +------------------------------------------------------------------------------------------------+  |
|  |                                  AGENTE BACK-END                                               |  |
|  |  • Generación de Clave de Idempotencia SHA-256 (nombre + tel + serv + fecha)                   |  |
|  |  • Interrogación directa de archivos Excel mediante pandas:                                    |  |
|  |     - 'Instrumentos_Laboratorio_02': Contrato de entrada, Catálogo de errores, Disponibilidad   |  |
|  |     - 'Instrumentos_Laboratorio 01': Línea base del proceso y muestreo                         |  |
|  |  • Verificación de disponibilidad de stock/salas/hornos en tablas de Excel (F_GW_Disponible)    |  |
|  |  • Asignación automática de alternativa comercial y operativa si no hay cupo (F_DefinirAlt)   |  |
|  |  • Cálculo de cotización: Subtotal, IGV (18%) e importe total en Soles (PEN) (F_GenerarCotiz)  |  |
|  |  • Registro en Repositorio Central (DS_Central) y Cola de Fallidos (Dead Letter Queue)         |  |
|  +------------------------------------------------------------------------------------------------+  |
+------------------------------------------------------------------------------------------------------+
```

---

## 2. Correspondencia 1-a-1 con el Diagrama BPMN TO-BE

| Elemento BPMN | Nombre en el Diagrama | Rol / Agente Responsable | Implementación en Código |
|---|---|---|---|
| `F_Start` | Solicitud digital recibida | Agente Front-End | `AgenteAtencionCliente.recibir_solicitud()` |
| `F_Registrar` | Registrar solicitud automáticamente | Agente Back-End | `AgenteAdministracion.registrar_solicitud_inicial()` |
| `F_Validar` | Validar información | Agente Front-End | `AgenteAtencionCliente.validar_informacion()` |
| `F_GW_Datos` | ¿Datos completos? | Front-End / Orquestador | `ValidacionResultado.es_valida` (Compuerta exclusiva) |
| `F_SolicitarDatos` | Solicitar datos faltantes | Agente Front-End | `AgenteAtencionCliente.generar_mensaje_datos_faltantes()` |
| `F_GW_EsperaDatos` | Esperar datos del cliente | Orquestador de Flujo | Event-Based Gateway (espera de `F_DatosRecibidos` o `F_TimeoutDatos`) |
| `F_TimeoutDatos` | Plazo sin recibir datos (P2D) | Agente Front-End | `AgenteAtencionCliente.evaluar_timeout_datos()` (2 días) |
| `F_Incompleta` | Registrar solicitud incompleta | Agente Back-End | `AgenteAdministracion.registrar_solicitud_incompleta()` |
| `F_FinIncompleta` | Solicitud incompleta (Fin) | Orquestador | Cierre definitivo sin cotización |
| `F_ConsultarCatalogo` | Consultar servicios y precios | Agente Back-End | `ExcelService.consultar_catalogo()` con `pandas` |
| `F_VerificarDisponibilidad` | Verificar disponibilidad | Agente Back-End | `ExcelService.verificar_disponibilidad()` con `pandas` |
| `F_GW_Disponible` | ¿Servicio disponible? | Back-End / Orquestador | `DisponibilidadResultado.disponible` |
| `F_DefinirAlternativa` | Definir alternativa | Agente Back-End | Selección de alternativa predefinida con recálculo de tarifa |
| `F_GenerarCotizacion` | Generar cotización | Agente Back-End | `AgenteAdministracion.generar_cotizacion()` (Subtotal + IGV) |
| `F_RevisarCotizacion` | Revisar cotización | Agente Front-End | Revisión interna de propuesta |
| `F_EnviarCotizacion` | Enviar cotización al cliente | Agente Front-End | `AgenteAtencionCliente.formatear_cotizacion_para_cliente()` |
| `F_RegistrarEmision` | Registrar emisión y programar seguimiento | Agente Back-End | `AgenteAdministracion.registrar_emision_cotizacion()` |
| `F_GW_EsperaDecision` | Esperar decisión del cliente | Orquestador de Flujo | Event-Based Gateway (Aceptación, Modificación, Rechazo, Timeout) |
| `F_TimeoutDecision` | Plazo seguimiento vencido (P2D) | Agente Front-End | `AgenteAtencionCliente.evaluar_timeout_decision()` (2 días) |
| `F_Recordatorio` | Enviar recordatorio | Agente Front-End | `AgenteAtencionCliente.generar_mensaje_recordatorio()` |
| `F_GW_EsperaFinal` | Esperar respuesta final | Orquestador de Flujo | Event-Based Gateway post-recordatorio |
| `F_TimeoutFinal` | Sin respuesta (P2D) | Agente Front-End | `AgenteAtencionCliente.evaluar_timeout_final()` (2 días más) |
| `F_RegistrarAceptacion` | Registrar aceptación | Agente Back-End | Actualización de estado en `registro_cotizaciones_central.xlsx` |
| `F_RegistrarRechazo` | Registrar rechazo | Agente Back-End | Actualización de estado en `registro_cotizaciones_central.xlsx` |
| `F_RegistrarSinRespuesta` | Registrar sin respuesta | Agente Back-End | Actualización de estado en `registro_cotizaciones_central.xlsx` |
| `F_GW_Cierre` | Unir cierre | Orquestador | Convergencia exclusiva |
| `F_Archivar` | Archivar solicitud | Agente Back-End | `AgenteAdministracion.archivar_solicitud()` |
| `F_Fin` | Solicitud cerrada (Fin) | Orquestador | Fin del proceso |

---

## 3. Estructura del Código Fuente

```
drive-download-20261015T024345Z-1-001/
├── archivos_funeraria/                             # Carpeta con todos los insumos y repositorios del proceso
│   ├── Instrumentos_Laboratorio 01 - Grupo 01.xlsx     # Línea base, muestreo, acta y entrevistas
│   ├── Instrumentos_Laboratorio_02 - Grupo 01.xlsx     # Contrato de datos, catálogo de errores, catálogo y stock
│   ├── Instrumentos_Laboratorio_02 - Grupo 01.xlsx.bak # Respaldo del instrumento original
│   ├── TO_BE_Cotizaciones_Funeraria_Velazquex_ORDENADO.bpmn # Modelo BPMN 2.0 TO-BE
│   ├── AS_IS_Cotizaciones_Funeraria_Velazquex_FINAL(ACTUALMENTE).bpmn # Modelo AS-IS inicial
│   ├── AS_IS_Cotizaciones_Funeraria_Velazquex_ORDENADO.bpmn # Modelo AS-IS ordenado
│   ├── acad4b6d-0865-4a66-b1af-213ac1bb1fdb.png       # Imagen/diagrama de referencia
│   ├── registro_cotizaciones_central.xlsx              # Repositorio Central sincronizado (DS_Central)
│   └── cola_errores.json                               # Cola de Fallidos (Dead Letter Queue - 6 campos)
├── funeraria_velazquex/                            # Paquete del Sistema Multi-Agente
│   ├── __init__.py                                 # Exportaciones públicas del paquete
│   ├── config.py                                   # Constantes, temporizadores (P2D) y resolución de rutas
│   ├── models.py                                   # Modelos Pydantic (Solicitud, Cotización, Errores)
│   ├── excel_service.py                            # Interrogación de archivos Excel mediante pandas
│   ├── agent_frontend.py                           # Agente Front-End (Atención al Cliente)
│   ├── agent_backend.py                            # Agente Back-End (Administración)
│   └── orchestrator.py                             # Orquestador del Flujo TO-BE
├── main.py                                         # Banco de pruebas automatizado ejecutable
└── README_ARQUITECTURA_MULTIAGENTE.md              # Documentación técnica completa
```

---

## 4. Banco de Pruebas Automatizado (`main.py`)

El script principal ejecuta 8 casos de prueba exhaustivos que validan cada ramificación del proceso:

1. **Caso 1: Flujo Estándar Exitoso**: Solicitud válida de Sepelio -> Cotización calculada en Soles -> Aceptación -> Archivado.
2. **Caso 2: Compuerta F_GW_Datos con Datos Faltantes**: Generación de mensaje empático con condolencias solicitando teléfono y fecha -> Simulación de reenvío de datos del deudo dentro del plazo (MF03) -> Actualización (`F_Actualizar`) -> Re-validación y emisión.
3. **Caso 3: Timeout de Espera de Datos (P2D)**: Solicitud incompleta sin respuesta tras 2 días -> Disparo de `F_TimeoutDatos` -> `F_Incompleta` -> `F_FinIncompleta`.
4. **Caso 4: Disponibilidad y Alternativa Automática (`F_DefinirAlternativa`)**: Consulta de Cremación en fecha con capacidad colmada (`2026-10-20`) -> Back-End detecta `disponible = 'No'` en Excel -> Sugiere automáticamente `Sepelio Integral Dignidad` -> Front-End comunica desglose y justificación transparente.
5. **Caso 5: Idempotencia SHA-256 (Prueba P2)**: Verificación de hash SHA-256 sobre contenido de negocio para evitar registros duplicados.
6. **Caso 6: Servicio Inexistente y Cola de Fallidos (Prueba P3)**: Consulta de `'AtaudPremium'` -> Clasificado como error de catálogo -> Registro en `cola_errores.json` con los 6 campos mínimos.
7. **Caso 7: Timeout de Decisión y Recordatorio Empático (`F_Recordatorio`)**: Transcurso de 2 días sin respuesta -> Front-End envía recordatorio respetuoso -> Cliente acepta en segunda instancia (`F_Aceptacion2`).
8. **Caso 8: Analítica de Impacto vs. Línea Base (Laboratorio 01)**: Extracción directa de las magnitudes de línea base (mediana manual: 0.83 horas / costo unitario S/ 3.66) vs. tiempo digital (< 1 segundo).

---

## 5. Instrucciones de Ejecución

Para ejecutar el sistema y correr el banco de pruebas completo:

```bash
python main.py
```
