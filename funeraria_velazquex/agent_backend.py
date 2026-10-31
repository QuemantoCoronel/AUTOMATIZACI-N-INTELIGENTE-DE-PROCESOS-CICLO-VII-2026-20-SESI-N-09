"""
Agente Back-End: Administración
Funeraria Velazquex - Consulta de Excel con pandas, Idempotencia, Disponibilidad, Alternativas y Repositorio
"""

import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd

from .config import TASA_IGV, MONEDA_SIMBOLO
from .excel_service import ExcelService
from .models import (
    SolicitudEntrada,
    ServicioCatalogo,
    DisponibilidadResultado,
    ItemCotizacion,
    Cotizacion,
    EstadoProceso,
    RegistroErrorCola,
    DecisionCliente,
)

logger = logging.getLogger("AgenteBackEnd")


class AgenteAdministracion:
    """
    Agente Back-End (Administración).
    Representa el Lane 'Administración' del modelo BPMN TO-BE:
    - F_Registrar: Registro automático en repositorio central
    - F_Actualizar: Actualización de solicitud al recibir datos completados
    - F_Incompleta: Registro de solicitud incompleta por timeout
    - F_ConsultarCatalogo: Consulta de servicios y precios en Excel mediante pandas
    - F_VerificarDisponibilidad / F_GW_Disponible: Verificación de disponibilidad en tablas de Excel
    - F_DefinirAlternativa: Selección de alternativa si el ítem no está disponible
    - F_GenerarCotizacion: Cálculo de importes y totales
    - F_RegistrarEmision: Registro de emisión y programación de seguimiento
    - F_RegistrarAceptacion / F_RegistrarRechazo / F_RegistrarSinRespuesta: Gestión de cierre
    - F_Archivar: Cierre y archivado del caso
    """

    def __init__(self, excel_service: Optional[ExcelService] = None):
        self.excel = excel_service or ExcelService()

    # =========================================================================
    # CLAVE DE IDEMPOTENCIA (Hoja 'Idempotencia' de Lab 02)
    # =========================================================================

    def generar_clave_idempotencia(self, solicitud: SolicitudEntrada) -> str:
        """
        Calcula el hash SHA-256 a partir del contenido de negocio:
        nombre_cliente + telefono + servicio_solicitado + fecha_servicio
        (Ejemplo del Lab 02: JuanPerez987654321Cremacion20-09-2026)
        """
        nom = str(solicitud.nombre_cliente or "").strip().replace(" ", "").lower()
        tel = str(solicitud.telefono or "").strip().replace(" ", "")
        serv = str(solicitud.servicio_solicitado or "").strip().replace(" ", "").lower()
        fec = str(solicitud.fecha_servicio or "").strip().replace(" ", "")

        cadena_negocio = f"{nom}{tel}{serv}{fec}"
        hash_sha256 = hashlib.sha256(cadena_negocio.encode("utf-8")).hexdigest()
        return hash_sha256

    def verificar_idempotencia(self, clave_idempotencia: str) -> Optional[Dict[str, Any]]:
        """
        Verifica si la solicitud ya fue procesada previamente para garantizar
        la prueba P2 de idempotencia (un registro por solicitud idéntica).
        """
        return self.excel.consultar_solicitud_por_idempotencia(clave_idempotencia)

    # =========================================================================
    # REGISTRO Y ACTUALIZACIÓN EN REPOSITORIO CENTRAL (F_Registrar / F_Actualizar)
    # =========================================================================

    def registrar_solicitud_inicial(self, solicitud: SolicitudEntrada) -> str:
        """
        F_Registrar: Registra la solicitud entrante en el Repositorio Central (DS_Central).
        """
        clave_idemp = self.generar_clave_idempotencia(solicitud)
        registro = {
            "id_solicitud": solicitud.id_solicitud,
            "codigo_cotizacion": "PENDIENTE",
            "clave_idempotencia": clave_idemp,
            "nombre_cliente": solicitud.nombre_cliente,
            "telefono": solicitud.telefono,
            "servicio_solicitado": solicitud.servicio_solicitado,
            "fecha_servicio": solicitud.fecha_servicio,
            "tipo_cliente": solicitud.tipo_cliente.value if solicitud.tipo_cliente else "Familiar directo",
            "estado_actual": EstadoProceso.REGISTRADA_INICIAL.value,
            "total_pen": 0.0,
            "alternativa_aplicada": "No",
        }
        self.excel.guardar_en_repositorio_central(registro)
        logger.info(f"[F_Registrar] Solicitud {solicitud.id_solicitud} registrada en Repositorio Central.")
        return clave_idemp

    def actualizar_solicitud(self, solicitud: SolicitudEntrada):
        """
        F_Actualizar: Actualiza la solicitud en DS_Central con los datos completados
        recibidos del cliente.
        """
        clave_idemp = self.generar_clave_idempotencia(solicitud)
        registro = {
            "id_solicitud": solicitud.id_solicitud,
            "clave_idempotencia": clave_idemp,
            "nombre_cliente": solicitud.nombre_cliente,
            "telefono": solicitud.telefono,
            "servicio_solicitado": solicitud.servicio_solicitado,
            "fecha_servicio": solicitud.fecha_servicio,
            "estado_actual": EstadoProceso.DATOS_ACTUALIZADOS.value,
        }
        self.excel.guardar_en_repositorio_central(registro)
        logger.info(f"[F_Actualizar] Solicitud {solicitud.id_solicitud} actualizada en DS_Central.")

    def registrar_solicitud_incompleta(self, id_solicitud: str, motivo: str):
        """
        F_Incompleta: Registra la solicitud como incompleta tras vencer el timeout de 2 días.
        """
        registro = {
            "id_solicitud": id_solicitud,
            "estado_actual": EstadoProceso.INCOMPLETA_CERRADA.value,
        }
        self.excel.guardar_en_repositorio_central(registro)
        logger.warning(f"[F_Incompleta] Solicitud {id_solicitud} cerrada por datos incompletos ({motivo}).")

    # =========================================================================
    # CONSULTA DE CATÁLOGO Y PRECIOS (F_ConsultarCatalogo)
    # =========================================================================

    def consultar_catalogo(self, servicio_solicitado: str, id_solicitud: str) -> Tuple[bool, Optional[ServicioCatalogo]]:
        """
        F_ConsultarCatalogo: Consulta servicios y precios en Excel mediante pandas.
        Si el servicio no existe, aplica el manejo de error previsible (Catálogo de errores, Error 1)
        y lo deriva a la Cola de Fallidos (Dead Letter Queue).
        """
        encontrado, item, mensaje = self.excel.consultar_catalogo(servicio_solicitado)
        if not encontrado:
            # Error previsible 1: "El servicio solicitado no existe en el catálogo"
            error_cola = RegistroErrorCola(
                id_caso=id_solicitud,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                error=mensaje,
                clase_error="De datos / Catálogo",
                carga_original={"servicio_solicitado": servicio_solicitado, "id_solicitud": id_solicitud},
                reintentos=0,
            )
            self.excel.registrar_cola_errores(error_cola)
            logger.error(f"[F_ConsultarCatalogo] Error: {mensaje}. Enviado a cola de fallidos.")
            return False, None

        logger.info(f"[F_ConsultarCatalogo] Servicio encontrado: {item.nombre_servicio} ({MONEDA_SIMBOLO} {item.precio_base_pen})")
        return True, item

    # =========================================================================
    # VERIFICACIÓN DE DISPONIBILIDAD Y ALTERNATIVAS (F_VerificarDisponibilidad / F_DefinirAlternativa)
    # =========================================================================

    def verificar_disponibilidad(
        self, item: ServicioCatalogo, fecha_servicio: str
    ) -> DisponibilidadResultado:
        """
        F_VerificarDisponibilidad / F_GW_Disponible:
        Consulta la tabla 'Disponibilidad' en Excel con pandas.
        Si no hay disponibilidad, localiza la alternativa sugerida (F_DefinirAlternativa).
        """
        resultado = self.excel.verificar_disponibilidad(item, fecha_servicio)
        if resultado.disponible:
            logger.info(f"[F_VerificarDisponibilidad] F_GW_Disponible = Sí ({item.nombre_servicio} en {fecha_servicio})")
        else:
            logger.warning(
                f"[F_VerificarDisponibilidad] F_GW_Disponible = No. Motivo: {resultado.observaciones}. "
                f"Alternativa sugerida: {resultado.servicio_alternativo.nombre_servicio if resultado.servicio_alternativo else 'Sin alternativa'}"
            )
        return resultado

    # =========================================================================
    # GENERACIÓN Y CÁLCULO DE COTIZACIÓN (F_GenerarCotizacion)
    # =========================================================================

    def generar_cotizacion(
        self,
        solicitud: SolicitudEntrada,
        item_base: ServicioCatalogo,
        disp_resultado: DisponibilidadResultado,
    ) -> Cotizacion:
        """
        F_GenerarCotizacion:
        Calcula los importes netos, impuestos (IGV 18%) y total en Soles (PEN).
        Si se asignó alternativa, ajusta los ítems y los importes según la tabla de catálogo.
        """
        secuencia = solicitud.id_solicitud.split("-")[-1] if "-" in str(solicitud.id_solicitud) else "001"
        codigo_cot = f"COT-{datetime.now().strftime('%Y%m')}-{secuencia}"
        clave_idemp = self.generar_clave_idempotencia(solicitud)

        items_cot: List[ItemCotizacion] = []
        alternativa_aplicada = not disp_resultado.disponible
        detalle_alt = None

        if alternativa_aplicada and disp_resultado.servicio_alternativo:
            item_elegido = disp_resultado.servicio_alternativo
            subtotal = item_elegido.precio_base_pen
            items_cot.append(
                ItemCotizacion(
                    codigo=item_elegido.codigo_servicio,
                    concepto=item_elegido.nombre_servicio,
                    descripcion=item_elegido.descripcion,
                    precio_unitario=item_elegido.precio_base_pen,
                    cantidad=1,
                    subtotal=subtotal,
                    es_alternativa=True,
                )
            )
            detalle_alt = (
                f"El servicio original '{item_base.nombre_servicio}' no tiene cupo disponible "
                f"para el {solicitud.fecha_servicio} ({disp_resultado.motivo_alternativa}). "
                f"Se ha asignado como alternativa: '{item_elegido.nombre_servicio}' con tarifa de "
                f"{MONEDA_SIMBOLO} {item_elegido.precio_base_pen:,.2f}."
            )
        else:
            subtotal = item_base.precio_base_pen
            items_cot.append(
                ItemCotizacion(
                    codigo=item_base.codigo_servicio,
                    concepto=item_base.nombre_servicio,
                    descripcion=item_base.descripcion,
                    precio_unitario=item_base.precio_base_pen,
                    cantidad=1,
                    subtotal=subtotal,
                    es_alternativa=False,
                )
            )

        # Cálculo de importes con precisión contable
        igv = round(subtotal * TASA_IGV, 2)
        total = round(subtotal + igv, 2)

        cotizacion = Cotizacion(
            codigo_cotizacion=codigo_cot,
            clave_idempotencia=clave_idemp,
            solicitud_id=solicitud.id_solicitud,
            nombre_cliente=solicitud.nombre_cliente or "Familiar Responsable",
            telefono=solicitud.telefono or "",
            tipo_cliente=solicitud.tipo_cliente.value if solicitud.tipo_cliente else "Familiar directo",
            servicio_solicitado=solicitud.servicio_solicitado or "",
            fecha_servicio=solicitud.fecha_servicio or "",
            items=items_cot,
            subtotal_pen=subtotal,
            igv_pen=igv,
            total_pen=total,
            fecha_emision=datetime.now(),
            fecha_validez_dias=5,
            estado=EstadoProceso.COTIZACION_GENERADA,
            alternativa_aplicada=alternativa_aplicada,
            detalle_alternativa=detalle_alt,
        )

        logger.info(f"[F_GenerarCotizacion] Cotización {codigo_cot} calculada: Total {MONEDA_SIMBOLO} {total:,.2f}")
        return cotizacion

    # =========================================================================
    # REGISTRO DE EMISIÓN Y SEGUIMIENTO (F_RegistrarEmision)
    # =========================================================================

    def registrar_emision_cotizacion(self, cotizacion: Cotizacion):
        """
        F_RegistrarEmision: Registra la cotización emitida en DS_Central
        y programa el seguimiento del cliente.
        """
        registro = {
            "id_solicitud": cotizacion.solicitud_id,
            "codigo_cotizacion": cotizacion.codigo_cotizacion,
            "clave_idempotencia": cotizacion.clave_idempotencia,
            "total_pen": cotizacion.total_pen,
            "alternativa_aplicada": "Sí" if cotizacion.alternativa_aplicada else "No",
            "estado_actual": EstadoProceso.COTIZACION_ENVIADA.value,
        }
        self.excel.guardar_en_repositorio_central(registro)
        logger.info(f"[F_RegistrarEmision] Emisión de cotización {cotizacion.codigo_cotizacion} registrada en DS_Central.")

    # =========================================================================
    # REGISTRO DE DECISIÓN Y ARCHIVADO (F_RegistrarAceptacion / Rechazo / SinRespuesta / F_Archivar)
    # =========================================================================

    def registrar_decision_cliente(self, cotizacion: Cotizacion, decision: DecisionCliente):
        """
        Registra en DS_Central la respuesta del cliente según las ramas del BPMN:
        - Aceptar -> F_RegistrarAceptacion
        - Rechazar -> F_RegistrarRechazo
        - Sin respuesta -> F_RegistrarSinRespuesta
        """
        estados_map = {
            DecisionCliente.ACEPTAR: EstadoProceso.ACEPTADA,
            DecisionCliente.RECHAZAR: EstadoProceso.RECHAZADA,
            DecisionCliente.TIMEOUT: EstadoProceso.SIN_RESPUESTA,
            DecisionCliente.MODIFICAR: EstadoProceso.MODIFICACION_SOLICITADA,
        }
        nuevo_estado = estados_map.get(decision, EstadoProceso.ARCHIVADA)

        registro = {
            "id_solicitud": cotizacion.solicitud_id,
            "codigo_cotizacion": cotizacion.codigo_cotizacion,
            "estado_actual": nuevo_estado.value,
        }
        self.excel.guardar_en_repositorio_central(registro)
        logger.info(f"Decisión '{decision.value}' registrada en DS_Central para {cotizacion.codigo_cotizacion}")

    def archivar_solicitud(self, id_solicitud: str):
        """
        F_Archivar -> F_Fin: Archiva la solicitud y concluye el proceso TO-BE.
        """
        registro = {
            "id_solicitud": id_solicitud,
            "estado_actual": EstadoProceso.ARCHIVADA.value,
        }
        self.excel.guardar_en_repositorio_central(registro)
        logger.info(f"[F_Archivar] Solicitud {id_solicitud} archivada en repositorio central. Proceso F_Fin concluido.")
