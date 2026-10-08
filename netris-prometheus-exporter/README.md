> **[WARNING] Demonstration Code Only**
> This repository contains unsupported demonstration code for architectural illustration. It is a **possible implementation pattern**, not an official Netris product or supported tool. Use at your own risk.

# Netris Prometheus Exporter & Observability Stack

A standalone Prometheus Exporter and pre-configured Grafana Observability stack for the Netris Controller, featuring semantic data enrichment and a 100% offline simulation replay engine.

---

## 1. What This Is
Unlike generic SNMP pollers, this integration correlates low-level switch telemetry with high-level Netris constructs.
- Integrates **Prometheus/Grafana** with the **Netris Controller**.
- Designed for Network Operators and SREs.
- Features: Semantic enrichment (Tenants, VPCs, V-Nets), Instant 90-Min Historical TSDB backfill, and offline offline simulation mode.

---

## 2. How It Works (Under the Hood)

1. **Initialization:** The script reads from `.env` to determine if it should run in `--live` or `--sim` mode.
2. **Authentication (Live):** It authenticates against the Netris Controller API.
3. **Data Retrieval:** It pulls telemetry and topology intent from the controller.
4. **Enrichment:** It maps physical ports to their logical VPCs and Server Clusters.
5. **Execution:** It exposes these metrics dynamically on port `:8000` for the local Prometheus container to scrape.

---

## 3. How to Run It (Quickstart)

### Prerequisites
- Python 3.10+
- Docker & Docker Compose

### Steps
1. **Clone the repository:**
   ```bash
   git clone https://github.com/iamjarvs/netris-prometheus-exporter.git
   cd netris-prometheus-exporter
   ```
2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials if using live mode
   ```
3. **Start the tool (Simulation Mode):**
   ```bash
   ./start.sh --sim
   ```
4. **Stop the tool:**
   ```bash
   ./stop.sh
   ```

---

## 4. How to Build Your Own Experience (For Developers)

If you want to modify this integration, start here:
- **`app/exporter.py`:** The main entry point and web server.
- **`app/enricher.py`:** The core logic mapping physical counters to VPCs. Modify this if you want to add new semantic tags.
- **`app/netris_client.py`:** The live API client.
- **`app/sim_client.py`:** The offline mock API client.
