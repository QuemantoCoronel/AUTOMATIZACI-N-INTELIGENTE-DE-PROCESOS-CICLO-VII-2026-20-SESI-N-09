"""
Servidor Web de Chat Interactivo con Inspector BPMN en Tiempo Real
Funeraria Velazquex - Sistema Multi-Agente de Cotizaciones Digitales
Construido con la librería estándar de Python (http.server) - Cero dependencias adicionales.
"""

import json
import logging
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

# Configuración de codificación para consola Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from funeraria_velazquex import OrquestadorFlujo, ARCHIVOS_FUNERARIA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AppWeb")

# Instancia global del orquestador
orquestador = OrquestadorFlujo()
SESION_ID_WEB = "web_user"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Funeraria Velazquex · Cotizaciones Digitales Multi-Agente</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #0b1120;
      --card-bg: rgba(30, 41, 59, 0.7);
      --card-border: rgba(255, 255, 255, 0.08);
      --primary: #38bdf8;
      --primary-hover: #0ea5e9;
      --accent: #818cf8;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --chat-bot-bg: #1e293b;
      --chat-user-bg: #0369a1;
      --bpmn-active: #10b981;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Outfit', sans-serif;
      background-color: var(--bg-dark);
      background-image: radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.08) 0px, transparent 50%),
                        radial-gradient(at 100% 100%, rgba(129, 140, 248, 0.08) 0px, transparent 50%);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: rgba(15, 23, 42, 0.8);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--card-border);
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .brand-icon {
      font-size: 1.8rem;
      background: linear-gradient(135deg, #38bdf8, #818cf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .brand h1 { font-size: 1.35rem; font-weight: 700; letter-spacing: -0.02em; }
    .brand p { font-size: 0.75rem; color: var(--text-muted); font-family: 'Inter', sans-serif; }
    .header-actions button {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 0.5rem 1rem;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 500;
      transition: all 0.2s;
    }
    .header-actions button:hover {
      background: rgba(255, 255, 255, 0.1);
      border-color: var(--primary);
    }
    .container {
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 1.5rem;
      padding: 1.5rem 2rem;
      flex: 1;
      max-width: 1600px;
      width: 100%;
      margin: 0 auto;
    }
    @media (max-width: 950px) {
      .container { grid-template-columns: 1fr; }
    }
    .chat-panel {
      background: var(--card-bg);
      backdrop-filter: blur(16px);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      height: calc(100vh - 120px);
    }
    .chat-header {
      padding: 1rem 1.25rem;
      background: rgba(15, 23, 42, 0.5);
      border-bottom: 1px solid var(--card-border);
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .agent-avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: linear-gradient(135deg, #0284c7, #6366f1);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.2rem;
    }
    .agent-info h2 { font-size: 0.95rem; font-weight: 600; }
    .agent-info span { font-size: 0.75rem; color: #34d399; display: flex; align-items: center; gap: 4px; }
    .agent-info span::before {
      content: '';
      width: 6px;
      height: 6px;
      background: #34d399;
      border-radius: 50%;
      display: inline-block;
    }
    .chat-messages {
      flex: 1;
      padding: 1.25rem;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .msg {
      max-width: 82%;
      padding: 0.85rem 1.15rem;
      border-radius: 14px;
      font-size: 0.9rem;
      line-height: 1.5;
      position: relative;
      animation: fadeIn 0.3s ease-out;
      white-space: pre-wrap;
    }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
    .msg-bot {
      align-self: flex-start;
      background: var(--chat-bot-bg);
      border: 1px solid rgba(255, 255, 255, 0.05);
      color: #e2e8f0;
      border-bottom-left-radius: 2px;
    }
    .msg-user {
      align-self: flex-end;
      background: var(--chat-user-bg);
      color: #ffffff;
      border-bottom-right-radius: 2px;
    }
    .msg-time {
      font-size: 0.65rem;
      color: var(--text-muted);
      margin-top: 4px;
      text-align: right;
    }
    .quick-chips {
      padding: 0.5rem 1rem;
      background: rgba(15, 23, 42, 0.4);
      display: flex;
      gap: 0.5rem;
      overflow-x: auto;
      border-top: 1px solid var(--card-border);
    }
    .chip {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      padding: 0.35rem 0.75rem;
      border-radius: 20px;
      font-size: 0.75rem;
      color: #cbd5e1;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }
    .chip:hover {
      background: rgba(56, 189, 248, 0.2);
      border-color: var(--primary);
      color: #ffffff;
    }
    .chat-input-area {
      padding: 1rem;
      background: rgba(15, 23, 42, 0.7);
      border-top: 1px solid var(--card-border);
      display: flex;
      gap: 0.75rem;
    }
    .chat-input-area input {
      flex: 1;
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 0.75rem 1rem;
      color: var(--text-main);
      font-size: 0.9rem;
      outline: none;
      transition: border 0.2s;
    }
    .chat-input-area input:focus {
      border-color: var(--primary);
    }
    .chat-input-area button {
      background: linear-gradient(135deg, var(--primary), var(--accent));
      border: none;
      color: white;
      padding: 0 1.25rem;
      border-radius: 10px;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.2s;
    }
    .chat-input-area button:hover { opacity: 0.9; }
    .inspector-panel {
      background: var(--card-bg);
      backdrop-filter: blur(16px);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      height: calc(100vh - 120px);
    }
    .inspector-header {
      padding: 1rem 1.25rem;
      background: rgba(15, 23, 42, 0.5);
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .inspector-header h2 { font-size: 0.95rem; font-weight: 600; }
    .state-badge {
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid #10b981;
      color: #34d399;
      font-size: 0.7rem;
      padding: 0.2rem 0.6rem;
      border-radius: 20px;
      font-weight: 600;
    }
    .inspector-body {
      flex: 1;
      overflow-y: auto;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }
    .card-section {
      background: rgba(15, 23, 42, 0.4);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1rem;
    }
    .card-section h3 {
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--primary);
      margin-bottom: 0.75rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .entity-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.5rem;
    }
    .entity-item {
      background: rgba(255, 255, 255, 0.03);
      padding: 0.5rem 0.75rem;
      border-radius: 8px;
    }
    .entity-label { font-size: 0.68rem; color: var(--text-muted); }
    .entity-val { font-size: 0.82rem; font-weight: 500; color: #f1f5f9; }
    .bpmn-trace-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      max-height: 250px;
      overflow-y: auto;
      font-family: 'Inter', monospace;
      font-size: 0.72rem;
    }
    .trace-item {
      background: rgba(0, 0, 0, 0.25);
      padding: 0.4rem 0.6rem;
      border-left: 3px solid var(--primary);
      border-radius: 0 4px 4px 0;
      color: #cbd5e1;
      line-height: 1.4;
    }
    .trace-node { color: #38bdf8; font-weight: 600; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="brand-icon">🕊️</div>
      <div>
        <h1>Funeraria Velazquex</h1>
        <p>Sistema Multi-Agente de Cotizaciones Digitales (BPMN TO-BE)</p>
      </div>
    </div>
    <div class="header-actions">
      <button onclick="reiniciarConversacion()">🔄 Nueva Cotización</button>
    </div>
  </header>

  <main class="container">
    <!-- PANEL DE CHAT (FRONT-END / ATENCIÓN AL CLIENTE) -->
    <section class="chat-panel">
      <div class="chat-header">
        <div class="agent-avatar">🕊️</div>
        <div class="agent-info">
          <h2>Agente Front-End · Atención al Cliente</h2>
          <span>En línea · Acompañamiento 24h</span>
        </div>
      </div>

      <div class="chat-messages" id="chatBox">
        <div class="msg msg-bot">
          Buenos días/tardes. En nombre de <strong>Funeraria Velazquex</strong> le extendemos un cálido saludo y estamos a su entera disposición para orientarle en todo lo relativo a servicios funerarios. ¿En qué podemos acompañarle hoy?
          <div class="msg-time">Sistema activo</div>
        </div>
      </div>

      <!-- BOTONES DE PRUEBA RÁPIDA -->
      <div class="quick-chips">
        <div class="chip" onclick="enviarChip('Hola, necesito una cotización para un servicio funerario básico')">1️⃣ 'Hola, necesito cotización básico'</div>
        <div class="chip" onclick="enviarChip('Mi nombre es Juan Pérez, teléfono 987654321 y fecha 2026-11-20')">2️⃣ 'Completar datos: Juan Pérez'</div>
        <div class="chip" onclick="enviarChip('Cremación para el 2026-10-20')">3️⃣ 'Probar indisponibilidad (2026-10-20)'</div>
        <div class="chip" onclick="enviarChip('Acepto la cotización propuesta')">4️⃣ 'Aceptar cotización'</div>
        <div class="chip" onclick="enviarChip('Deseo modificar el servicio')">5️⃣ 'Modificar'</div>
      </div>

      <div class="chat-input-area">
        <input type="text" id="userInput" placeholder="Escriba su mensaje como deudo o familiar..." onkeypress="handleKey(event)">
        <button onclick="enviarMensaje()">Enviar</button>
      </div>
    </section>

    <!-- PANEL DEL INSPECTOR (BACK-END / BPMN Y EXCEL PANDAS) -->
    <section class="inspector-panel">
      <div class="inspector-header">
        <h2>⚙️ Inspector Back-End & Proceso BPMN</h2>
        <span class="state-badge" id="badgeEstado">F_Start: Listo</span>
      </div>

      <div class="inspector-body">
        <!-- Entidades extraídas por Front-End -->
        <div class="card-section">
          <h3>📌 Contrato de Entrada (Datos Extraídos)</h3>
          <div class="entity-grid">
            <div class="entity-item">
              <div class="entity-label">Nombre Deudo</div>
              <div class="entity-val" id="valNombre">-</div>
            </div>
            <div class="entity-item">
              <div class="entity-label">Teléfono</div>
              <div class="entity-val" id="valTelefono">-</div>
            </div>
            <div class="entity-item">
              <div class="entity-label">Servicio Solicitado</div>
              <div class="entity-val" id="valServicio">-</div>
            </div>
            <div class="entity-item">
              <div class="entity-label">Fecha Servicio</div>
              <div class="entity-val" id="valFecha">-</div>
            </div>
          </div>
        </div>

        <!-- Cotización calculada por Back-End -->
        <div class="card-section" id="seccionCotizacion" style="display: none;">
          <h3>💼 Cotización Calculada (DS_Central)</h3>
          <div class="entity-grid">
            <div class="entity-item">
              <div class="entity-label">Código</div>
              <div class="entity-val" id="cotCodigo">-</div>
            </div>
            <div class="entity-item">
              <div class="entity-label">Importe Total (PEN)</div>
              <div class="entity-val" id="cotTotal" style="color: #34d399; font-weight: 700;">-</div>
            </div>
            <div class="entity-item">
              <div class="entity-label">Alternativa Asignada</div>
              <div class="entity-val" id="cotAlternativa">-</div>
            </div>
            <div class="entity-item">
              <div class="entity-label">Validez</div>
              <div class="entity-val">5 días calendario</div>
            </div>
          </div>
        </div>

        <!-- Trazabilidad del BPMN en segundo plano -->
        <div class="card-section" style="flex: 1; display: flex; flex-direction: column;">
          <h3>⚡ Trazas del BPMN TO-BE en Segundo Plano</h3>
          <div class="bpmn-trace-list" id="traceList">
            <div class="trace-item">[Inicio] Orquestador Multi-Agente inicializado y esperando solicitud.</div>
          </div>
        </div>
      </div>
    </section>
  </main>

  <script>
    function agregarMensaje(remitente, texto) {
      const chatBox = document.getElementById('chatBox');
      const div = document.createElement('div');
      div.className = 'msg ' + (remitente === 'usuario' ? 'msg-user' : 'msg-bot');
      div.textContent = texto;

      const time = document.createElement('div');
      time.className = 'msg-time';
      const now = new Date();
      time.textContent = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
      div.appendChild(time);

      chatBox.appendChild(div);
      chatBox.scrollTop = chatBox.scrollHeight;
    }

    function handleKey(e) {
      if (e.key === 'Enter') enviarMensaje();
    }

    function enviarChip(texto) {
      document.getElementById('userInput').value = texto;
      enviarMensaje();
    }

    async function enviarMensaje() {
      const input = document.getElementById('userInput');
      const texto = input.value.trim();
      if (!texto) return;

      input.value = '';
      agregarMensaje('usuario', texto);

      try {
        const resp = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mensaje: texto })
        });
        const data = await resp.json();

        // Respuesta del Agente Front-End
        agregarMensaje('bot', data.mensaje_asistente);

        // Actualizar Inspector Back-End
        if (data.estado_proceso) {
          document.getElementById('badgeEstado').textContent = data.estado_proceso.split(':')[0] || data.estado_proceso;
        }

        if (data.solicitud_actual) {
          document.getElementById('valNombre').textContent = data.solicitud_actual.nombre_cliente || 'Pendiente';
          document.getElementById('valTelefono').textContent = data.solicitud_actual.telefono || 'Pendiente';
          document.getElementById('valServicio').textContent = data.solicitud_actual.servicio_solicitado || 'Pendiente';
          document.getElementById('valFecha').textContent = data.solicitud_actual.fecha_servicio || 'Pendiente';
        }

        if (data.cotizacion) {
          document.getElementById('seccionCotizacion').style.display = 'block';
          document.getElementById('cotCodigo').textContent = data.cotizacion.codigo_cotizacion;
          document.getElementById('cotTotal').textContent = 'S/ ' + Number(data.cotizacion.total_pen).toLocaleString('es-PE', { minimumFractionDigits: 2 });
          document.getElementById('cotAlternativa').textContent = data.cotizacion.alternativa_aplicada ? 'Sí (Por Disponibilidad)' : 'No';
        }

        if (data.trazas_recientes && data.trazas_recientes.length > 0) {
          const traceList = document.getElementById('traceList');
          data.trazas_recientes.forEach(t => {
            const item = document.createElement('div');
            item.className = 'trace-item';
            item.textContent = t;
            traceList.appendChild(item);
          });
          traceList.scrollTop = traceList.scrollHeight;
        }

      } catch (err) {
        agregarMensaje('bot', 'Error de conexión con el Orquestador: ' + err);
      }
    }

    async function reiniciarConversacion() {
      await fetch('/api/reset', { method: 'POST' });
      document.getElementById('chatBox').innerHTML = `
        <div class="msg msg-bot">
          Nueva sesión iniciada. En <strong>Funeraria Velazquex</strong> estamos a su entera disposición. ¿Qué servicio funerario desea consultar?
          <div class="msg-time">Sesión reiniciada</div>
        </div>
      `;
      document.getElementById('badgeEstado').textContent = 'F_Start: Listo';
      document.getElementById('valNombre').textContent = '-';
      document.getElementById('valTelefono').textContent = '-';
      document.getElementById('valServicio').textContent = '-';
      document.getElementById('valFecha').textContent = '-';
      document.getElementById('seccionCotizacion').style.display = 'none';
      document.getElementById('traceList').innerHTML = '<div class="trace-item">[Reinicio] Memoria de sesión restablecida.</div>';
    }
  </script>
</body>
</html>
"""


class FunerariaHTTPHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self._set_headers(200, "text/html")
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif parsed.path == "/api/estado":
            sesion = orquestador._sesiones.get(SESION_ID_WEB, {})
            self._set_headers(200)
            self.wfile.write(json.dumps(sesion, default=str, ensure_ascii=False).encode("utf-8"))
        else:
            self._set_headers(404, "text/plain")
            self.wfile.write(b"Ruta no encontrada")

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if parsed.path == "/api/chat":
            try:
                data = json.loads(body.decode("utf-8"))
                mensaje = data.get("mensaje", "")
                resultado = orquestador.procesar_mensaje_conversacional(
                    mensaje_texto=mensaje,
                    sesion_id=SESION_ID_WEB,
                )
                self._set_headers(200)
                self.wfile.write(json.dumps(resultado, default=str, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                logger.error(f"Error procesando chat: {e}")
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/reset":
            orquestador.reiniciar_sesion(SESION_ID_WEB)
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "reset_ok"}).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(b"Endpoint no encontrado")


def run_server(port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, FunerariaHTTPHandler)
    print(f"\n========================================================================")
    print(f"  🕊️  FUNERARIA VELAZQUEX · SERVIDOR DE COTIZACIONES DIGITALES")
    print(f"  Aplicación Web Interactiva disponible en: http://localhost:{port}")
    print(f"========================================================================\n")
    logger.info(f"Servidor iniciado en http://localhost:{port}. Presiona Ctrl+C para detener.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo servidor...")
        httpd.server_close()


if __name__ == "__main__":
    puerto = 8000
    if len(sys.argv) > 1:
        try:
            puerto = int(sys.argv[1])
        except ValueError:
            pass
    run_server(puerto)
