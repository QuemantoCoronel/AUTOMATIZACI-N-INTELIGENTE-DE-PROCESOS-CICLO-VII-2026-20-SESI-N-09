"""
Servicio de Gestión y Consulta de Archivos Excel con pandas
Funeraria Velazquex - Acceso a Catálogos, Disponibilidad y Repositorios
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd

from .config import (
    EXCEL_LAB_01_PATH,
    EXCEL_LAB_02_PATH,
    REPOSITORIO_CENTRAL_PATH,
    COLA_ERRORES_PATH,
    MAX_REINTENTOS_SISTEMA,
    ESPERA_REINTENTO_SEGUNDOS,
)
from .models import (
    ServicioCatalogo,
    DisponibilidadResultado,
    RegistroErrorCola,
    EstadoProceso,
    Cotizacion,
)

logger = logging.getLogger("ExcelService")


class ExcelService:
    """
    Gestiona la lectura e interrogación directa de los archivos Excel
    'Instrumentos_Laboratorio 01 - Grupo 01.xlsx' y
    'Instrumentos_Laboratorio_02 - Grupo 01.xlsx' mediante pandas.
    """

    def __init__(
        self,
        excel_lab01: Path = EXCEL_LAB_01_PATH,
        excel_lab02: Path = EXCEL_LAB_02_PATH,
        repo_central: Path = REPOSITORIO_CENTRAL_PATH,
        cola_errores: Path = COLA_ERRORES_PATH,
    ):
        self.excel_lab01 = Path(excel_lab01)
        self.excel_lab02 = Path(excel_lab02)
        self.repo_central = Path(repo_central)
        self.cola_errores = Path(cola_errores)

        # Cargas iniciales en memoria
        self._df_catalogo: Optional[pd.DataFrame] = None
        self._df_disponibilidad: Optional[pd.DataFrame] = None
        self._df_contrato: Optional[pd.DataFrame] = None
        self._df_errores: Optional[pd.DataFrame] = None
        self._df_linea_base: Optional[pd.DataFrame] = None

        self._inicializar()

    def _inicializar(self):
        """Carga y valida la existencia de tablas en los archivos de Excel"""
        self.recargar_tablas()
        self._asegurar_cola_errores()
        self._asegurar_repositorio_central()

    def recargar_tablas(self):
        """Carga DataFrames de pandas desde los archivos Excel con manejo de reintentos"""
        intentos = 0
        while intentos < MAX_REINTENTOS_SISTEMA:
            try:
                # 1. Cargar Contrato de entrada y Catálogo de errores desde Lab 02
                if self.excel_lab02.exists():
                    self._df_contrato = pd.read_excel(
                        self.excel_lab02, sheet_name="Contrato de entrada", skiprows=3
                    )
                    self._df_errores = pd.read_excel(
                        self.excel_lab02, sheet_name="Catalogo de errores", skiprows=3
                    )
                    
                    # Cargar Catálogo de servicios
                    self._df_catalogo = pd.read_excel(
                        self.excel_lab02, sheet_name="Catalogo_Servicios"
                    )
                    
                    # Cargar Disponibilidad de servicios
                    self._df_disponibilidad = pd.read_excel(
                        self.excel_lab02, sheet_name="Disponibilidad"
                    )
                    
                # 2. Cargar Línea base de Lab 01 para analítica y observabilidad
                if self.excel_lab01.exists():
                    self._df_linea_base = pd.read_excel(
                        self.excel_lab01, sheet_name="Linea base", skiprows=3
                    )
                
                logger.info("Tablas de Excel cargadas exitosamente con pandas.")
                return
            except Exception as e:
                intentos += 1
                logger.warning(
                    f"Intento {intentos}/{MAX_REINTENTOS_SISTEMA} fallido al leer Excel: {e}"
                )
                if intentos >= MAX_REINTENTOS_SISTEMA:
                    logger.error("No se pudo acceder al registro de servicios (Error de sistema).")
                    raise IOError(f"Error crítico al acceder a los archivos Excel: {e}")

    # =========================================================================
    # CONSULTAS DE CATÁLOGO Y DISPONIBILIDAD (Back-End)
    # =========================================================================

    def obtener_servicios_permitidos_contrato(self) -> List[str]:
        """
        Extrae la lista de servicios válidos del Contrato de Entrada mediante pandas.
        Valores: 'Sepelio', 'Cremación', 'Velatorio', 'Traslado'
        """
        if self._df_contrato is None:
            return ["Sepelio", "Cremación", "Velatorio", "Traslado"]
        
        fila_servicio = self._df_contrato[
            self._df_contrato["Campo"].astype(str).str.strip() == "servicio_solicitado"
        ]
        if not fila_servicio.empty:
            restriccion = str(fila_servicio["Restricción / rango"].values[0])
            servicios = [s.strip() for s in restriccion.split("|")]
            return servicios
        return ["Sepelio", "Cremación", "Velatorio", "Traslado"]

    def normalizar_nombre_servicio(self, servicio_solicitado: str) -> str:
        """
        Maneja sinónimos según la nota de negocio del Excel (ej. Cremación = Incineración)
        """
        s = servicio_solicitado.strip().capitalize()
        if "incinerac" in s.lower():
            return "Cremación"
        if "cremac" in s.lower():
            return "Cremación"
        if "sepelio" in s.lower() or "entierro" in s.lower():
            return "Sepelio"
        if "velatorio" in s.lower() or "velacion" in s.lower() or "velación" in s.lower():
            return "Velatorio"
        if "traslado" in s.lower() or "carroza" in s.lower():
            return "Traslado"
        return s

    def consultar_catalogo(self, servicio_solicitado: str) -> Tuple[bool, Optional[ServicioCatalogo], str]:
        """
        Busca el servicio en la tabla 'Catalogo_Servicios' de Excel usando filtros de pandas.
        Retorna: (encontrado: bool, item: Optional[ServicioCatalogo], mensaje: str)
        """
        categoria = self.normalizar_nombre_servicio(servicio_solicitado)
        
        # Validación con pandas
        filtro = self._df_catalogo["categoria"].str.strip().str.lower() == categoria.lower()
        df_encontrados = self._df_catalogo[filtro]

        if df_encontrados.empty:
            # Error previsible 1 del catálogo de errores: "El servicio solicitado no existe en el catálogo"
            return (
                False,
                None,
                f"El servicio '{servicio_solicitado}' no pertenece al catálogo disponible de la funeraria.",
            )

        # Seleccionamos el servicio principal de la categoría (el primer paquete estándar)
        fila = df_encontrados.iloc[0]
        item = ServicioCatalogo(
            codigo_servicio=str(fila["codigo_servicio"]),
            categoria=str(fila["categoria"]),
            nombre_servicio=str(fila["nombre_servicio"]),
            descripcion=str(fila["descripcion"]),
            precio_base_pen=float(fila["precio_base_pen"]),
            disponible_por_defecto=str(fila["disponible_por_defecto"]),
            codigo_alternativa=str(fila["codigo_alternativa"]) if pd.notna(fila["codigo_alternativa"]) else None,
            nombre_alternativa=str(fila["nombre_alternativa"]) if pd.notna(fila["nombre_alternativa"]) else None,
            motivo_alternativa=str(fila["motivo_alternativa"]) if pd.notna(fila["motivo_alternativa"]) else None,
        )
        return (True, item, "Servicio localizado exitosamente en el catálogo.")

    def verificar_disponibilidad(
        self, item: ServicioCatalogo, fecha_servicio: str
    ) -> DisponibilidadResultado:
        """
        Interroga la tabla 'Disponibilidad' en Excel con pandas para la fecha requerida.
        Si no hay disponibilidad, busca y asigna la alternativa configurada en la tabla.
        """
        # 1. Filtrar por código y fecha específica en pandas
        filtro_fecha = (
            (self._df_disponibilidad["codigo_servicio"] == item.codigo_servicio) &
            (self._df_disponibilidad["fecha_servicio"].astype(str) == str(fecha_servicio))
        )
        df_fecha = self._df_disponibilidad[filtro_fecha]

        # 2. Si no hay registro para la fecha exacta, consultar la regla general wildcard ('*')
        if df_fecha.empty:
            filtro_gen = (
                (self._df_disponibilidad["codigo_servicio"] == item.codigo_servicio) &
                (self._df_disponibilidad["fecha_servicio"].astype(str) == "*")
            )
            df_fecha = self._df_disponibilidad[filtro_gen]

        disponible = True
        obs = "Disponible con normalidad."
        capacidad = 1
        cupos = 0

        if not df_fecha.empty:
            fila = df_fecha.iloc[0]
            val_disp = str(fila["disponible"]).strip().lower()
            disponible = val_disp in ["sí", "si", "true", "1", "yes"]
            obs = str(fila.get("observaciones", ""))
            capacidad = int(fila.get("capacidad_total", 1))
            cupos = int(fila.get("cupos_ocupados", 0))

        # Si está disponible, retornamos resultado favorable
        if disponible:
            return DisponibilidadResultado(
                codigo_servicio=item.codigo_servicio,
                fecha_servicio=fecha_servicio,
                disponible=True,
                capacidad_total=capacidad,
                cupos_ocupados=cupos,
                observaciones=obs,
                tiene_alternativa=False,
            )

        # Si NO está disponible: Replicar compuerta F_GW_Disponible -> No -> F_DefinirAlternativa
        servicio_alt = None
        motivo_alt = item.motivo_alternativa or obs or "Capacidad operativa colmada para la fecha."

        if item.codigo_alternativa:
            # Buscar el ítem alternativo en el catálogo
            filtro_alt = self._df_catalogo["codigo_servicio"] == item.codigo_alternativa
            df_alt = self._df_catalogo[filtro_alt]
            if not df_alt.empty:
                fila_alt = df_alt.iloc[0]
                servicio_alt = ServicioCatalogo(
                    codigo_servicio=str(fila_alt["codigo_servicio"]),
                    categoria=str(fila_alt["categoria"]),
                    nombre_servicio=str(fila_alt["nombre_servicio"]),
                    descripcion=str(fila_alt["descripcion"]),
                    precio_base_pen=float(fila_alt["precio_base_pen"]),
                    disponible_por_defecto=str(fila_alt["disponible_por_defecto"]),
                )

        return DisponibilidadResultado(
            codigo_servicio=item.codigo_servicio,
            fecha_servicio=fecha_servicio,
            disponible=False,
            capacidad_total=capacidad,
            cupos_ocupados=cupos,
            observaciones=obs,
            tiene_alternativa=(servicio_alt is not None),
            servicio_alternativo=servicio_alt,
            motivo_alternativa=motivo_alt,
        )

    # =========================================================================
    # REPOSITORIO CENTRAL Y REGISTROS (DataStore_Central)
    # =========================================================================

    def _asegurar_repositorio_central(self):
        """Crea el archivo Excel de repositorio central si no existe"""
        if not self.repo_central.exists():
            self.repo_central.parent.mkdir(parents=True, exist_ok=True)
            columnas = [
                "id_solicitud", "codigo_cotizacion", "clave_idempotencia",
                "nombre_cliente", "telefono", "servicio_solicitado",
                "fecha_servicio", "tipo_cliente", "estado_actual",
                "total_pen", "alternativa_aplicada", "fecha_registro", "fecha_actualizacion"
            ]
            df = pd.DataFrame(columns=columnas)
            df.to_excel(self.repo_central, index=False, sheet_name="Solicitudes_Central")
            logger.info(f"Repositorio central creado en {self.repo_central}")

    def guardar_en_repositorio_central(self, datos: Dict[str, Any]):
        """
        Registra o actualiza un caso en el Repositorio Central (DS_Central)
        usando pandas para leer y sincronizar.
        """
        try:
            df = pd.read_excel(self.repo_central, sheet_name="Solicitudes_Central")
        except Exception:
            self._asegurar_repositorio_central()
            df = pd.read_excel(self.repo_central, sheet_name="Solicitudes_Central")

        id_solicitud = datos.get("id_solicitud")
        datos["fecha_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if "id_solicitud" in df.columns and (df["id_solicitud"] == id_solicitud).any():
            # Actualización
            idx = df[df["id_solicitud"] == id_solicitud].index[0]
            for col, val in datos.items():
                if col not in df.columns:
                    df[col] = None
                df[col] = df[col].astype(object)
                df.at[idx, col] = val
        else:
            # Nuevo registro
            datos["fecha_registro"] = datos.get("fecha_registro", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            nueva_fila = pd.DataFrame([datos])
            if df.empty or len(df.dropna(how='all')) == 0:
                df = nueva_fila
            else:
                df = pd.concat([df, nueva_fila], ignore_index=True)

        df.to_excel(self.repo_central, index=False, sheet_name="Solicitudes_Central")

    def consultar_solicitud_por_idempotencia(self, clave_idempotencia: str) -> Optional[Dict[str, Any]]:
        """
        Verifica en el repositorio central si ya existe una solicitud con la misma clave de idempotencia
        (Prueba P2 de idempotencia en Lab 02).
        """
        if not self.repo_central.exists():
            return None
        try:
            df = pd.read_excel(self.repo_central, sheet_name="Solicitudes_Central")
            if "clave_idempotencia" in df.columns:
                coincidencias = df[df["clave_idempotencia"] == clave_idempotencia]
                if not coincidencias.empty:
                    return coincidencias.iloc[0].to_dict()
        except Exception as e:
            logger.error(f"Error al verificar idempotencia: {e}")
        return None

    # =========================================================================
    # COLA DE FALLIDOS (Dead Letter Queue - Requisito E2)
    # =========================================================================

    def _asegurar_cola_errores(self):
        """Inicializa el archivo JSON de la cola de fallidos si no existe"""
        if not self.cola_errores.exists():
            self.cola_errores.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cola_errores, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)

    def registrar_cola_errores(self, registro: RegistroErrorCola):
        """
        Registra el error en la cola de fallidos conservando los 6 campos mínimos
        declarados en el Laboratorio 02:
        [id_caso, timestamp, error, clase_error, carga_original, reintentos]
        """
        self._asegurar_cola_errores()
        try:
            with open(self.cola_errores, "r", encoding="utf-8") as f:
                cola = json.load(f)
        except Exception:
            cola = []

        cola.append(registro.model_dump())
        with open(self.cola_errores, "w", encoding="utf-8") as f:
            json.dump(cola, f, indent=2, ensure_ascii=False)
        logger.warning(
            f"Caso {registro.id_caso} derivado a Cola de Fallidos: {registro.error} (Clase: {registro.clase_error})"
        )

    # =========================================================================
    # LECTURA DE LÍNEA BASE (Laboratorio 01 - Analítica y Caso de Negocio)
    # =========================================================================

    def obtener_resumen_linea_base(self) -> Dict[str, Any]:
        """
        Lee directamente la hoja 'Linea base' de Lab 01 para contrastar
        el tiempo y costo manual frente a la automatización digital.
        """
        resumen = {
            "volumen_mensual": 80.0,
            "tiempo_ciclo_mediana_h": 0.83,
            "tiempo_ciclo_max_h": 14.83,
            "trabajo_efectivo_min": 19.4,
            "costo_horario_soles": 11.33,
            "costo_unitario_caso_soles": 3.66,
            "tasa_reproceso": 0.25,
        }
        if self._df_linea_base is not None and not self._df_linea_base.empty:
            try:
                for _, row in self._df_linea_base.iterrows():
                    mag = str(row.get("Magnitud", "")).strip().lower()
                    val = row.get("Valor")
                    if pd.notna(val):
                        if "volumen mensual" in mag:
                            resumen["volumen_mensual"] = float(val)
                        elif "mediana" in mag:
                            resumen["tiempo_ciclo_mediana_h"] = float(val)
                        elif "máximo" in mag or "maximo" in mag:
                            resumen["tiempo_ciclo_max_h"] = float(val)
                        elif "trabajo efectivo" in mag:
                            resumen["trabajo_efectivo_min"] = float(val)
                        elif "costo horario" in mag:
                            resumen["costo_horario_soles"] = float(val)
                        elif "costo unitario" in mag:
                            resumen["costo_unitario_caso_soles"] = float(val)
            except Exception as e:
                logger.warning(f"Error procesando línea base: {e}")
        return resumen
