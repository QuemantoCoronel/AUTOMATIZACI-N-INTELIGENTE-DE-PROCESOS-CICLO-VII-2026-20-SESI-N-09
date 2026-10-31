"""
Módulo de Configuración del Sistema Multi-Agente
Funeraria Velazquex - Automatización de Cotizaciones Digitales
"""

from pathlib import Path

# Directorio base del proyecto y carpeta de archivos
BASE_DIR = Path(__file__).resolve().parent.parent
ARCHIVOS_FUNERARIA_DIR = BASE_DIR / "archivos_funeraria"

def _resolver_ruta(nombre_archivo: str) -> Path:
    """Busca el archivo primero en archivos_funeraria, y si no, en BASE_DIR"""
    ruta_en_carpeta = ARCHIVOS_FUNERARIA_DIR / nombre_archivo
    if ruta_en_carpeta.exists():
        return ruta_en_carpeta
    return BASE_DIR / nombre_archivo

# Rutas de los archivos de Excel
EXCEL_LAB_01_PATH = _resolver_ruta("Instrumentos_Laboratorio 01 - Grupo 01.xlsx")
EXCEL_LAB_02_PATH = _resolver_ruta("Instrumentos_Laboratorio_02 - Grupo 01.xlsx")

# Rutas de los diagramas BPMN
BPMN_TO_BE_PATH = _resolver_ruta("TO_BE_Cotizaciones_Funeraria_Velazquex_ORDENADO.bpmn")
BPMN_AS_IS_PATH = _resolver_ruta("AS_IS_Cotizaciones_Funeraria_Velazquex_ORDENADO.bpmn")

# Repositorios del sistema (guardados preferentemente en archivos_funeraria)
REPOSITORIO_CENTRAL_PATH = ARCHIVOS_FUNERARIA_DIR / "registro_cotizaciones_central.xlsx"
COLA_ERRORES_PATH = ARCHIVOS_FUNERARIA_DIR / "cola_errores.json"

# Políticas de Temporizadores (BPMN ISO 8601: P2D = 2 Días)
TIMEOUT_DIAS_DATOS = 2        # F_TimeoutDatos: 2 días para completar datos
TIMEOUT_DIAS_DECISION = 2     # F_TimeoutDecision: 2 días para decisión inicial
TIMEOUT_DIAS_FINAL = 2        # F_TimeoutFinal: 2 días tras recordatorio sin respuesta

# Parámetros de negocio
TASA_IGV = 0.18               # Impuesto General a las Ventas (18%)
MONEDA_SIMBOLO = "S/"
MONEDA_ISO = "PEN"

# Reintentos para errores transitorios y de sistema (según Catálogo de Errores Lab 02)
MAX_REINTENTOS_SISTEMA = 3
ESPERA_REINTENTO_SEGUNDOS = 5

# Plantillas de empatía para Atención al Cliente (Duelo y Respeto)
PLANTILLAS_EMPATIA = {
    "condolencias": (
        "Estimada familia {nombre_cliente}, en nombre de Funeraria Velazquex le extendemos "
        "nuestras más sentidas condolencias y solidaridad en este momento tan doloroso."
    ),
    "datos_faltantes": (
        "Comprendemos lo delicado de esta situación. Para brindarle una cotización transparente, "
        "digna y adaptada a sus requerimientos, con sumo respeto le solicitamos completar los siguientes datos:\n"
        "{lista_faltantes}\n"
        "Estamos a su disposición las 24 horas del día para acompañarle."
    ),
    "cotizacion_disponible": (
        "Hemos preparado la propuesta detallada para el servicio funerario solicitado. "
        "En Funeraria Velazquex nos comprometemos a cuidar cada detalle con el máximo respeto y calidez."
    ),
    "alternativa_sugerida": (
        "Deseamos informarle con total transparencia que, para la fecha requerida ({fecha_servicio}), "
        "el servicio inicial presenta una limitación operativa ({motivo}).\n"
        "Pensando en la tranquilidad de su familia, le presentamos una alternativa inmediata y equivalente: "
        "*{nombre_alternativa}*."
    ),
    "recordatorio_seguimiento": (
        "Estimada familia {nombre_cliente}, nos comunicamos con todo respeto para consultar si tuvo "
        "oportunidad de revisar la propuesta de cotización N.° {codigo_cotizacion}. Si requiere algún ajuste, "
        "facilidad o personalización del servicio, nuestro equipo de guardia está para apoyarle."
    ),
    "cierre_incompleta": (
        "Estimado/a {nombre_cliente}, al haber transcurrido el plazo de espera de datos ({dias} días), "
        "la solicitud ha sido suspendida temporalmente. Quedamos a su entera disposición cuando usted lo estime oportuno."
    ),
    "cierre_sin_respuesta": (
        "Estimado/a {nombre_cliente}, tras haber enviado el recordatorio y transcurrido el tiempo de seguimiento, "
        "procedemos a archivar respetuosamente su cotización. Podrá reactivarla en cualquier momento comunicándose con nosotros."
    )
}
