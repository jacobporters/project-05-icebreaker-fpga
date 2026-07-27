"""
Sensor Data Logger — Live Dashboard
====================================
Run:  python3 dashboard.py
Open: http://localhost:5000

Receives UDP packets from ESP32, serves a live dashboard with:
  - Real-time plots (temperature, voltage, current, power)
  - Live numeric readouts
  - CSV file browser + download (fetched from ESP32 SD card)
  - FPGA message popup (via ESP32 UART bridge from iCEBreaker)

UDP packet formats (from ESP32):
  Sensor data:   time_ms,temp_C,bus_V,current_mA,power_mW
  FPGA control:  MSG_START | MSG_TEXT:<text> | MSG_END
"""

import socket
import threading
import csv
import io
import json
import time
import requests
from datetime import datetime
from collections import deque
from flask import Flask, jsonify, render_template_string, Response, request

# ── Config ───────────────────────────────────
UDP_PORT       = 5005
MAX_POINTS     = 120          # 2 minutes of history at 1 Hz
ESP32_IP       = None         # auto-detected from first UDP packet
ESP32_HTTP_PORT = 80

# ── Shared data (thread-safe deque) ─────────────────────────
lock   = threading.Lock()
data   = {
    "timestamps": deque(maxlen=MAX_POINTS),
    "temp_C":     deque(maxlen=MAX_POINTS),
    "bus_V":      deque(maxlen=MAX_POINTS),
    "current_mA": deque(maxlen=MAX_POINTS),
    "power_mW":   deque(maxlen=MAX_POINTS),
    "last_update": None,
    "packet_count": 0,
    "fpga_message_state": "idle",   # idle | waiting | showing
    "fpga_message_text":  None,
}

# ── UDP receiver thread ──────────────────────────────────
def udp_receiver():
    global ESP32_IP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', UDP_PORT))
    sock.settimeout(1.0)
    print(f"[UDP] Listening on port {UDP_PORT}...")

    while True:
        try:
            raw, addr = sock.recvfrom(256)
            if ESP32_IP is None:
                ESP32_IP = addr[0]
                print(f"[UDP] ESP32 detected at {ESP32_IP}")

            text = raw.decode(errors='ignore').strip()

            # ── FPGA message override packets ──
            if text == "MSG_START":
                with lock:
                    data["fpga_message_state"] = "waiting"
                    data["fpga_message_text"]  = None
                continue
            elif text.startswith("MSG_TEXT:"):
                with lock:
                    data["fpga_message_state"] = "showing"
                    data["fpga_message_text"]  = text[len("MSG_TEXT:"):]
                continue
            elif text == "MSG_END":
                with lock:
                    data["fpga_message_state"] = "idle"
                    data["fpga_message_text"]  = None
                continue

            parts = text.split(',')
            if len(parts) != 5:
                continue

            ts_ms, temp, volts, amps, watts = [float(p) for p in parts]
            wall_time = datetime.now().strftime("%H:%M:%S")

            with lock:
                data["timestamps"].append(wall_time)
                data["temp_C"].append(temp if temp > -998 else None)
                data["bus_V"].append(volts)
                data["current_mA"].append(amps)
                data["power_mW"].append(watts)
                data["last_update"] = wall_time
                data["packet_count"] += 1

        except socket.timeout:
            continue
        except Exception as e:
            print(f"[UDP] Error: {e}")

# ── Flask app ──────────────────────────────────────
app = Flask(__name__)
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def index():
    return render_template_string(HTML_DASHBOARD)

@app.route('/api/data')
def api_data():
    with lock:
        return jsonify({
            "timestamps":  list(data["timestamps"]),
            "temp_C":      list(data["temp_C"]),
            "bus_V":       list(data["bus_V"]),
            "current_mA":  list(data["current_mA"]),
            "power_mW":    list(data["power_mW"]),
            "last_update": data["last_update"],
            "packet_count": data["packet_count"],
            "esp32_ip":    ESP32_IP,
            "fpga_message_state": data["fpga_message_state"],
            "fpga_message_text":  data["fpga_message_text"],
        })

@app.route('/api/files')
def api_files():
    if not ESP32_IP:
        return jsonify({"error": "ESP32 not detected yet"}), 503
    try:
        r = requests.get(f"http://{ESP32_IP}/files", timeout=3)
        return jsonify(json.loads(r.text))
    except Exception as e:
        return jsonify({"error": str(e)}), 503

@app.route('/api/download/<filename>')
def api_download(filename):
    """Proxy SD card file download from ESP32."""
    if not ESP32_IP:
        return "ESP32 not detected", 503
    # Safety: only allow CSV filenames, no path traversal
    if '/' in filename or '\\' in filename or not filename.upper().endswith('.CSV'):
        return "Invalid filename", 400
    try:
        r = requests.get(f"http://{ESP32_IP}/sd/{filename}", timeout=10, stream=True)
        return Response(
            r.iter_content(chunk_size=1024),
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv",
            }
        )
    except Exception as e:
        return f"Download failed: {e}", 503

