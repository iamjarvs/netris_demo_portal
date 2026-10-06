"""
app.py
Flask API Server for Fabric Terraform Builder UI with Live Deployment & Cleanup Engine.
"""

import os
import io
import zipfile
import tempfile
import shutil
import subprocess
from flask import Flask, request, jsonify, send_file, send_from_directory
from netris_client import NetrisClient
from conflict_engine import ConflictChecker
from tf_generator import TerraformGenerator, auto_calculate_ns_fabric, auto_calculate_entire_fabric
from deployer import deploy_manager
from design_store import design_store
from topology_layout import TopologyLayoutEngine
from deployment_history import history_manager

app = Flask(__name__, static_folder="../frontend/dist", static_url_path="")

# Enable CORS for all routes
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Fabric Terraform Builder API"})


@app.route("/api/calculate-ns-fabric", methods=["POST", "OPTIONS"])
def calculate_ns_fabric_endpoint():
    if request.method == "OPTIONS":
        return "", 204
    data = request.json or {}
    gpu_count = int(data.get("gpu_count", 8))
    gpu_ns_ports = int(data.get("gpu_ns_ports", 2))
    storage_servers = int(data.get("storage_servers", 4)) if data.get("enable_storage", True) else 0
    storage_ns_ports = int(data.get("storage_ns_ports", 2))
    switch_port_count = int(data.get("switch_port_count", 64))
    softgate_flavor = data.get("softgate_flavor", "sg-hs")

    recom = auto_calculate_ns_fabric(
        gpu_count=gpu_count,
        gpu_ns_ports=gpu_ns_ports,
        storage_servers=storage_servers,
        storage_ns_ports=storage_ns_ports,
        switch_port_count=switch_port_count,
        softgate_flavor=softgate_flavor
    )
    return jsonify({"success": True, "recommendation": recom})


@app.route("/api/netris/test-connection", methods=["POST", "OPTIONS"])
def test_connection():
    if request.method == "OPTIONS":
        return "", 204
    data = request.json or {}
    url = data.get("controller_address", "https://adam-ctl.netris.io")
    user = data.get("controller_login", "netris")
    password = data.get("controller_password", "")

    client = NetrisClient(url, user, password)
    res = client.authenticate()
    return jsonify(res)


@app.route("/api/netris/fetch-state", methods=["POST", "OPTIONS"])
def fetch_state():
    if request.method == "OPTIONS":
        return "", 204
    data = request.json or {}
    url = data.get("controller_address", "https://adam-ctl.netris.io")
    user = data.get("controller_login", "netris")
    password = data.get("controller_password", "")

    client = NetrisClient(url, user, password)
    auth = client.authenticate()
    if not auth["success"]:
        return jsonify(auth), 401

    try:
        state = client.fetch_full_state()
        return jsonify({"success": True, "state": state})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/netris/check-conflicts", methods=["POST", "OPTIONS"])
def check_conflicts():
    if request.method == "OPTIONS":
        return "", 204
    payload = request.json or {}
    cfg = payload.get("fabric_config", {})
    ctl_url = cfg.get("controller_address", "https://adam-ctl.netris.io")
    ctl_user = cfg.get("controller_login", "netris")
    ctl_pass = cfg.get("controller_password", "")

    client = NetrisClient(ctl_url, ctl_user, ctl_pass)
    auth = client.authenticate()
    if not auth["success"]:
        return jsonify({
            "success": False,
            "message": f"Controller authentication failed: {auth['message']}",
            "conflicts": [],
            "suggestions": {}
        }), 400

    try:
        state = client.fetch_full_state()
        checker = ConflictChecker(state)
        report = checker.check(cfg)
        return jsonify({"success": True, "report": report, "state_summary": {
            "sites": [s.get("name") for s in state.get("sites", []) if isinstance(s, dict)],
            "allocations_count": len(state.get("allocations", [])),
            "subnets_count": len(state.get("subnets", [])),
            "asns_count": len(state.get("existing_asns", [])),
            "hardware_count": state.get("hardware_count", 0),
        }})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/fabric/auto-size", methods=["POST", "OPTIONS"])
def api_auto_size_fabric():
    if request.method == "OPTIONS":
        return "", 204
    cfg = request.json or {}
    try:
        sizing = auto_calculate_entire_fabric(cfg)
        return jsonify({"success": True, "sizing": sizing})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route("/api/generator/preview", methods=["POST", "OPTIONS"])
