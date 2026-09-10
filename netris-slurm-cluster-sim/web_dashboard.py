#!/usr/bin/env python3
"""
web_dashboard.py - Real-Time Web Server & REST API for Slurm + Netris Integration
Serves the web UI and handles live API calls without any external Python dependencies.
"""

import http.server
import json
import logging
import os
import posixpath
import socketserver
import time
import urllib.parse
from typing import Any, Dict, Optional
from slurm_orchestrator import SlurmOrchestrator

logger = logging.getLogger("web_dashboard")


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_dashboard_handler(orchestrator: SlurmOrchestrator, static_dir: str):
    """Factory creating the HTTP request handler bound to the orchestrator."""

    # Cache live Netris clusters for 2 seconds to avoid overwhelming the controller
    netris_cache = {"data": [], "last_fetch": 0.0}

    def _get_live_netris_clusters():
        now = time.time()
        if now - netris_cache["last_fetch"] < 2.0 and netris_cache["data"]:
            return netris_cache["data"]
        try:
            clusters = orchestrator.client.get_active_clusters()
            netris_cache["data"] = clusters
            netris_cache["last_fetch"] = now
            return clusters
        except Exception as e:
            logger.warning(f"Failed to fetch live clusters from Netris: {e}")
            return netris_cache.get("data", [])

    class DashboardHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # Suppress high-frequency polling access logs to keep terminal quiet
            try:
                msg = str(format) % args
                if "/api/state" in msg or "favicon.ico" in msg or "/api/telemetry" in msg:
                    return
                logger.info(f"{self.address_string()} - {msg}")
            except Exception:
                pass

        def _send_json(self, data: Any, status: int = 200):
            try:
                payload = json.dumps(data).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(payload)
            except Exception as e:
                logger.warning(f"Error sending JSON response: {e}")

        def _send_error_json(self, msg: str, status: int = 400):
            self._send_json({"error": msg}, status=status)

        def do_GET(self):
            try:
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path

                if path in ("", "/"):
                    self._serve_file(os.path.join(static_dir, "index.html"), "text/html")
                    return

                if path.startswith("/static/"):
                    rel_path = path[len("/static/") :]
                    file_path = os.path.join(static_dir, rel_path)
                    if os.path.exists(file_path):
                        content_type = "text/plain"
                        if file_path.endswith(".html"):
                            content_type = "text/html"
                        elif file_path.endswith(".css"):
                            content_type = "text/css"
                        elif file_path.endswith(".js"):
                            content_type = "application/javascript"
                        elif file_path.endswith(".svg"):
                            content_type = "image/svg+xml"
                        self._serve_file(file_path, content_type)
                        return
                    else:
                        self.send_error(404, "File not found")
                        return

                if path == "/api/state":
                    snapshot = orchestrator.get_cluster_snapshot()
                    snapshot["netris_clusters"] = _get_live_netris_clusters()
                    self._send_json(snapshot)
                    return

                if path == "/api/telemetry":
                    snap = orchestrator.get_cluster_snapshot()
                    self._send_json(snap.get("telemetry", {}))
                    return

                if path == "/api/clusters":
                    self._send_json(_get_live_netris_clusters())
                    return

                if path == "/favicon.ico":
                    self.send_response(204)
                    self.end_headers()
                    return

                self.send_error(404, "Endpoint not found")
            except Exception as e:
                logger.error(f"Unhandled GET error for {self.path}: {e}")
                self._send_error_json(str(e), status=500)

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length) if length > 0 else b"{}"
            try:
                body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            except json.JSONDecodeError:
                body = {}

            if path == "/api/jobs":
                name = body.get("name", "Custom-AI-Job")
                nodes = int(body.get("nodes", 2))
                duration = int(body.get("duration", 20))
                pattern = body.get("pattern", "Ring-AllReduce")
                user = body.get("user", "web-operator")

                if nodes < 1 or nodes > len(orchestrator.nodes):
                    self._send_error_json(f"Requested {nodes} nodes, but pool only has {len(orchestrator.nodes)}")
                    return

                job_id = orchestrator.submit_job(
                    name=name,
                    nodes_count=nodes,
                    duration=duration,
                    pattern=pattern,
                    user=user,
                )
                self._send_json({"job_id": job_id, "status": "submitted"})
                return

            if path.startswith("/api/jobs/") and path.endswith("/cancel"):
                # /api/jobs/<id>/cancel
                parts = path.strip("/").split("/")
                if len(parts) == 4:
                    job_id = parts[2]
                    ok = orchestrator.cancel_job(job_id)
                    self._send_json({"job_id": job_id, "cancelled": ok})
                    return

            if path == "/api/autopilot":
                orchestrator.autopilot = not orchestrator.autopilot
                self._send_json({"autopilot": orchestrator.autopilot})
                return

            if path == "/api/teardown":
                orchestrator.teardown_all()
                self._send_json({"status": "teardown_initiated"})
                return

            self.send_error(404, "Endpoint not found")

        def _serve_file(self, filepath: str, content_type: str):
            try:
                with open(filepath, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, f"Error reading file: {e}")

    return DashboardHandler


def run_web_server(orchestrator: SlurmOrchestrator, host: str = "0.0.0.0", port: int = 8088):
    """Starts the threaded HTTP web server on the specified host and port."""
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    handler = make_dashboard_handler(orchestrator, static_dir)
    server = ThreadedHTTPServer((host, port), handler)
    logger.info(f"Slurm + Netris Web Dashboard live at http://{host}:{port}/")
    print(f"\n=================================================================")
    print(f"  NETRIS + SLURM AI FABRIC DASHBOARD")
    print(f"  Access UI at: http://localhost:{port}/")
    print(f"=================================================================\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        logger.info("Web dashboard stopped.")


if __name__ == "__main__":
    from netris_api import NetrisAPIClient

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    client = NetrisAPIClient()
    client.authenticate()
    orch = SlurmOrchestrator(client, pool_size=8, autopilot=True)
    orch.start()
    run_web_server(orch, port=8088)