# ── Dashboard HTML ──────────────────────────────────────
HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sensor Logger</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg:        #0d1117;
    --surface:   #161b22;
    --border:    #21262d;
    --text:      #e6edf3;
    --muted:     #7d8590;
    --accent:    #58a6ff;
    --green:     #3fb950;
    --yellow:    #d29922;
    --orange:    #f0883e;
    --red:       #f85149;
    --font-mono: "SF Mono", "Fira Code", monospace;
    --font-ui:   -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--font-ui);
    min-height: 100vh;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
    position: sticky;
    top: 0;
    z-index: 10;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 0.02em;
  }

  .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--muted);
    transition: background 0.3s;
  }
  .dot.live { background: var(--green); box-shadow: 0 0 6px var(--green); }

  .status {
    font-size: 12px;
    color: var(--muted);
    font-family: var(--font-mono);
  }

  main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
    display: grid;
    gap: 20px;
  }

  /* ── Readout cards ── */
  .readouts {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 20px;
  }

  .card-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 8px;
  }

  .card-value {
    font-size: 32px;
    font-family: var(--font-mono);
    font-weight: 300;
    letter-spacing: -0.02em;
    line-height: 1;
  }

  .card-unit {
    font-size: 14px;
    color: var(--muted);
    margin-left: 4px;
  }

  .card.temp  .card-value { color: var(--orange); }
  .card.volts .card-value { color: var(--accent); }
  .card.amps  .card-value { color: var(--green); }
  .card.watts .card-value { color: var(--yellow); }

  /* ── Charts ── */
  .charts {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .chart-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
  }

  .chart-title {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 12px;
  }

  .chart-card canvas { width: 100% !important; height: 160px !important; }

  /* ── Files section ── */
  .files-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
  }

  .files-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .files-title {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.04em;
  }

  .btn {
    background: none;
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
    cursor: pointer;
    font-family: var(--font-ui);
    transition: border-color 0.15s, background 0.15s;
  }
  .btn:hover { border-color: var(--accent); background: rgba(88,166,255,0.06); }

  .file-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .file-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    font-family: var(--font-mono);
    font-size: 13px;
  }

  .file-row:hover { border-color: var(--muted); }

  .dl-btn {
    font-size: 11px;
    padding: 3px 10px;
    color: var(--accent);
    border-color: var(--accent);
  }

  .empty-state {
    text-align: center;
    color: var(--muted);
    font-size: 13px;
    padding: 24px;
  }

  /* ── FPGA message popup ── */
  .fpga-popup {
    position: fixed;
    top: 24px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 100;
    background: var(--surface);
    border: 1px solid var(--accent);
    border-radius: 8px;
    padding: 16px 28px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    transition: opacity 0.2s, transform 0.2s;
  }
  .fpga-popup.hidden {
    opacity: 0;
    pointer-events: none;
    transform: translateX(-50%) translateY(-10px);
  }
  .fpga-popup-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 6px;
    text-align: center;
  }
  .fpga-popup-text {
    font-size: 20px;
    font-family: var(--font-mono);
    color: var(--accent);
    text-align: center;
    white-space: nowrap;
  }
  .fpga-popup-text.flashing {
    animation: fpga-flash 0.6s step-start infinite;
  }
  @keyframes fpga-flash {
    50% { opacity: 0.15; }
  }

  @media (max-width: 700px) {
    .readouts { grid-template-columns: 1fr 1fr; }
    .charts   { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="dot" id="statusDot"></div>
    Sensor Logger
  </div>
  <div class="status" id="statusText">Waiting for ESP32...</div>
</header>

<div id="fpgaPopup" class="fpga-popup hidden">
  <div class="fpga-popup-inner">
    <div id="fpgaPopupLabel" class="fpga-popup-label">Incoming message</div>
    <div id="fpgaPopupText" class="fpga-popup-text"></div>
  </div>
</div>

<main>
  <!-- Live readouts -->
  <div class="readouts">
    <div class="card temp">
      <div class="card-label">Temperature</div>
      <div class="card-value" id="valTemp">--<span class="card-unit">°C</span></div>
    </div>
    <div class="card volts">
      <div class="card-label">Voltage</div>
      <div class="card-value" id="valVolts">--<span class="card-unit">V</span></div>
    </div>
    <div class="card amps">
      <div class="card-label">Current</div>
      <div class="card-value" id="valAmps">--<span class="card-unit">mA</span></div>
    </div>
    <div class="card watts">
      <div class="card-label">Power</div>
      <div class="card-value" id="valWatts">--<span class="card-unit">mW</span></div>
    </div>
  </div>

  <!-- Charts -->
  <div class="charts">
    <div class="chart-card">
      <div class="chart-title">Temperature (°C)</div>
      <canvas id="chartTemp"></canvas>
    </div>
    <div class="chart-card">
      <div class="chart-title">Voltage (V)</div>
      <canvas id="chartVolts"></canvas>
    </div>
    <div class="chart-card">
      <div class="chart-title">Current (mA)</div>
      <canvas id="chartAmps"></canvas>
    </div>
    <div class="chart-card">
      <div class="chart-title">Power (mW)</div>
      <canvas id="chartWatts"></canvas>
    </div>
  </div>

  <!-- SD card files -->
  <div class="files-card">
    <div class="files-header">
      <div class="files-title">SD Card — Log Files</div>
      <button class="btn" onclick="loadFiles()">Refresh</button>
    </div>
    <div class="file-list" id="fileList">
      <div class="empty-state">Click Refresh to load files from SD card</div>
    </div>
  </div>
</main>

<script>
// ── Chart factory ──────────────────────────────────────
const COLORS = {
  temp:  '#f0883e',
  volts: '#58a6ff',
  amps:  '#3fb950',
  watts: '#d29922',
};

function makeChart(id, color) {
  const ctx = document.getElementById(id).getContext('2d');
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        data: [],
        borderColor: color,
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.3,
        fill: true,
        backgroundColor: color + '18',
      }]
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          ticks: {
            color: '#7d8590',
            font: { size: 10, family: 'monospace' },
            maxTicksLimit: 6,
            maxRotation: 0,
          },
          grid: { color: '#21262d' },
        },
        y: {
          ticks: { color: '#7d8590', font: { size: 10 } },
          grid: { color: '#21262d' },
        }
      }
    }
  });
}

