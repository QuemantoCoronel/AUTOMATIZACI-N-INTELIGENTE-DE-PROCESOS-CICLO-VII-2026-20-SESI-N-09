"""
Modelos de Datos y Contratos para el Sistema Multi-Agente
Funeraria Velazquex - Basado en el Contrato de Entrada (Lab 02) y BPMN TO-BE
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TipoCliente(str, Enum):
    FAMILIAR_DIRECTO = "Familiar directo"
    REPRESENTANTE = "Representante"


class DecisionCliente(str, Enum):
    ACEPTAR = "Aceptar"
    MODIFICAR = "Modificar"
    RECHAZAR = "Rechazar"
    TIMEOUT = "Timeout"


class EstadoProceso(str, Enum):
    # Estados alineados estrictamente con el modelo BPMN TO-BE
    RECIBIDA = "F_Start: Solicitud recibida"
    REGISTRADA_INICIAL = "F_Registrar: Solicitud registrada automáticamente"
    DATOS_INCOMPLETOS = "F_GW_Datos: Incompleta (Esperando datos del cliente)"
    DATOS_ACTUALIZADOS = "F_Actualizar: Solicitud actualizada con datos recibidos"
    VALIDADA = "F_Validar: Validación aprobada"
    INCOMPLETA_CERRADA = "F_FinIncompleta: Cerrada por plazo vencido (P2D)"
    CATALOGO_CONSULTADO = "F_ConsultarCatalogo: Catálogo y precios consultados"
    DISPONIBLE = "F_GW_Disponible: Servicio disponible"
    ALTERNATIVA_ASIGNADA = "F_DefinirAlternativa: Alternativa sugerida por indisponibilidad"
    COTIZACION_GENERADA = "F_GenerarCotizacion: Cotización calculada"
    COTIZACION_REVISADA = "F_RevisarCotizacion: Revisión interna completada"
    COTIZACION_ENVIADA = "F_EnviarCotizacion: Emitida y enviada al cliente"
    ESPERANDO_DECISION = "F_GW_EsperaDecision: Esperando decisión del cliente"
    MODIFICACION_SOLICITADA = "F_Modificacion: Modificación solicitada por cliente"
    RECORDATORIO_ENVIADO = "F_Recordatorio: Recordatorio de seguimiento enviado (P2D)"
    ESPERANDO_DECISION_FINAL = "F_GW_EsperaFinal: Esperando respuesta tras recordatorio"
    ACEPTADA = "F_RegistrarAceptacion: Cotización aceptada"
    RECHAZADA = "F_RegistrarRechazo: Cotización rechazada"
    SIN_RESPUESTA = "F_RegistrarSinRespuesta: Sin respuesta tras recordatorio"
    ARCHIVADA = "F_Archivar: Solicitud archivada en repositorio central"
    FINALIZADA = "F_Fin: Proceso cerrado"


class SolicitudEntrada(BaseModel):
    """
    Contrato de datos de entrada según 'Contrato de entrada' en Lab 02.
    """
    id_solicitud: Optional[str] = Field(default=None, description="Identificador único del caso (ej: SOL-2026-001)")
    nombre_cliente: Optional[str] = Field(default=None, description="Nombre de la persona que cotiza (3-100 car.)")
    telefono: Optional[str] = Field(default=None, description="Teléfono de contacto (9-15 dígitos numéricos)")
    servicio_solicitado: Optional[str] = Field(default=None, description="Servicio: Sepelio | Cremación | Velatorio | Traslado")
    fecha_servicio: Optional[str] = Field(default=None, description="Fecha solicitada (Formato AAAA-MM-DD)")
    tipo_cliente: Optional[TipoCliente] = Field(default=TipoCliente.FAMILIAR_DIRECTO, description="Familiar directo | Representante")
    observaciones: Optional[str] = Field(default="Sin observaciones especiales", description="Observaciones (máx. 300 car.)")
    fecha_ingreso: datetime = Field(default_factory=datetime.now, description="Timestamp de recepción digital")


class ValidacionResultado(BaseModel):
    """
    Resultado de la evaluación de la compuerta lógica F_GW_Datos
    """
    es_valida: bool
    campos_faltantes: List[str] = Field(default_factory=list)
    errores_detalle: List[str] = Field(default_factory=list)
    mensaje_empatico: Optional[str] = None
    solicitud_normalizada: Optional[SolicitudEntrada] = None


class ServicioCatalogo(BaseModel):
    """
    Ítem extraído directamente de la tabla de catálogo en Excel mediante pandas
    """
    codigo_servicio: str
    categoria: str
    nombre_servicio: str
    descripcion: str
    precio_base_pen: float
    disponible_por_defecto: str
    codigo_alternativa: Optional[str] = None
    nombre_alternativa: Optional[str] = None
    motivo_alternativa: Optional[str] = None


class DisponibilidadResultado(BaseModel):
    """
    Resultado de la verificación en la tabla de disponibilidad en Excel
    """
    codigo_servicio: str
    fecha_servicio: str
    disponible: bool
    capacidad_total: int = 1
    cupos_ocupados: int = 0
    observaciones: str = ""
    tiene_alternativa: bool = False
    servicio_alternativo: Optional[ServicioCatalogo] = None
    motivo_alternativa: Optional[str] = None


class ItemCotizacion(BaseModel):
    codigo: str
    concepto: str
    descripcion: str
    precio_unitario: float
    cantidad: int = 1
    subtotal: float
    es_alternativa: bool = False


class Cotizacion(BaseModel):
    """
    Entidad formal de cotización generada por el Back-End y comunicada por el Front-End
    """
    codigo_cotizacion: str
    clave_idempotencia: str
    solicitud_id: str
    nombre_cliente: str
    telefono: str
    tipo_cliente: str
    servicio_solicitado: str
    fecha_servicio: str
    items: List[ItemCotizacion]
    subtotal_pen: float
    igv_pen: float
    total_pen: float
    fecha_emision: datetime = Field(default_factory=datetime.now)
    fecha_validez_dias: int = 5
    estado: EstadoProceso = EstadoProceso.COTIZACION_GENERADA
    alternativa_aplicada: bool = False
    detalle_alternativa: Optional[str] = None
    mensaje_comercial_empatico: Optional[str] = None


class RegistroErrorCola(BaseModel):
    """
    Esquema de la Cola de Fallidos (Dead Letter Queue) con los 6 campos mínimos
    exigidos en el entregable E2 / Lab 02.
    """
    id_caso: str
    timestamp: str
    error: str
    clase_error: str               # 'De datos' | 'De sistema' | 'Transitorio'
    carga_original: Dict[str, Any] # Carga original completa para reprocesamiento
    reintentos: int
