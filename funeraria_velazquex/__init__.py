"""
Paquete funeraria_velazquex
Sistema Multi-Agente para la Automatización de Cotizaciones Digitales
Basado en el BPMN TO-BE e Instrumentos de Laboratorio UPAO
"""

from .config import (
    TIMEOUT_DIAS_DATOS,
    TIMEOUT_DIAS_DECISION,
    TIMEOUT_DIAS_FINAL,
    EXCEL_LAB_01_PATH,
    EXCEL_LAB_02_PATH,
    BPMN_TO_BE_PATH,
    BPMN_AS_IS_PATH,
    ARCHIVOS_FUNERARIA_DIR,
    COLA_ERRORES_PATH,
)
from .models import (
    SolicitudEntrada,
    Cotizacion,
    DecisionCliente,
    EstadoProceso,
    ValidacionResultado,
)
from .excel_service import ExcelService
from .agent_frontend import AgenteAtencionCliente
from .agent_backend import AgenteAdministracion
from .orchestrator import OrquestadorFlujo

__all__ = [
    "SolicitudEntrada",
    "Cotizacion",
    "DecisionCliente",
    "EstadoProceso",
    "ValidacionResultado",
    "ExcelService",
    "AgenteAtencionCliente",
    "AgenteAdministracion",
    "OrquestadorFlujo",
    "TIMEOUT_DIAS_DATOS",
    "TIMEOUT_DIAS_DECISION",
    "TIMEOUT_DIAS_FINAL",
    "EXCEL_LAB_01_PATH",
    "EXCEL_LAB_02_PATH",
    "BPMN_TO_BE_PATH",
    "BPMN_AS_IS_PATH",
    "ARCHIVOS_FUNERARIA_DIR",
    "COLA_ERRORES_PATH",
]