const charts = {
  temp:  makeChart('chartTemp',  COLORS.temp),
  volts: makeChart('chartVolts', COLORS.volts),
  amps:  makeChart('chartAmps',  COLORS.amps),
  watts: makeChart('chartWatts', COLORS.watts),
};

// ── Update loop ──────────────────────────────────
let lastCount = 0;

function updateChart(chart, labels, values) {
  chart.data.labels = labels;
  chart.data.datasets[0].data = values;
  chart.update('none');
}

function setReadout(id, value, decimals) {
  const el = document.getElementById(id);
  const unit = el.querySelector('.card-unit').outerHTML;
  el.innerHTML = (value === null ? '--' : value.toFixed(decimals)) + unit;
}

async function fetchData() {
  try {
    const res = await fetch('/api/data');
    const d   = await res.json();

    const live = d.packet_count > 0;
    document.getElementById('statusDot').className = 'dot' + (live ? ' live' : '');
    document.getElementById('statusText').textContent = live
      ? `${d.packet_count} packets · last ${d.last_update} · ESP32 ${d.esp32_ip}`
      : 'Waiting for ESP32...';

    // ── FPGA message popup ──
    const popup     = document.getElementById('fpgaPopup');
    const popupLbl  = document.getElementById('fpgaPopupLabel');
    const popupText = document.getElementById('fpgaPopupText');

    if (d.fpga_message_state === 'waiting') {
      popup.classList.remove('hidden');
      popupLbl.textContent = 'Incoming message';
      popupText.textContent = 'Waiting for message…';
      popupText.classList.remove('flashing');
    } else if (d.fpga_message_state === 'showing') {
      popup.classList.remove('hidden');
      popupLbl.textContent = 'Incoming message';
      popupText.textContent = d.fpga_message_text || '';
      popupText.classList.add('flashing');
    } else {
      popup.classList.add('hidden');
      popupText.classList.remove('flashing');
    }

    if (d.timestamps.length === 0) return;

    const labels = d.timestamps;
    updateChart(charts.temp,  labels, d.temp_C);
    updateChart(charts.volts, labels, d.bus_V);
    updateChart(charts.amps,  labels, d.current_mA);
    updateChart(charts.watts, labels, d.power_mW);

    const last = d.timestamps.length - 1;
    setReadout('valTemp',  d.temp_C[last],     1);
    setReadout('valVolts', d.bus_V[last],      3);
    setReadout('valAmps',  d.current_mA[last], 2);
    setReadout('valWatts', d.power_mW[last],   2);

  } catch(e) {
    console.error('Fetch error:', e);
  }
}

setInterval(fetchData, 1000);
fetchData();

// ── File browser ─────────────────────────────────────
async function loadFiles() {
  const el = document.getElementById('fileList');
  el.innerHTML = '<div class="empty-state">Loading...</div>';
  try {
    const res = await fetch('/api/files');
    if (!res.ok) {
      const err = await res.json();
      el.innerHTML = `<div class="empty-state">${err.error || 'Could not reach ESP32'}</div>`;
      return;
    }
    const files = await res.json();
    if (!files.length) {
      el.innerHTML = '<div class="empty-state">No CSV files found on SD card</div>';
      return;
    }
    el.innerHTML = files
      .slice()
      .reverse()   // newest first
      .map(f => `
        <div class="file-row">
          <span>${f}</span>
          <a href="/api/download/${f}" download="${f}">
            <button class="btn dl-btn">Download</button>
          </a>
        </div>`)
      .join('');
  } catch(e) {
    el.innerHTML = `<div class="empty-state">Error: ${e.message}</div>`;
  }
}
</script>
</body>
</html>
"""

# ── Entry point ────────────────────────────────────────
if __name__ == '__main__':
    t = threading.Thread(target=udp_receiver, daemon=True)
    t.start()
    print("[Dashboard] Open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000, debug=False)
