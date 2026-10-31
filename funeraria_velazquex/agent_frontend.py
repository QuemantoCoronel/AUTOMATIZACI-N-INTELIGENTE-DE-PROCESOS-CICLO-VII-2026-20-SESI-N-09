"""
Agente Front-End: Atención al Cliente
Funeraria Velazquex - Recepción, Validación Empática y Gestión de Recordatorios
"""

import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from .config import (
    PLANTILLAS_EMPATIA,
    TIMEOUT_DIAS_DATOS,
    TIMEOUT_DIAS_DECISION,
    TIMEOUT_DIAS_FINAL,
    MONEDA_SIMBOLO,
)
from .models import (
    SolicitudEntrada,
    ValidacionResultado,
    TipoCliente,
    Cotizacion,
    EstadoProceso,
    DecisionCliente,
)

logger = logging.getLogger("AgenteFrontEnd")


class AgenteAtencionCliente:
    """
    Agente Front-End (Atención al Cliente).
    Representa el Lane 'Atención al cliente' del modelo BPMN TO-BE:
    - F_Start: Recepción de solicitud digital
    - F_Validar / F_GW_Datos: Validación del contrato de entrada
    - F_SolicitarDatos: Envío de solicitud de datos faltantes con tono empático
    - F_GW_EsperaDatos / F_TimeoutDatos: Control de timeout de 2 días para completar datos
    - F_RevisarCotizacion / F_EnviarCotizacion: Presentación y despacho de cotización
    - F_Recordatorio: Envío de recordatorio respetuoso tras plazo vencido (2 días)
    - F_GW_EsperaFinal / F_TimeoutFinal: Cierre por inactividad tras recordatorio
    """

    def __init__(self, servicios_permitidos: Optional[List[str]] = None):
        self.servicios_permitidos = servicios_permitidos or [
            "Sepelio", "Cremación", "Velatorio", "Traslado"
        ]

    # =========================================================================
    # RECEPCIÓN Y NORMALIZACIÓN DE SOLICITUD (F_Start)
    # =========================================================================

    def recibir_solicitud(self, payload: Dict[str, Any]) -> SolicitudEntrada:
        """
        Recepciona el payload digital (Webhook, WhatsApp o Formulario)
        y lo mapea al modelo SolicitudEntrada.
        """
        id_sol = payload.get("id_solicitud") or f"SOL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        solicitud = SolicitudEntrada(
            id_solicitud=id_sol,
            nombre_cliente=payload.get("nombre_cliente"),
            telefono=str(payload.get("telefono", "")).strip() if payload.get("telefono") else None,
            servicio_solicitado=payload.get("servicio_solicitado"),
            fecha_servicio=payload.get("fecha_servicio"),
            tipo_cliente=payload.get("tipo_cliente", TipoCliente.FAMILIAR_DIRECTO),
            observaciones=payload.get("observaciones", "Sin observaciones especiales"),
            fecha_ingreso=datetime.now(),
        )
        logger.info(f"[F_Start] Solicitud recibida: {solicitud.id_solicitud} de {solicitud.nombre_cliente}")
        return solicitud

    def extraer_datos_de_mensaje_natural(
        self,
        mensaje: str,
        solicitud_existente: Optional[SolicitudEntrada] = None,
        esperando_decision: bool = False,
    ) -> Tuple[SolicitudEntrada, Optional[DecisionCliente], Dict[str, Any]]:
        """
        Interpreta un mensaje en lenguaje natural recibido por chat/WhatsApp,
        extrayendo entidades de negocio (nombre, teléfono, servicio, fecha)
        o detectando la decisión del cliente sobre una cotización previa.
        """
        sol = solicitud_existente or SolicitudEntrada()
        texto_limpio = mensaje.strip()
        texto_lower = texto_limpio.lower()
        entidades_detectadas = {}
        decision_detectada = None

        # 1. Detección de decisiones de cliente
        if esperando_decision or any(k in texto_lower for k in ["acepto", "aceptar", "rechazo", "rechazar", "modificar"]):
            if any(k in texto_lower for k in ["acepto", "aceptar", "de acuerdo", "procedamos", "confirmo", "sí, procedamos", "si procedamos", "me parece bien", "adelante"]):
                decision_detectada = DecisionCliente.ACEPTAR
            elif any(k in texto_lower for k in ["rechazo", "rechazar", "no deseo", "descartar", "cancelar", "no gracias", "muy caro"]):
                decision_detectada = DecisionCliente.RECHAZAR
            elif any(k in texto_lower for k in ["modificar", "cambiar", "otro servicio", "otra opción", "otra opcion", "ajustar"]):
                decision_detectada = DecisionCliente.MODIFICAR

        # 2. Extracción de Teléfono (9 dígitos peruanos o 9-15 números)
        tel_match = re.search(r"\b(9\d{8})\b", texto_limpio) or re.search(r"\b(\d{9,15})\b", texto_limpio)
        if tel_match:
            nuevo_tel = tel_match.group(1)
            sol.telefono = nuevo_tel
            entidades_detectadas["telefono"] = nuevo_tel

        # 3. Extracción de Fecha (formatos AAAA-MM-DD o DD/MM/AAAA o '20 de noviembre')
        fecha_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", texto_limpio)
        if fecha_match:
            nueva_fecha = fecha_match.group(1)
            sol.fecha_servicio = nueva_fecha
            entidades_detectadas["fecha_servicio"] = nueva_fecha
        else:
            fecha_barra = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", texto_limpio)
            if fecha_barra:
                d, m, y = fecha_barra.groups()
                nueva_fecha = f"{y}-{int(m):02d}-{int(d):02d}"
                sol.fecha_servicio = nueva_fecha
                entidades_detectadas["fecha_servicio"] = nueva_fecha
            else:
                meses = {
                    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
                    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
                    "septiembre": "09", "setiembre": "09", "octubre": "10",
                    "noviembre": "11", "diciembre": "12",
                }
                for m_nom, m_num in meses.items():
                    patron_mes = rf"\b(\d{{1,2}})\s+de\s+{m_nom}(?:\s+de\s+(\d{{4}}))?\b"
                    m_match = re.search(patron_mes, texto_lower)
                    if m_match:
                        dia = int(m_match.group(1))
                        anio = m_match.group(2) or str(datetime.now().year)
                        nueva_fecha = f"{anio}-{m_num}-{dia:02d}"
                        sol.fecha_servicio = nueva_fecha
                        entidades_detectadas["fecha_servicio"] = nueva_fecha
                        break

        # 4. Extracción de Servicio Funerario
        if any(w in texto_lower for w in ["cremac", "inciner", "ceniza", "urna"]):
            sol.servicio_solicitado = "Cremación"
            entidades_detectadas["servicio_solicitado"] = "Cremación"
        elif any(w in texto_lower for w in ["velator", "velorio", "sala de velaci", "capilla"]):
            sol.servicio_solicitado = "Velatorio"
            entidades_detectadas["servicio_solicitado"] = "Velatorio"
        elif any(w in texto_lower for w in ["traslado", "carroza", "transporte"]):
            sol.servicio_solicitado = "Traslado"
            entidades_detectadas["servicio_solicitado"] = "Traslado"
        elif any(w in texto_lower for w in ["sepelio", "entierro", "funerario", "ataud", "ataúd", "inhumaci"]):
            sol.servicio_solicitado = "Sepelio"
            entidades_detectadas["servicio_solicitado"] = "Sepelio"

        # 5. Extracción de Nombre del Deudo
        nombre_match = re.search(
            r"(?:me llamo|mi nombre es|soy|nombre:\s*|deudo:\s*|familiar:\s*)([A-Za-zÁÉÍÓÚáéíóúñÑ ]{3,40})",
            texto_limpio,
            re.IGNORECASE,
        )
        if nombre_match:
            candidato_nombre = nombre_match.group(1).strip()
            # Limpiar posibles palabras pegadas
            sol.nombre_cliente = candidato_nombre
            entidades_detectadas["nombre_cliente"] = candidato_nombre
        elif not sol.nombre_cliente:
            # Si el usuario solo escribió su nombre (2 a 4 palabras, solo letras, sin verbos comunes de petición)
            palabras = texto_limpio.split()
            if 1 <= len(palabras) <= 4 and all(re.match(r"^[A-Za-zÁÉÍÓÚáéíóúñÑ.]+$", p) for p in palabras):
                if not any(w in texto_lower for w in ["hola", "buenas", "cotizacion", "servicio", "gracias", "precio"]):
                    sol.nombre_cliente = texto_limpio
                    entidades_detectadas["nombre_cliente"] = texto_limpio

        return sol, decision_detectada, entidades_detectadas

    # =========================================================================
    # VALIDACIÓN DEL CONTRATO DE ENTRADA (F_Validar / F_GW_Datos)
    # =========================================================================

    def validar_informacion(self, solicitud: SolicitudEntrada) -> ValidacionResultado:
        """
        Evalúa el Contrato de Entrada (Lab 02) replicando la compuerta F_GW_Datos:
        1. nombre_cliente: obligatorio, 3 a 100 caracteres.
        2. telefono: obligatorio, 9 a 15 caracteres numéricos.
        3. servicio_solicitado: obligatorio, debe coincidir con catálogo ('Sepelio'|'Cremación'|'Velatorio'|'Traslado').
        4. fecha_servicio: obligatorio, formato AAAA-MM-DD y fecha no pasada.
        """
        faltantes = []
        errores = []

        # 1. Validación de nombre_cliente
        nombre = solicitud.nombre_cliente
        if not nombre or not str(nombre).strip():
            faltantes.append("Nombre completo del deudo o solicitante")
            errores.append("Campo 'nombre_cliente' es obligatorio.")
        elif len(str(nombre).strip()) < 3 or len(str(nombre).strip()) > 100:
            errores.append("El nombre debe contener entre 3 y 100 caracteres.")

        # 2. Validación de telefono
        tel = str(solicitud.telefono or "").strip()
        tel_limpio = re.sub(r"[^\d]", "", tel)
        if not tel_limpio:
            faltantes.append("Número de teléfono de contacto (9 a 15 dígitos)")
            errores.append("Campo 'telefono' es obligatorio.")
        elif len(tel_limpio) < 9 or len(tel_limpio) > 15:
            errores.append("El teléfono debe tener entre 9 y 15 dígitos numéricos.")

        # 3. Validación de servicio_solicitado
        serv = str(solicitud.servicio_solicitado or "").strip()
        if not serv or serv.lower() == "none":
            faltantes.append("Tipo de servicio funerario requerido (Sepelio, Cremación, Velatorio o Traslado)")
            errores.append("Campo 'servicio_solicitado' es obligatorio.")

        # 4. Validación de fecha_servicio
        fecha_str = str(solicitud.fecha_servicio or "").strip()
        if not fecha_str or fecha_str.lower() == "none":
            faltantes.append("Fecha estimada en que se requerirá el servicio (Formato AAAA-MM-DD)")
            errores.append("Campo 'fecha_servicio' es obligatorio.")
        else:
            try:
                datetime.strptime(fecha_str, "%Y-%m-%d")
            except ValueError:
                errores.append("El formato de fecha_servicio debe ser válido (AAAA-MM-DD).")

        es_valida = (len(faltantes) == 0 and len(errores) == 0)

        # Si faltan datos, redactar mensaje empático de solicitud
        mensaje_empatico = None
        if not es_valida:
            mensaje_empatico = self.generar_mensaje_datos_faltantes(
                nombre_cliente=nombre or "estimada familia",
                faltantes=faltantes,
                errores=errores,
            )

        return ValidacionResultado(
            es_valida=es_valida,
            campos_faltantes=faltantes,
            errores_detalle=errores,
            mensaje_empatico=mensaje_empatico,
            solicitud_normalizada=solicitud,
        )

    # =========================================================================
    # MENSAJE EMPÁTICO DE DATOS FALTANTES (F_SolicitarDatos)
    # =========================================================================

    def generar_mensaje_datos_faltantes(
        self, nombre_cliente: str, faltantes: List[str], errores: List[str]
    ) -> str:
        """
        Redacta una respuesta empática y respetuosa para solicitar datos faltantes (F_SolicitarDatos).
        Utiliza el protocolo de acompañamiento en duelo de Funeraria Velazquex.
        """
        if nombre_cliente and str(nombre_cliente).strip().lower() not in ["estimada familia", "none", ""]:
            encabezado = f"Estimada familia {str(nombre_cliente).strip()}, en nombre de Funeraria Velazquex le extendemos nuestras más sentidas condolencias y solidaridad en este momento tan doloroso."
        else:
            encabezado = "Estimada familia, en nombre de Funeraria Velazquex le extendemos nuestras más sentidas condolencias y solidaridad en este momento tan doloroso."
        items_texto = "\n".join([f"  • {item}" for item in faltantes])
        cuerpo = PLANTILLAS_EMPATIA["datos_faltantes"].format(
            lista_faltantes=items_texto
        )

        mensaje_completo = (
            f"🕊️ *FUNERARIA VELAZQUEX · ATENCIÓN Y ACOMPAÑAMIENTO*\n\n"
            f"{encabezado}\n\n"
            f"{cuerpo}\n\n"
            f"_(Dispone de {TIMEOUT_DIAS_DATOS} días para remitir estos datos y mantener activa su solicitud)._"
        )
        return mensaje_completo

    # =========================================================================
    # REVISIÓN Y FORMATEO DE COTIZACIÓN PARA ENVÍO (F_RevisarCotizacion / F_EnviarCotizacion)
    # =========================================================================

    def formatear_cotizacion_para_cliente(self, cotizacion: Cotizacion) -> str:
        """
        Prepara el mensaje formal y empático que se comunica al cliente (F_EnviarCotizacion).
        Incluye detalles de servicios, precios en Soles, avisos de alternativa y validez.
        """
        nombre = cotizacion.nombre_cliente
        encabezado = PLANTILLAS_EMPATIA["condolencias"].format(nombre_cliente=nombre)
        introduccion = PLANTILLAS_EMPATIA["cotizacion_disponible"]

        # Formateo de los ítems cotizados
        filas_items = []
        for i, item in enumerate(cotizacion.items, 1):
            tag_alt = " *(Alternativa asignada por disponibilidad)*" if item.es_alternativa else ""
            filas_items.append(
                f"{i}. *{item.concepto}*{tag_alt}\n"
                f"   Detalle: {item.descripcion}\n"
                f"   Importe: {MONEDA_SIMBOLO} {item.precio_unitario:,.2f}"
            )
        tabla_items = "\n\n".join(filas_items)

        # Sección de alternativa si aplicó
        seccion_alt = ""
        if cotizacion.alternativa_aplicada:
            seccion_alt = (
                f"\n\n⚠️ *Nota sobre disponibilidad:*\n"
                f"{cotizacion.detalle_alternativa}\n"
            )

        mensaje = (
            f"🕊️ *FUNERARIA VELAZQUEX · PROPUESTA DE COTIZACIÓN DIGITAL*\n"
            f"N.° Cotización: *{cotizacion.codigo_cotizacion}* | Fecha: {cotizacion.fecha_emision.strftime('%d/%m/%Y %H:%M')}\n\n"
            f"{encabezado}\n\n"
            f"{introduccion}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*RESUMEN DE SERVICIOS PREPARADOS:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{tabla_items}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Subtotal: {MONEDA_SIMBOLO} {cotizacion.subtotal_pen:,.2f}\n"
            f"I.G.V. (18%): {MONEDA_SIMBOLO} {cotizacion.igv_pen:,.2f}\n"
            f"*IMPORTE TOTAL: {MONEDA_SIMBOLO} {cotizacion.total_pen:,.2f}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{seccion_alt}"
            f"📌 *Validez de la oferta:* {cotizacion.fecha_validez_dias} días calendario.\n"
            f"Puede responder este mensaje indicando si desea *Aceptar*, *Modificar* algún detalle o *Rechazar* la propuesta."
        )
        return mensaje

    # =========================================================================
    # RECORDATORIO DE SEGUIMIENTO EMPÁTICO (F_Recordatorio)
    # =========================================================================

    def generar_mensaje_recordatorio(self, cotizacion: Cotizacion) -> str:
        """
        Genera el mensaje respetuoso de recordatorio cuando han pasado 2 días
        sin respuesta de decisión (F_TimeoutDecision -> F_Recordatorio).
        """
        cuerpo = PLANTILLAS_EMPATIA["recordatorio_seguimiento"].format(
            nombre_cliente=cotizacion.nombre_cliente,
            codigo_cotizacion=cotizacion.codigo_cotizacion,
        )
        mensaje = (
            f"🕊️ *FUNERARIA VELAZQUEX · RECORDATORIO DE SEGUIMIENTO*\n\n"
            f"{cuerpo}\n\n"
            f"• Servicio cotizado: {cotizacion.servicio_solicitado} ({MONEDA_SIMBOLO} {cotizacion.total_pen:,.2f})\n"
            f"• Si requiere modificar ítems o facilidades de pago, avísenos con total libertad.\n"
            f"_(Dispone de {TIMEOUT_DIAS_FINAL} días adicionales antes de archivar la cotización)._"
        )
        return mensaje

    # =========================================================================
    # EVALUACIÓN DE TEMPORIZADORES (Timeout P2D)
    # =========================================================================

    def evaluar_timeout_datos(self, dias_espera: float) -> bool:
        """
        Evalúa si la espera de datos excedió el plazo de 2 días (F_TimeoutDatos).
        Retorna True si expiró el plazo.
        """
        return dias_espera >= TIMEOUT_DIAS_DATOS

    def evaluar_timeout_decision(self, dias_espera: float) -> bool:
        """
        Evalúa si la espera de decisión del cliente excedió los 2 días (F_TimeoutDecision).
        Retorna True si venció y debe disparar F_Recordatorio.
        """
        return dias_espera >= TIMEOUT_DIAS_DECISION

    def evaluar_timeout_final(self, dias_espera_post_recordatorio: float) -> bool:
        """
        Evalúa si tras el recordatorio transcurrieron 2 días sin respuesta (F_TimeoutFinal).
        Retorna True si debe registrarse como 'Sin respuesta' y archivarse.
        """
        return dias_espera_post_recordatorio >= TIMEOUT_DIAS_FINAL
