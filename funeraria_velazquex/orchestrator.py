"""
Orquestador de Flujo del Proceso TO-BE
Funeraria Velazquex - Coordinación Multi-Agente siguiendo las compuertas y transiciones BPMN
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from .agent_frontend import AgenteAtencionCliente
from .agent_backend import AgenteAdministracion
from .excel_service import ExcelService
from .models import (
    SolicitudEntrada,
    ValidacionResultado,
    Cotizacion,
    DecisionCliente,
    EstadoProceso,
    RegistroErrorCola,
)

logger = logging.getLogger("OrquestadorFlujo")


class OrquestadorFlujo:
    """
    Orquestador Central del Proceso TO-BE:
    'Atender y registrar solicitudes de cotización de servicios funerarios'.
    Coordina al Agente Front-End (Atención al Cliente) y al Agente Back-End (Administración)
    respetando rigurosamente cada secuencia y compuerta lógica del BPMN.
    """

    def __init__(
        self,
        excel_service: Optional[ExcelService] = None,
        agente_frontend: Optional[AgenteAtencionCliente] = None,
        agente_backend: Optional[AgenteAdministracion] = None,
    ):
        self.excel = excel_service or ExcelService()
        self.frontend = agente_frontend or AgenteAtencionCliente()
        self.backend = agente_backend or AgenteAdministracion(self.excel)
        self.trazas_ejecucion: List[str] = []
        self._sesiones: Dict[str, Dict[str, Any]] = {}

    def _registrar_traza(self, nodo_bpmn: str, descripcion: str):
        """Registra cada paso por los nodos del flujo para trazabilidad y observabilidad"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        linea = f"[{timestamp}] [{nodo_bpmn}] {descripcion}"
        self.trazas_ejecucion.append(linea)
        logger.info(linea)

    def ejecutar_flujo_completo(
        self,
        payload_solicitud: Dict[str, Any],
        datos_completados_simulados: Optional[Dict[str, Any]] = None,
        dias_espera_datos: float = 0.0,
        decision_cliente: DecisionCliente = DecisionCliente.ACEPTAR,
        nuevo_servicio_modificacion: Optional[str] = None,
        dias_espera_decision: float = 0.0,
        decision_final_tras_recordatorio: Optional[DecisionCliente] = None,
        dias_espera_final: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Ejecuta el flujo completo de principio a fin, guiando la solicitud
        a través de las ramas del proceso TO-BE según los eventos y decisiones.
        """
        self.trazas_ejecucion.clear()
        self._registrar_traza("F_Start", "Recepción de solicitud digital de cotización (Mensaje MF01).")

        # 1. Front-End recibe y normaliza payload
        solicitud = self.frontend.recibir_solicitud(payload_solicitud)

        # Si el cliente remite datos completados (F07 -> F_DatosRecibidos / MF03)
        if datos_completados_simulados:
            self._registrar_traza("F_DatosRecibidos", "Cliente remite datos completados (MF03).")
            for campo, valor in datos_completados_simulados.items():
                setattr(solicitud, campo, valor)

            # F08 -> F_Actualizar
            self._registrar_traza("F_Actualizar", "Back-End actualiza la solicitud en Repositorio Central con datos recibidos.")
            self.backend.actualizar_solicitud(solicitud)

            # F09 -> F_Validar (Re-validación)
            self._registrar_traza("F_Validar", "Re-validando información tras actualización.")
            val_resultado = self.frontend.validar_informacion(solicitud)
            if not val_resultado.es_valida:
                self._registrar_traza("F_GW_Datos", "Re-validación fallida. Solicitud aún presenta inconsistencias.")
                return {
                    "exito": False,
                    "estado_final": EstadoProceso.DATOS_INCOMPLETOS.value,
                    "mensaje_cliente": val_resultado.mensaje_empatico,
                    "trazas": self.trazas_ejecucion,
                }
            self._registrar_traza("F_GW_Datos", "Decisión: SÍ (Datos completados y validados con éxito).")
            return self._procesar_catalogo_y_cotizacion(
                solicitud=solicitud,
                decision_cliente=decision_cliente,
                nuevo_servicio_modificacion=nuevo_servicio_modificacion,
                dias_espera_decision=dias_espera_decision,
                decision_final_tras_recordatorio=decision_final_tras_recordatorio,
                dias_espera_final=dias_espera_final,
            )

        # 2. Control de Idempotencia previo a procesar nueva solicitud (Prueba P2)
        clave_idemp = self.backend.generar_clave_idempotencia(solicitud)
        duplicado = self.backend.verificar_idempotencia(clave_idemp)
        if duplicado and duplicado.get("estado_actual") not in [
            EstadoProceso.REGISTRADA_INICIAL.value,
            EstadoProceso.DATOS_INCOMPLETOS.value,
        ]:
            self._registrar_traza(
                "Idempotencia",
                f"Solicitud duplicada detectada (Hash: {clave_idemp[:12]}...). "
                f"Retornando registro existente para evitar duplicidad."
            )
            return {
                "exito": True,
                "es_duplicado": True,
                "estado_final": duplicado.get("estado_actual"),
                "codigo_cotizacion": duplicado.get("codigo_cotizacion"),
                "total_pen": float(duplicado.get("total_pen", 0.0)),
                "cotizacion": duplicado,
                "clave_idempotencia": clave_idemp,
                "registro_existente": duplicado,
                "trazas": self.trazas_ejecucion,
            }

        # 3. F01 -> F_Registrar: Registro automático en Repositorio Central (DS_Central)
        self._registrar_traza("F_Registrar", "Registro automático inicial en Repositorio Central (DS_Central).")
        self.backend.registrar_solicitud_inicial(solicitud)

        # 4. F02 -> F_Validar / F03 -> F_GW_Datos: Validación del contrato de datos
        self._registrar_traza("F_Validar", "Validando datos de entrada según el esquema del Contrato de Entrada.")
        val_resultado = self.frontend.validar_informacion(solicitud)

        # RAMA F_GW_Datos: ¿Datos completos?
        if not val_resultado.es_valida:
            self._registrar_traza("F_GW_Datos", "Decisión: NO (Información incompleta o con formatos inválidos).")
            # F05 -> F_SolicitarDatos
            self._registrar_traza("F_SolicitarDatos", "Front-End envía mensaje empático solicitando datos faltantes al cliente.")
            mensaje_faltantes = val_resultado.mensaje_empatico

            # F06 -> F_GW_EsperaDatos (Event-Based Gateway)
            self._registrar_traza("F_GW_EsperaDatos", "Compuerta de eventos: Esperando respuesta del cliente o timeout (P2D = 2 días).")

            # Evaluación de Timeout en espera de datos
            if self.frontend.evaluar_timeout_datos(dias_espera_datos):
                # F10 -> F_TimeoutDatos -> F11 -> F_Incompleta -> F12 -> F_FinIncompleta
                self._registrar_traza("F_TimeoutDatos", f"Plazo sin recibir datos vencido ({dias_espera_datos} días >= 2 días).")
                self._registrar_traza("F_Incompleta", "Back-End registra solicitud incompleta en DS_Central.")
                self.backend.registrar_solicitud_incompleta(solicitud.id_solicitud, "Plazo de 2 días vencido sin datos")
                self._registrar_traza("F_FinIncompleta", "Solicitud incompleta cerrada definitivamente.")
                return {
                    "exito": False,
                    "estado_final": EstadoProceso.INCOMPLETA_CERRADA.value,
                    "mensaje_cliente": mensaje_faltantes,
                    "motivo": "Timeout de 2 días sin recibir datos completados",
                    "trazas": self.trazas_ejecucion,
                }

            # En espera de datos dentro del plazo
            return {
                "exito": False,
                "estado_final": EstadoProceso.DATOS_INCOMPLETOS.value,
                "mensaje_cliente": mensaje_faltantes,
                "motivo": "Esperando que el cliente envíe datos faltantes.",
                "trazas": self.trazas_ejecucion,
            }

        self._registrar_traza("F_GW_Datos", "Decisión: SÍ (Datos validados y completos).")

        # 5. F04 -> F_ConsultarCatalogo
        return self._procesar_catalogo_y_cotizacion(
            solicitud=solicitud,
            decision_cliente=decision_cliente,
            nuevo_servicio_modificacion=nuevo_servicio_modificacion,
            dias_espera_decision=dias_espera_decision,
            decision_final_tras_recordatorio=decision_final_tras_recordatorio,
            dias_espera_final=dias_espera_final,
        )

    def _procesar_catalogo_y_cotizacion(
        self,
        solicitud: SolicitudEntrada,
        decision_cliente: DecisionCliente,
        nuevo_servicio_modificacion: Optional[str] = None,
        dias_espera_decision: float = 0.0,
        decision_final_tras_recordatorio: Optional[DecisionCliente] = None,
        dias_espera_final: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Ejecuta desde F_ConsultarCatalogo hasta la emisión, seguimiento y cierre.
        """
        # F_ConsultarCatalogo
        self._registrar_traza(
            "F_ConsultarCatalogo",
            f"Back-End consulta catálogo y tarifas en Excel mediante pandas para '{solicitud.servicio_solicitado}'."
        )
        encontrado, item_catalogo = self.backend.consultar_catalogo(
            solicitud.servicio_solicitado, solicitud.id_solicitud
        )

        if not encontrado or item_catalogo is None:
            # Error previsible: Servicio no existe en catálogo -> Derivado a Cola de Fallidos
            self._registrar_traza(
                "ColaErrores",
                f"Servicio '{solicitud.servicio_solicitado}' no existe en el catálogo. "
                f"Caso derivado a cola de fallidos (Prueba P3)."
            )
            return {
                "exito": False,
                "error": "Servicio no pertenece al catálogo",
                "estado_final": "ENVIADO_COLA_FALLIDOS",
                "trazas": self.trazas_ejecucion,
            }

        # F13 -> F_VerificarDisponibilidad
        self._registrar_traza(
            "F_VerificarDisponibilidad",
            f"Back-End verifica disponibilidad en tablas de Excel para {item_catalogo.codigo_servicio} "
            f"en la fecha {solicitud.fecha_servicio}."
        )
        disp_resultado = self.backend.verificar_disponibilidad(item_catalogo, solicitud.fecha_servicio)

        # F14 -> F_GW_Disponible
        if not disp_resultado.disponible:
            # F16 -> F_DefinirAlternativa
            self._registrar_traza(
                "F_GW_Disponible",
                f"Decisión: NO. Capacidad o stock no disponible para la fecha ({disp_resultado.observaciones})."
            )
            self._registrar_traza(
                "F_DefinirAlternativa",
                f"Definiendo alternativa en catálogo: '{disp_resultado.servicio_alternativo.nombre_servicio if disp_resultado.servicio_alternativo else 'N/A'}'."
            )
        else:
            self._registrar_traza("F_GW_Disponible", "Decisión: SÍ. Servicio y capacidad confirmados disponibles.")

        # F15 / F17 -> F_GW_UnirDisponibilidad -> F18 -> F_GenerarCotizacion
        self._registrar_traza("F_GW_UnirDisponibilidad", "Unión de ramas de disponibilidad.")
        self._registrar_traza("F_GenerarCotizacion", "Back-End calcula subtotal, IGV (18%) y total en Soles (PEN).")
        cotizacion = self.backend.generar_cotizacion(solicitud, item_catalogo, disp_resultado)

        # F19 -> F_RevisarCotizacion
        self._registrar_traza("F_RevisarCotizacion", "Front-End revisa internamente la cotización calculada.")

        # F20 -> F_EnviarCotizacion
        self._registrar_traza("F_EnviarCotizacion", "Front-End despacha la cotización digital formal con mensaje empático.")
        mensaje_cliente = self.frontend.formatear_cotizacion_para_cliente(cotizacion)
        cotizacion.mensaje_comercial_empatico = mensaje_cliente

        # F21 -> F_RegistrarEmision
        self._registrar_traza("F_RegistrarEmision", "Back-End registra emisión en DS_Central y programa seguimiento.")
        self.backend.registrar_emision_cotizacion(cotizacion)

        # F22 -> F_GW_EsperaDecision (Event-Based Gateway de Decisión del Cliente)
        self._registrar_traza("F_GW_EsperaDecision", "Esperando respuesta del cliente (Aceptación, Modificación, Rechazo o Timeout 2 días).")

        # =====================================================================
        # MANEJO DE RAMAS DE DECISIÓN DEL CLIENTE
        # =====================================================================

        # Rama 1: Aceptación inmediata
        if decision_cliente == DecisionCliente.ACEPTAR:
            # F23 -> F_Aceptacion -> F24 -> F_RegistrarAceptacion
            self._registrar_traza("F_Aceptacion", "Cliente remite mensaje de Aceptación (MF05).")
            self._registrar_traza("F_RegistrarAceptacion", "Back-End registra la aceptación en Repositorio Central.")
            self.backend.registrar_decision_cliente(cotizacion, DecisionCliente.ACEPTAR)
            return self._cerrar_y_archivar(cotizacion, EstadoProceso.ACEPTADA.value)

        # Rama 2: Modificación inmediata
        elif decision_cliente == DecisionCliente.MODIFICAR:
            # F26 -> F_Modificacion -> F27 -> F_RevisarModificacion -> F28 -> Loop a F_ConsultarCatalogo
            self._registrar_traza("F_Modificacion", "Cliente solicita modificación de la cotización (MF06).")
            self._registrar_traza("F_RevisarModificacion", "Front-End y Back-End revisan cambios solicitados por el familiar.")
            
            nuevo_servicio = nuevo_servicio_modificacion or "Cremación"
            self._registrar_traza(
                "F_ConsultarCatalogo",
                f"Retorno en bucle a consultar catálogo con nuevo servicio modificado: '{nuevo_servicio}'."
            )
            solicitud.servicio_solicitado = nuevo_servicio
            # Re-cotización (reproceso registrado)
            return self._procesar_catalogo_y_cotizacion(
                solicitud=solicitud,
                decision_cliente=DecisionCliente.ACEPTAR, # Acepta tras modificación
                dias_espera_decision=0.0,
            )

        # Rama 3: Rechazo inmediato
        elif decision_cliente == DecisionCliente.RECHAZAR:
            # F29 -> F_Rechazo -> F30 -> F_RegistrarRechazo
            self._registrar_traza("F_Rechazo", "Cliente remite mensaje de Rechazo (MF07).")
            self._registrar_traza("F_RegistrarRechazo", "Back-End registra el rechazo en Repositorio Central.")
            self.backend.registrar_decision_cliente(cotizacion, DecisionCliente.RECHAZAR)
            return self._cerrar_y_archivar(cotizacion, EstadoProceso.RECHAZADA.value)

        # Rama 4: Timeout de decisión inicial (>= 2 días)
        elif self.frontend.evaluar_timeout_decision(dias_espera_decision):
            # F32 -> F_TimeoutDecision -> F33 -> F_Recordatorio
            self._registrar_traza("F_TimeoutDecision", f"Plazo de seguimiento inicial vencido ({dias_espera_decision} días >= 2 días).")
            self._registrar_traza("F_Recordatorio", "Front-End envía recordatorio respetuoso de seguimiento al cliente (MF08).")
            mensaje_recordatorio = self.frontend.generar_mensaje_recordatorio(cotizacion)

            # F34 -> F_GW_EsperaFinal (Event-Based Gateway tras recordatorio)
            self._registrar_traza("F_GW_EsperaFinal", "Esperando respuesta final del cliente tras recordatorio o timeout final (P2D).")

            # Decisión tras recordatorio
            if decision_final_tras_recordatorio == DecisionCliente.ACEPTAR:
                # F35 -> F_Aceptacion2 -> F36 -> F_RegistrarAceptacion
                self._registrar_traza("F_Aceptacion2", "Cliente responde al recordatorio aceptando la propuesta (MF09).")
                self.backend.registrar_decision_cliente(cotizacion, DecisionCliente.ACEPTAR)
                return self._cerrar_y_archivar(cotizacion, EstadoProceso.ACEPTADA.value)

            elif decision_final_tras_recordatorio == DecisionCliente.MODIFICAR:
                # F37 -> F_Modificacion2 -> F38 -> F_RevisarModificacion
                self._registrar_traza("F_Modificacion2", "Cliente responde al recordatorio solicitando cambios (MF10).")
                solicitud.servicio_solicitado = nuevo_servicio_modificacion or "Velatorio"
                return self._procesar_catalogo_y_cotizacion(
                    solicitud=solicitud,
                    decision_cliente=DecisionCliente.ACEPTAR,
                    dias_espera_decision=0.0,
                )

            elif decision_final_tras_recordatorio == DecisionCliente.RECHAZAR:
                # F39 -> F_Rechazo2 -> F40 -> F_RegistrarRechazo
                self._registrar_traza("F_Rechazo2", "Cliente responde al recordatorio rechazando la propuesta (MF11).")
                self.backend.registrar_decision_cliente(cotizacion, DecisionCliente.RECHAZAR)
                return self._cerrar_y_archivar(cotizacion, EstadoProceso.RECHAZADA.value)

            elif self.frontend.evaluar_timeout_final(dias_espera_final):
                # F41 -> F_TimeoutFinal -> F42 -> F_RegistrarSinRespuesta
                self._registrar_traza(
                    "F_TimeoutFinal",
                    f"Plazo final vencido sin respuesta del deudo ({dias_espera_final} días >= 2 días)."
                )
                self._registrar_traza("F_RegistrarSinRespuesta", "Back-End registra el caso como 'Sin respuesta' en DS_Central.")
                self.backend.registrar_decision_cliente(cotizacion, DecisionCliente.TIMEOUT)
                return self._cerrar_y_archivar(cotizacion, EstadoProceso.SIN_RESPUESTA.value)

            else:
                # Aún en ventana de espera tras recordatorio
                return {
                    "exito": True,
                    "estado_final": EstadoProceso.RECORDATORIO_ENVIADO.value,
                    "cotizacion": cotizacion.model_dump(),
                    "mensaje_recordatorio": mensaje_recordatorio,
                    "trazas": self.trazas_ejecucion,
                }

        # En espera de decisión dentro del plazo inicial
        return {
            "exito": True,
            "estado_final": EstadoProceso.ESPERANDO_DECISION.value,
            "cotizacion": cotizacion.model_dump(),
            "mensaje_cliente": mensaje_cliente,
            "trazas": self.trazas_ejecucion,
        }

    def _cerrar_y_archivar(self, cotizacion: Cotizacion, estado_final: str) -> Dict[str, Any]:
        """
        F_GW_Cierre -> F_Archivar -> F_Fin:
        Concluye el ciclo del proceso TO-BE archivando la solicitud en el Repositorio Central.
        """
        self._registrar_traza("F_GW_Cierre", "Compuerta exclusiva de convergencia de cierre.")
        self._registrar_traza("F_Archivar", f"Back-End archiva solicitud {cotizacion.solicitud_id} en DS_Central.")
        self.backend.archivar_solicitud(cotizacion.solicitud_id)
        self._registrar_traza("F_Fin", "Fin del proceso TO-BE de cotización digital (Solicitud cerrada).")

        return {
            "exito": True,
            "estado_final": estado_final,
            "codigo_cotizacion": cotizacion.codigo_cotizacion,
            "total_pen": cotizacion.total_pen,
            "alternativa_aplicada": cotizacion.alternativa_aplicada,
            "cotizacion": cotizacion.model_dump(),
            "trazas": self.trazas_ejecucion,
        }

    # =========================================================================
    # CHAT INTERACTIVO Y PROCESAMIENTO CONVERSACIONAL (WhatsApp / Terminal / Web)
    # =========================================================================

    def reiniciar_sesion(self, sesion_id: str = "default"):
        """Reinicia la memoria de una sesión conversacional"""
        self._sesiones[sesion_id] = {
            "solicitud": SolicitudEntrada(
                id_solicitud=f"SOL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            ),
            "esperando_decision": False,
            "cotizacion": None,
            "registrada_inicial": False,
            "historial": [],
        }

    def procesar_mensaje_conversacional(
        self,
        mensaje_texto: str,
        sesion_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Gestiona un turno de conversación interactiva con el cliente:
        - Extrae entidades y decisiones en lenguaje natural
        - Reacciona en segundo plano según las compuertas BPMN
        - Devuelve la respuesta empática del Front-End y las trazas operativas del Back-End
        """
        if sesion_id not in self._sesiones:
            self.reiniciar_sesion(sesion_id)

        sesion = self._sesiones[sesion_id]
        solicitud_actual: SolicitudEntrada = sesion["solicitud"]
        esperando_decision: bool = sesion["esperando_decision"]
        cotizacion_actual: Optional[Cotizacion] = sesion["cotizacion"]

        num_trazas_antes = len(self.trazas_ejecucion)

        # 1. Interpretar lenguaje natural y extraer entidades
        solicitud_actual, decision, entidades = self.frontend.extraer_datos_de_mensaje_natural(
            mensaje=mensaje_texto,
            solicitud_existente=solicitud_actual,
            esperando_decision=esperando_decision,
        )
        sesion["solicitud"] = solicitud_actual

        # Guardar mensaje del usuario en historial
        sesion["historial"].append({"remitente": "cliente", "mensaje": mensaje_texto, "hora": datetime.now().strftime("%H:%M")})

        # 2. Si estábamos esperando decisión del cliente sobre una cotización emitida:
        if esperando_decision and decision and cotizacion_actual:
            if decision == DecisionCliente.ACEPTAR:
                self._registrar_traza("F_Aceptacion", f"Cliente envía mensaje de Aceptación: '{mensaje_texto}' (MF05).")
                self._registrar_traza("F_RegistrarAceptacion", "Back-End registra la aceptación en Repositorio Central (DS_Central).")
                self.backend.registrar_decision_cliente(cotizacion_actual, DecisionCliente.ACEPTAR)
                res_cierre = self._cerrar_y_archivar(cotizacion_actual, EstadoProceso.ACEPTADA.value)
                sesion["esperando_decision"] = False

                mensaje_front = (
                    f"🕊️ *¡Muchas gracias por su confianza!*\n\n"
                    f"Hemos registrado formalmente la aceptación de su cotización *N.° {cotizacion_actual.codigo_cotizacion}*.\n"
                    f"En este momento nuestro equipo de guardia se pondrá en contacto telefónico al *{cotizacion_actual.telefono}* "
                    f"para ultimar los detalles ceremoniales y la logística de traslado. Estamos a su entera disposición las 24 horas."
                )
                sesion["historial"].append({"remitente": "asistente", "mensaje": mensaje_front, "hora": datetime.now().strftime("%H:%M")})
                trazas_turno = self.trazas_ejecucion[num_trazas_antes:]
                return {
                    "mensaje_asistente": mensaje_front,
                    "estado_proceso": EstadoProceso.FINALIZADA.value,
                    "fase": "CERRADA_ACEPTADA",
                    "trazas_recientes": trazas_turno,
                    "cotizacion": cotizacion_actual.model_dump(),
                    "entidades_detectadas": entidades,
                }

            elif decision == DecisionCliente.RECHAZAR:
                self._registrar_traza("F_Rechazo", f"Cliente envía mensaje de Rechazo: '{mensaje_texto}' (MF07).")
                self._registrar_traza("F_RegistrarRechazo", "Back-End registra el rechazo en Repositorio Central (DS_Central).")
                self.backend.registrar_decision_cliente(cotizacion_actual, DecisionCliente.RECHAZAR)
                res_cierre = self._cerrar_y_archivar(cotizacion_actual, EstadoProceso.RECHAZADA.value)
                sesion["esperando_decision"] = False

                mensaje_front = (
                    f"🕊️ *Entendemos plenamente su decisión.*\n\n"
                    f"En Funeraria Velazquex le agradecemos por contactarnos. Hemos archivado su propuesta con el mayor respeto. "
                    f"Si en algún momento futuro requiere nuestra asesoría o apoyo, nuestras líneas permanecen abiertas."
                )
                sesion["historial"].append({"remitente": "asistente", "mensaje": mensaje_front, "hora": datetime.now().strftime("%H:%M")})
                trazas_turno = self.trazas_ejecucion[num_trazas_antes:]
                return {
                    "mensaje_asistente": mensaje_front,
                    "estado_proceso": EstadoProceso.FINALIZADA.value,
                    "fase": "CERRADA_RECHAZADA",
                    "trazas_recientes": trazas_turno,
                    "cotizacion": cotizacion_actual.model_dump(),
                    "entidades_detectadas": entidades,
                }

            elif decision == DecisionCliente.MODIFICAR:
                self._registrar_traza("F_Modificacion", f"Cliente solicita modificación: '{mensaje_texto}' (MF06).")
                self._registrar_traza("F_RevisarModificacion", "Front-End y Back-End inician revisión de cambios solicitados.")
                sesion["esperando_decision"] = False
                sesion["cotizacion"] = None

                mensaje_front = (
                    f"🕊️ *Con mucho gusto adaptamos la cotización.*\n\n"
                    f"Por favor coméntenos: ¿Qué cambio o adición desea realizar? (Por ejemplo: cambiar a *Cremación*, *Velatorio*, *Traslado*, o cambiar la fecha)."
                )
                sesion["historial"].append({"remitente": "asistente", "mensaje": mensaje_front, "hora": datetime.now().strftime("%H:%M")})
                trazas_turno = self.trazas_ejecucion[num_trazas_antes:]
                return {
                    "mensaje_asistente": mensaje_front,
                    "estado_proceso": EstadoProceso.MODIFICACION_SOLICITADA.value,
                    "fase": "MODIFICANDO",
                    "trazas_recientes": trazas_turno,
                    "entidades_detectadas": entidades,
                }

        # 3. Registro inicial o actualización en Repositorio Central (DS_Central)
        if not sesion["registrada_inicial"]:
            self._registrar_traza("F_Start", f"Recepción de solicitud digital de cotización (Mensaje MF01): '{mensaje_texto}'")
            self._registrar_traza("F_Registrar", "Registro automático inicial en Repositorio Central (DS_Central).")
            self.backend.registrar_solicitud_inicial(solicitud_actual)
            sesion["registrada_inicial"] = True
        elif entidades:
            self._registrar_traza("F_DatosRecibidos", f"Datos completados recibidos (MF03): {entidades}")
            self._registrar_traza("F_Actualizar", "Back-End actualiza la solicitud en Repositorio Central con datos recibidos.")
            self.backend.actualizar_solicitud(solicitud_actual)

        # 4. F02 -> F_Validar / F03 -> F_GW_Datos: Validación del contrato de datos
        self._registrar_traza("F_Validar", "Validando datos de entrada según el esquema del Contrato de Entrada.")
        val_resultado = self.frontend.validar_informacion(solicitud_actual)

        # RAMA F_GW_Datos: ¿Datos completos?
        if not val_resultado.es_valida:
            self._registrar_traza(
                "F_GW_Datos",
                f"Decisión: NO (Faltan {len(val_resultado.campos_faltantes)} campos: {', '.join(val_resultado.campos_faltantes)})."
            )
            self._registrar_traza("F_SolicitarDatos", "Front-End envía mensaje empático solicitando datos faltantes al cliente.")
            self._registrar_traza("F_GW_EsperaDatos", "Compuerta de eventos: Esperando respuesta del cliente o timeout (P2D = 2 días).")

            mensaje_front = val_resultado.mensaje_empatico
            sesion["historial"].append({"remitente": "asistente", "mensaje": mensaje_front, "hora": datetime.now().strftime("%H:%M")})
            trazas_turno = self.trazas_ejecucion[num_trazas_antes:]
            return {
                "mensaje_asistente": mensaje_front,
                "estado_proceso": EstadoProceso.DATOS_INCOMPLETOS.value,
                "fase": "ESPERANDO_DATOS",
                "campos_faltantes": val_resultado.campos_faltantes,
                "solicitud_actual": solicitud_actual.model_dump(),
                "trazas_recientes": trazas_turno,
                "entidades_detectadas": entidades,
            }

        # RAMA F_GW_Datos = SÍ -> Proceder con Catálogo, Disponibilidad y Cotización
        self._registrar_traza("F_GW_Datos", "Decisión: SÍ (Datos validados y completos).")

        # F_ConsultarCatalogo
        self._registrar_traza(
            "F_ConsultarCatalogo",
            f"Back-End consulta catálogo y tarifas en Excel mediante pandas para '{solicitud_actual.servicio_solicitado}'."
        )
        encontrado, item_catalogo = self.backend.consultar_catalogo(
            solicitud_actual.servicio_solicitado, solicitud_actual.id_solicitud
        )
        if not encontrado or item_catalogo is None:
            self._registrar_traza(
                "ColaErrores",
                f"Servicio '{solicitud_actual.servicio_solicitado}' no pertenece al catálogo. Derivado a Cola de Fallidos."
            )
            mensaje_front = (
                f"🕊️ Estimado/a familiar, hemos revisado nuestro catálogo oficial y el servicio solicitado "
                f"('*{solicitud_actual.servicio_solicitado}*') no se encuentra disponible directamente. "
                f"Nuestros servicios principales son: *Sepelio*, *Cremación*, *Velatorio* o *Traslado*. "
                f"¿Desea que le preparemos una propuesta en alguno de estos servicios?"
            )
            sesion["historial"].append({"remitente": "asistente", "mensaje": mensaje_front, "hora": datetime.now().strftime("%H:%M")})
            trazas_turno = self.trazas_ejecucion[num_trazas_antes:]
            return {
                "mensaje_asistente": mensaje_front,
                "estado_proceso": "ENVIADO_COLA_FALLIDOS",
                "fase": "ERROR_CATALOGO",
                "trazas_recientes": trazas_turno,
                "entidades_detectadas": entidades,
            }

        # F13 -> F_VerificarDisponibilidad
        self._registrar_traza(
            "F_VerificarDisponibilidad",
            f"Back-End verifica disponibilidad en tablas de Excel para {item_catalogo.codigo_servicio} "
            f"en la fecha {solicitud_actual.fecha_servicio}."
        )
        disp_resultado = self.backend.verificar_disponibilidad(item_catalogo, solicitud_actual.fecha_servicio)

        if not disp_resultado.disponible:
            self._registrar_traza(
                "F_GW_Disponible",
                f"Decisión: NO. Capacidad colmada para la fecha ({disp_resultado.observaciones})."
            )
            self._registrar_traza(
                "F_DefinirAlternativa",
                f"Definiendo alternativa en catálogo: '{disp_resultado.servicio_alternativo.nombre_servicio if disp_resultado.servicio_alternativo else 'N/A'}'."
            )
        else:
            self._registrar_traza("F_GW_Disponible", "Decisión: SÍ. Servicio y capacidad confirmados disponibles.")

        # F18 -> F_GenerarCotizacion
        self._registrar_traza("F_GW_UnirDisponibilidad", "Unión de ramas de disponibilidad.")
        self._registrar_traza("F_GenerarCotizacion", "Back-End calcula subtotal, IGV (18%) y total en Soles (PEN).")
        cotizacion = self.backend.generar_cotizacion(solicitud_actual, item_catalogo, disp_resultado)

        # F19 -> F_RevisarCotizacion
        self._registrar_traza("F_RevisarCotizacion", "Front-End revisa internamente la cotización calculada.")

        # F20 -> F_EnviarCotizacion
        self._registrar_traza("F_EnviarCotizacion", "Front-End despacha la cotización digital formal con mensaje empático.")
        mensaje_front = self.frontend.formatear_cotizacion_para_cliente(cotizacion)
        cotizacion.mensaje_comercial_empatico = mensaje_front

        # F21 -> F_RegistrarEmision
        self._registrar_traza("F_RegistrarEmision", "Back-End registra emisión en DS_Central y programa seguimiento.")
        self.backend.registrar_emision_cotizacion(cotizacion)

        # F22 -> F_GW_EsperaDecision
        self._registrar_traza("F_GW_EsperaDecision", "Esperando respuesta del cliente (Aceptar, Modificar o Rechazar).")

        sesion["cotizacion"] = cotizacion
        sesion["esperando_decision"] = True
        sesion["historial"].append({"remitente": "asistente", "mensaje": mensaje_front, "hora": datetime.now().strftime("%H:%M")})

        trazas_turno = self.trazas_ejecucion[num_trazas_antes:]
        return {
            "mensaje_asistente": mensaje_front,
            "estado_proceso": EstadoProceso.COTIZACION_ENVIADA.value,
            "fase": "COTIZACION_EMITIDA",
            "cotizacion": cotizacion.model_dump(),
            "trazas_recientes": trazas_turno,
            "entidades_detectadas": entidades,
        }