def preview_terraform():
    if request.method == "OPTIONS":
        return "", 204
    cfg = request.json or {}
    try:
        gen = TerraformGenerator(cfg)
        files = gen.generate_all_files()
        file_tree = []
        for path in sorted(files.keys()):
            is_csv = path.startswith("csv/")
            file_tree.append({
                "path": path,
                "category": "CSV Data" if is_csv else ("Config" if path.endswith(".tfvars") else "Terraform HCL"),
                "size": len(files[path]),
                "lines": len(files[path].splitlines()),
            })
        return jsonify({
            "success": True,
            "total_files": len(files),
            "file_tree": file_tree,
            "files": files
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route("/api/generator/download-zip", methods=["POST", "OPTIONS"])
def download_zip():
    if request.method == "OPTIONS":
        return "", 204
    cfg = request.json or {}
    try:
        gen = TerraformGenerator(cfg)
        files = gen.generate_all_files()
        
        site_name = cfg.get("site_name", "fabric-deployment").lower().replace(" ", "-")
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for path, content in files.items():
                zip_file.writestr(f"{site_name}/{path}", content)
        
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{site_name}-netris-terraform.zip"
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/generator/validate-tofu", methods=["POST", "OPTIONS"])
def validate_tofu():
    if request.method == "OPTIONS":
        return "", 204
    cfg = request.json or {}
    tofu_bin = "/opt/homebrew/bin/tofu"
    if not os.path.exists(tofu_bin):
        tofu_bin = shutil.which("tofu") or shutil.which("terraform")

    if not tofu_bin:
        return jsonify({
            "success": False,
            "message": "OpenTofu or Terraform binary not found on the host system."
        }), 404

    temp_dir = tempfile.mkdtemp(prefix="netris_tofu_val_")
    try:
        gen = TerraformGenerator(cfg)
        files = gen.generate_all_files()
        for path, content in files.items():
            full_path = os.path.join(temp_dir, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

        provider_cache = "/Users/adam/Downloads/kpn01-main/.terraform"
        lock_file = "/Users/adam/Downloads/kpn01-main/.terraform.lock.hcl"
        if os.path.exists(lock_file):
            shutil.copy(lock_file, temp_dir)
        if os.path.exists(provider_cache):
            try:
                os.symlink(provider_cache, os.path.join(temp_dir, ".terraform"))
            except Exception:
                shutil.copytree(provider_cache, os.path.join(temp_dir, ".terraform"))

        res = subprocess.run([tofu_bin, "validate"], cwd=temp_dir, capture_output=True, text=True)
        return jsonify({
            "success": res.returncode == 0,
            "exit_code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Live Deployment & Cleanup Engine Endpoints
# =============================================================================

@app.route("/api/deploy/run", methods=["POST", "OPTIONS"])
def deploy_run():
    if request.method == "OPTIONS":
        return "", 204
    data = request.get_json(silent=True) or {}
    action = data.get("action", "plan")  # init, plan, apply, destroy, cleanup
    config = data.get("config", None)
    slug = data.get("slug", None)

    res = deploy_manager.run_command(action, config=config, slug=slug)
    return jsonify(res)


@app.route("/api/deploy/status", methods=["GET"])
def deploy_status():
    return jsonify(deploy_manager.get_status())


@app.route("/api/deploy/logs", methods=["GET"])
def deploy_logs():
    since = int(request.args.get("since", 0))
    logs = deploy_manager.get_logs(since=since)
    status_info = deploy_manager.get_status()
    return jsonify({
        "logs": logs,
        "total_lines": len(deploy_manager.logs),
        "status": status_info["status"],
        "action": status_info["action"],
        "active_slug": status_info.get("active_slug"),
        "active_site_name": status_info.get("active_site_name"),
        "exit_code": status_info["exit_code"],
        "plan_summary": status_info["plan_summary"],
    })


@app.route("/api/deploy/abort", methods=["POST", "OPTIONS"])
def deploy_abort():
    if request.method == "OPTIONS":
        return "", 204
    return jsonify(deploy_manager.abort())


@app.route("/api/deploy/reset-state", methods=["POST", "OPTIONS"])
def deploy_reset_state():
    if request.method == "OPTIONS":
        return "", 204
    return jsonify(deploy_manager.reset_state())


@app.route("/api/deploy/state", methods=["GET", "POST", "OPTIONS"])
def deploy_state():
    if request.method == "OPTIONS":
        return "", 204
    data = request.get_json(silent=True) or {}
    slug = request.args.get("slug") or data.get("slug")
    if slug:
        return jsonify(deploy_manager.get_workspace_state(slug))
    config = data.get("config", data)
    return jsonify(deploy_manager.get_workspace_state(config))


@app.route("/api/deploy/purge-local", methods=["POST", "OPTIONS"])
def deploy_purge_local():
    if request.method == "OPTIONS":
        return "", 204
    data = request.get_json(silent=True) or {}
    slug = data.get("slug")
    if slug:
        return jsonify(deploy_manager.purge_local_state(slug))
    config = data.get("config", data)
    return jsonify(deploy_manager.purge_local_state(config))


# =============================================================================
# Deployment Fleet & History Endpoints
# =============================================================================

@app.route("/api/deployments", methods=["GET", "OPTIONS"])
def list_deployments():
    if request.method == "OPTIONS":
        return "", 204
    return jsonify({
        "success": True,
        "deployments": history_manager.scan_deployments()
    })


@app.route("/api/deployments/<slug>", methods=["GET", "OPTIONS"])
def get_deployment(slug):
    if request.method == "OPTIONS":
        return "", 204
    dep = history_manager.inspect_deployment(slug)
    return jsonify({
        "success": dep.get("exists", False),
        "deployment": dep
    })


@app.route("/api/deployments/<slug>/run", methods=["POST", "OPTIONS"])
def run_deployment_action(slug):
    if request.method == "OPTIONS":
        return "", 204
    data = request.get_json(silent=True) or {}
    action = data.get("action", "destroy")
    res = deploy_manager.run_command(action, slug=slug)
    return jsonify(res)


@app.route("/api/deployments/<slug>/purge", methods=["POST", "OPTIONS"])
def purge_deployment(slug):
    if request.method == "OPTIONS":
        return "", 204
    return jsonify(deploy_manager.purge_local_state(slug))


@app.route("/api/deployments/<slug>", methods=["DELETE", "OPTIONS"])
def delete_deployment_workspace(slug):
    if request.method == "OPTIONS":
        return "", 204
    force = request.args.get("force", "false").lower() == "true"
    return jsonify(history_manager.delete_deployment(slug, force=force))


@app.route("/api/deployments/history", methods=["GET", "OPTIONS"])
def get_deployment_history():
    if request.method == "OPTIONS":
        return "", 204
    limit = int(request.args.get("limit", 100))
    slug = request.args.get("slug")
    return jsonify({
        "success": True,
        "history": history_manager.get_history(limit=limit, site_slug=slug)
    })


# =============================================================================
# Saved Designs Endpoints
# =============================================================================

@app.route("/api/designs", methods=["GET", "OPTIONS"])
def list_designs():
    if request.method == "OPTIONS":
        return "", 204
    return jsonify({
        "success": True,
        "designs": design_store.list_designs()
    })


@app.route("/api/designs/<design_id>", methods=["GET", "DELETE", "OPTIONS"])
def get_or_delete_design(design_id):
    if request.method == "OPTIONS":
        return "", 204
    if request.method == "DELETE":
        ok = design_store.delete_design(design_id)
        return jsonify({"success": ok})
    design = design_store.get_design(design_id)
    if not design:
        return jsonify({"success": False, "message": "Design not found"}), 404
    return jsonify({"success": True, "design": design})


@app.route("/api/designs", methods=["POST"])
def save_design():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "message": "Design name is required"}), 400
    description = data.get("description", "").strip()
    config = data.get("config", {})
    design_id = data.get("id")

    saved = design_store.save_design(name, description, config, design_id=design_id)
    return jsonify({
        "success": True,
        "message": f"Design '{name}' saved successfully",
        "design": saved
    })


# =============================================================================
# Topology Layout Engine Endpoints
# =============================================================================

@app.route("/api/topology/arrange", methods=["POST", "OPTIONS"])
def topology_arrange():
    if request.method == "OPTIONS":
        return "", 204
    data = request.get_json(silent=True) or {}
    site_id = data.get("site_id")
    url = data.get("controller_address", "https://adam-ctl.netris.io")
    user = data.get("controller_login", "netris")
    password = data.get("controller_password", "")

    client = NetrisClient(url, user, password)
    auth = client.authenticate()
    if not auth.get("success"):
        return jsonify({"success": False, "message": f"Authentication failed: {auth.get('message')}"}), 401

    if not site_id:
        # Try finding site_id by site_name
        site_name = data.get("site_name", "").strip().lower()
        sites = client._get("/api/v2/sites") or []
        for s in sites:
            if isinstance(s, dict) and s.get("name", "").strip().lower() == site_name:
                site_id = s.get("id")
                break

    if not site_id:
        return jsonify({"success": False, "message": "site_id or valid site_name is required"}), 400

    try:
        engine = TopologyLayoutEngine(client)
        res = engine.apply_layout(int(site_id))
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/topology/reset", methods=["POST", "OPTIONS"])
def topology_reset():
    if request.method == "OPTIONS":
        return "", 204
    data = request.get_json(silent=True) or {}
    site_id = data.get("site_id")
    url = data.get("controller_address", "https://adam-ctl.netris.io")
    user = data.get("controller_login", "netris")
    password = data.get("controller_password", "")

    client = NetrisClient(url, user, password)
    auth = client.authenticate()
    if not auth.get("success"):
        return jsonify({"success": False, "message": f"Authentication failed: {auth.get('message')}"}), 401

    if not site_id:
        # Try finding site_id by site_name
        site_name = data.get("site_name", "").strip().lower()
        sites = client._get("/api/v2/sites") or []
        for s in sites:
            if isinstance(s, dict) and s.get("name", "").strip().lower() == site_name:
                site_id = s.get("id")
                break

    if not site_id:
        return jsonify({"success": False, "message": "site_id or valid site_name is required"}), 400

    try:
        engine = TopologyLayoutEngine(client)
        res = engine.clear_layout(int(site_id))
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



# Serve React Single-Page Application
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/dist"))
    if path and os.path.exists(os.path.join(dist_dir, path)):
        return send_from_directory(dist_dir, path)
    if os.path.exists(os.path.join(dist_dir, "index.html")):
        return send_from_directory(dist_dir, "index.html")
    return jsonify({
        "message": "Fabric Terraform Builder API is running."
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"Starting Fabric Terraform Builder backend on http://localhost:{port} ...")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
