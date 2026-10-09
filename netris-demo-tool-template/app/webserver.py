"""Web server entrypoint for the demo integration tool."""

from __future__ import annotations

import logging
from flask import Flask, jsonify, render_template_string
from config import get_config
from netris_client import NetrisClient, NetrisAPIError

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("webserver")

app = Flask(__name__)
cfg = get_config()


def get_client() -> NetrisClient:
    """Instantiate authenticated client from runtime configuration."""
    return NetrisClient(
        host=cfg["netris_url"],
        username=cfg["netris_username"],
        password=cfg["netris_password"],
        verify=cfg["netris_verify_ssl"],
    )


@app.route("/api/health", methods=["GET"])
def health():
    """Universal health endpoint utilised by Demo Control Portal."""
    return jsonify({
        "status": "healthy",
        "service": "netris-demo-tool",
        "target_controller": cfg["netris_url"],
    }), 200


@app.route("/api/status", methods=["GET"])
def status():
    """Retrieve integration status and target controller connectivity."""
    controller_connected = False
    details = {}
    try:
        client = get_client()
        sites = client.get_sites()
        controller_connected = True
        details["sites_count"] = len(sites)
        details["sites"] = [s.get("name") for s in sites]
    except Exception as exc:
        details["error"] = str(exc)

    return jsonify({
        "controller_connected": controller_connected,
        "controller_url": cfg["netris_url"],
        "details": details,
    })


INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Netris Demo Integration Tool</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 text-gray-900 font-sans p-8">
  <div class="max-w-4xl mx-auto space-y-6">
    <div class="bg-white rounded-2xl border border-gray-200 p-8 shadow-sm">
      <div class="flex items-center justify-between pb-6 border-b border-gray-100">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Netris Demo Integration Tool</h1>
          <p class="text-sm text-gray-500 mt-1">Standalone evaluation tool integrated with Netris Controller</p>
        </div>
        <span class="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-xs font-semibold">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          Operational
        </span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        <div class="p-4 bg-gray-50 rounded-xl border border-gray-100">
          <span class="text-xs font-medium text-gray-500">Controller URL</span>
          <p class="font-mono text-sm text-gray-800 mt-1 break-all">{{ cfg.netris_url }}</p>
        </div>
        <div class="p-4 bg-gray-50 rounded-xl border border-gray-100">
          <span class="text-xs font-medium text-gray-500">Target User</span>
          <p class="font-mono text-sm text-gray-800 mt-1">{{ cfg.netris_username }}</p>
        </div>
        <div class="p-4 bg-gray-50 rounded-xl border border-gray-100">
          <span class="text-xs font-medium text-gray-500">Service Port</span>
          <p class="font-mono text-sm text-gray-800 mt-1">{{ cfg.port }}</p>
        </div>
      </div>

      <div class="mt-8 pt-6 border-t border-gray-100 flex items-center justify-between">
        <div class="text-xs text-gray-500">
          Health check responding at <code class="bg-gray-100 px-1 py-0.5 rounded text-gray-700">/api/health</code>
        </div>
        <a href="/api/status" target="_blank" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition">
          Test Controller API Connectivity &rarr;
        </a>
      </div>
    </div>
  </div>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    """Render interactive dashboard for the tool."""
    return render_template_string(INDEX_HTML, cfg=cfg)


if __name__ == "__main__":
    port = cfg["port"]
    host = cfg["host"]
    logger.info("Starting Webserver on http://%s:%d", host, port)
    app.run(host=host, port=port, debug=False)
