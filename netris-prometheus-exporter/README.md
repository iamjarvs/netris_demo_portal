# Netris Prometheus Exporter & Observability Stack

A standalone Prometheus Exporter and pre-configured Grafana Observability stack for the **Netris Controller**.

Unlike generic SNMP pollers or standard node exporters, this integration features a **Semantic Data Enrichment Engine** that correlates low-level switch and port telemetry with high-level Netris constructs: **Tenants, VPCs, V-Nets, Server Clusters, and LLDP Physical Cabling Intent**.

It also features a 100% offline **Simulation Mode & Telemetry Recorder** with **Instant 90-Minute Historical TSDB Pre-population**, allowing you to start the stack and immediately present full, rich Grafana dashboards without waiting for streaming metrics to accumulate.

---

## 1. Architectural Highlights

```
┌────────────────────────────────────────────────────────┐
│  LIVE MODE: Netris Controller (adam-ctl.netris.io)     │
│  - Switch & Port Counters (Graphite streaming octets)  │
│  - Continuous Active Assurance (Health & Cabling)      │
│  - Topological Metadata (Sites, VPCs, Links, Clusters) │
└──────────────────────────┬─────────────────────────────┘
                           │ (Optional ./record.sh capture)
                           ▼
┌────────────────────────────────────────────────────────┐
│  OFFLINE SIMULATION: sim_data/telemetry_recording.json  │
│  - Instant 90-Minute TSDB Backfill (promtool blocks)   │
│  - Infinite Circular Buffer Replay                     │
│  - Micro-Jitter (±1-3%) for Organic Graph Variance     │
│  - Zero Netris Creds or Internet Needed                │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Netris Prometheus Exporter (Port 9101)                │
│  - Semantic Enrichment (Remote Switch, Server Cluster) │
│  - East-West vs North-South Traffic Separation         │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│  Prometheus TSDB (Port 9090) ──> Grafana (Port 3000)   │
│  - 90 Minutes of Historical Data Pre-populated         │
│  - Live Streaming Data Continuing Forward              │
└────────────────────────────────────────────────────────┘
```

### Key Capabilities
- **Instant Demo Readiness (90-Minute Pre-population)**: When simulation mode starts, Prometheus TSDB is automatically backfilled with 90 minutes of historical telemetry (1.4+ million samples). Every Grafana panel is 100% populated with continuous historical lines from the very first second.
- **Semantic Port Enrichment**: Every switch port counter is automatically enriched with its connected device (`remote_device`), remote port (`remote_port`), remote type (`server` / `switch`), port role (`server_facing` / `fabric_interconnect`), tenant (`Admin`), and assigned VPC & Server Cluster (`Demo`).
- **East-West & North-South Separation**: Segregates server-facing cluster access throughput from spine/leaf fabric transit in dedicated Grafana panels and metrics.
- **Continuous Active Assurance**: Exposes real-time pass/fail states for Netris's 1,300+ automated background verification checks, including LLDP cabling validation, BGP underlay consistency, and optical transceiver degradation.
- **BGP & Multi-Cloud Peering**: Tracks session states, prefixes received, and uptime across underlay fabric links and external edge BGP neighbors terminating on Netris SoftGates.
- **Node Hardware Assurance**: CPU load averages (1m, 5m, 15m), RAM % used, disk % used, fan tray RPM status, and dual-PSU redundancy.
- **Offline Simulation Replay**: Replay recorded fabric metrics continuously without live controller access.

---

## 2. Quickstart: One-Click Launcher (`start.sh`)

The root directory includes an automated launcher script `start.sh`:

### Running in Simulation Mode (Instant 90-Minute Demo Mode)
```bash
./start.sh --sim
```
* **Zero Credentials Required**: Does not require `netris.var` or access to `adam-ctl.netris.io`.
* **Instant Historical Data**: Automatically synthesizes and injects **90 minutes of historical TSDB data** into Prometheus in ~15 seconds using `promtool`.
* **Continuous Replay**: Replays frames in an infinite ring buffer with realistic micro-jitter (±1–3%) so Grafana streams continuous live updates after the historical data.

#### Customizing Historical Pre-fill Duration
```bash
# Pre-populate 120 minutes of history instead of 90:
./start.sh --sim --backfill 120

# Launch simulation mode without historical backfill:
./start.sh --sim --no-backfill
```

### Running in Live Mode (Active Controller)
```bash
./start.sh --live
```
* Connects to the Netris Controller specified in `netris.var`.
* Enriches and streams live switch octets and Active Assurance health checks.

### Stopping the Stack
```bash
./stop.sh
```

---

## 3. Standalone Historical Backfill Tool (`backfill.sh`)

You can artificially backfill or refresh Prometheus TSDB history at any time without restarting the entire stack:

```bash
# Syntax: ./backfill.sh [minutes] [step_in_seconds]
./backfill.sh 90 60
```

### How the Backfill Engine Works
1. Reads the recorded snapshot (`sim_data/telemetry_recording.json`).
2. Iterates backward in time from `now` to `now - N minutes` at the specified step resolution (e.g. 60 seconds).
3. Evaluates all 17,000+ metric series with realistic micro-jitter (traffic variance, CPU loads, memory utilization).
4. Emits valid OpenMetrics format grouped by metric family.
5. Invokes `promtool tsdb create-blocks-from openmetrics` inside the Prometheus container to compile raw TSDB blocks directly into `./prometheus/data`.
6. Prometheus serves historical range queries over this data instantly upon mounting.

---

## 4. Telemetry Recording Engine (`record.sh`)

You can create or refresh telemetry snapshot recordings at any time while connected to a live Netris Controller:

```bash
# Syntax: ./record.sh [duration_in_seconds] [interval_in_seconds]
./record.sh 60 15
```

Or using the launcher shortcut:
```bash
./start.sh --record 60 15
```

### What the Recorder Captures:
1. **Complete Topological Snapshot**:
   - Sites, Managed Hardware, Ports, and Cabling Links
   - VPCs, V-Nets, Tenants, and IPAM Subnets
   - Server Clusters and GPU Pod Mappings
2. **Dynamic Streaming Frames**:
   - Continuous Active Assurance health checks
   - Agent heartbeats & hardware alarms
   - Streaming Graphite interface octets (receive & transmit) across all switches and SoftGates
3. **Packaging**:
   - Compiles everything into `sim_data/telemetry_recording.json`.

---

## 5. Accessing Services & Grafana Dashboard Suite

Once started via `./start.sh`:

- **Grafana UI**: `http://localhost:3000` (User: `admin` / Password: `admin`)
- **Prometheus UI**: `http://localhost:9090`
- **Raw Exporter Metrics**: `http://localhost:9101/metrics`

### Pre-Configured Multi-Database Dashboard Suite:
The stack automatically provisions 4 production dashboards inside the **Netris Network Observability** folder, with seamless top-banner navigation between them:

1. **Netris Fabric Observability (`netris-fabric-overview.json`) [DEFAULT HOME]**
   - Executive cross-engine overview uniting fleet scale, dual-plane traffic (East-West compute mesh vs North-South border transit), continuous active assurance, and high-signal KPIs from all 3 underlying databases.
2. **Netris - Graphite Time-Series Engine (`netris-graphite-telemetry.json`)**
   - High-frequency streaming telemetry: interface octets (bps), packet flow rates (PPS in/out), discard & error rates, optical transceiver RX power levels (dBm per lane), per-core CPU mode breakdowns, memory allocations, and SoftGate NAT connection tracking dynamics.
3. **Netris - MariaDB Relational State & SLA Assurance (`netris-mariadb-state.json`)**
   - Relational system of record: Multi-Site Netris VPC & VPN mesh SLA metrics (Round-Trip Latency RTT ms, packet loss %, quality score 0-100), switch hardware forwarding capacity (FIB routes, bridge MAC tables), TCAM ACL quotas (ingress/egress), Layer-4 Load Balancer (L4LB) VIP health, and IPAM subnet allocations.
4. **Netris - MongoDB Environmental & Telescope Sensors (`netris-mongodb-sensors.json`)**
   - Telescope daemon real-time hardware telemetry: ASIC & chassis temperature sensors (°C), cooling fan tray tachometers (RPM), dual-PSU power supply status & redundancy, physical layer Bit Error Rates (Pre/Post-FEC BER), and critical switch NOS system daemons (`switchd`, `frr`, `syscd`, `vxpd-nvue`, `vxrd`).

---

## 6. Configuration Reference

### Connection File (`netris.var`)
*Used exclusively in Live Mode. Optional in Simulation Mode.*
```bash
NETRIS_URL="https://adam-ctl.netris.io"
NETRIS_USERNAME="netris"
NETRIS_PASSWORD="your-password"
NETRIS_AUTH_SCHEME_ID=1
NETRIS_VERIFY_SSL=false
```

### Runtime Parameters (`config.env`)
```bash
# Ports
EXPORTER_PORT=9101
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Exporter Behavior & Timings
METADATA_REFRESH_INTERVAL=300
SCRAPE_TIMEOUT=20
LOG_LEVEL=INFO

# Tri-Database Telemetry Toggles
ENABLE_STREAMING_TRAFFIC=true      # Graphite interface octets (bps)
ENABLE_STREAMING_PPS=true          # Graphite packet flow rates (pps)
ENABLE_STREAMING_ERRORS=true       # Graphite error & discard rates
ENABLE_STREAMING_OPTICS=true       # Graphite optical RX power levels (dBm)
ENABLE_STREAMING_SYSTEM=true       # Graphite per-core CPU, RAM & SoftGate conntrack
ENABLE_MARIADB_TELEMETRY=true      # MariaDB VPN SLA mesh, FIB/MAC & TCAM quotas
ENABLE_MONGODB_SENSORS=true        # MongoDB ASIC thermals, fan RPM, PSU & BER
STREAMING_TRAFFIC_ACTIVE_ONLY=true # Filters inactive down ports for lean TSDB

# Simulation Mode (can also be toggled with ./start.sh --sim)
SIMULATION_MODE=false
SIM_DATA_FILE=sim_data/telemetry_recording.json
```

---

## 7. Complete Metric Reference (48 Metric Families)

### 📊 Engine 1: Graphite / Whisper (High-Frequency Streaming)
| Metric Name | Type | Description | Key Enriched Labels |
| :--- | :--- | :--- | :--- |
| `netris_interface_receive_bits_per_second` | Gauge | Live receive throughput in bits/sec | `site`, `device_name`, `device_role`, `fabric_type`, `port`, `port_role`, `remote_device`, `remote_port`, `server_cluster`, `vpc`, `tenant` |
| `netris_interface_transmit_bits_per_second` | Gauge | Live transmit throughput in bits/sec | Same as receive bits/sec |
| `netris_interface_receive_bytes_per_second` | Gauge | Live receive throughput in bytes/sec | Same as receive bits/sec |
| `netris_interface_transmit_bytes_per_second` | Gauge | Live transmit throughput in bytes/sec | Same as receive bits/sec |
| `netris_interface_receive_packets_per_second` | Gauge | Ingress packet flow rate (PPS) | Same as receive bits/sec |
| `netris_interface_transmit_packets_per_second` | Gauge | Egress packet flow rate (PPS) | Same as receive bits/sec |
| `netris_interface_receive_errors_per_second` | Gauge | Physical layer ingress error rate | `site`, `device_name`, `device_role`, `port` |
| `netris_interface_transmit_errors_per_second` | Gauge | Physical layer egress error rate | `site`, `device_name`, `device_role`, `port` |
| `netris_optical_power_rx_dbm` | Gauge | Transceiver optical receive power in dBm | `site`, `device_name`, `device_role`, `port`, `lane` |
| `netris_node_cpu_percent` | Gauge | Per-core CPU utilization breakdown % | `site`, `device_name`, `cpu`, `mode` (user, system, idle, wait) |
| `netris_node_memory_bytes` | Gauge | Detailed node memory breakdown | `site`, `device_name`, `kind` (used, free) |
| `netris_softgate_conntrack_entries` | Gauge | Active SoftGate NAT/conntrack sessions | `site`, `device_name` |
| `netris_softgate_conntrack_percent` | Gauge | SoftGate conntrack table capacity used % | `site`, `device_name` |

### 🗄️ Engine 2: MariaDB (Relational State, Capacity & Multi-Site SLA)
| Metric Name | Type | Description | Key Enriched Labels |
| :--- | :--- | :--- | :--- |
| `netris_mesh_vpn_status` | Gauge | Multi-site VPN tunnel operational status | `site`, `tunnel_name`, `local_endpoint`, `remote_endpoint`, `local_site`, `remote_site` |
| `netris_mesh_vpn_quality_score` | Gauge | Multi-site VPN SLA quality score (0–100) | `site`, `tunnel_name`, `local_site`, `remote_site` |
| `netris_mesh_vpn_rtt_seconds` | Gauge | Multi-site VPN round-trip latency (RTT) | `site`, `tunnel_name`, `local_site`, `remote_site` |
| `netris_mesh_vpn_loss_percent` | Gauge | Multi-site VPN packet loss percentage | `site`, `tunnel_name`, `local_site`, `remote_site` |
| `netris_mesh_vpn_bgp_state` | Gauge | Underlay BGP peering state across tunnel | `site`, `tunnel_name`, `local_site`, `remote_site` |
| `netris_switch_capacity_routes` | Gauge | Hardware FIB routing table entries used | `site`, `device_name`, `device_role`, `fabric_type` |
| `netris_switch_capacity_macs` | Gauge | Hardware bridge MAC table entries used | `site`, `device_name`, `device_role`, `fabric_type` |
| `netris_switch_capacity_ingress_acls` | Gauge | TCAM ingress ACL rules consumed | `site`, `device_name`, `device_role`, `fabric_type` |
| `netris_switch_capacity_egress_acls` | Gauge | TCAM egress ACL rules consumed | `site`, `device_name`, `device_role`, `fabric_type` |
| `netris_l4lb_vip_health_status` | Gauge | Layer-4 Load Balancer virtual IP status | `site`, `lb_name`, `vip_ip`, `status_desc` |
| `netris_ipam_subnet_info` | Gauge | Fabric IPAM subnet allocation metadata | `site`, `subnet_prefix`, `purpose`, `vpc`, `tenant` |
| `netris_device_info` | Gauge | Managed inventory metadata | `site`, `device_name`, `device_role`, `fabric_type`, `nos` |
| `netris_device_status` | Gauge | Device operational state (1=OK, 0=Err) | `site`, `device_name`, `device_role`, `fabric_type` |
| `netris_port_status` | Gauge | Physical port operational state (1=UP, 0=DOWN) | `device_name`, `port`, `port_role`, `remote_device`, `remote_port`, `server_cluster`, `vpc`, `tenant` |
| `netris_port_utilization_rx_percent` | Gauge | Port RX bandwidth capacity utilization % | Same as `netris_port_status` |
| `netris_port_utilization_tx_percent` | Gauge | Port TX bandwidth capacity utilization % | Same as `netris_port_status` |
| `netris_port_error_status` | Gauge | Port link error / drop alarm state | `device_name`, `port`, `remote_device`, `port_role` |
| `netris_ebgp_session_state` | Gauge | External border transit BGP session state | `site`, `neighbor_name`, `peer_ip`, `peer_asn`, `softgate`, `vpc` |
| `netris_ebgp_prefixes_received` | Gauge | Prefixes received from external BGP peer | `site`, `neighbor_name`, `peer_ip`, `peer_asn`, `softgate`, `vpc` |

### 🌡️ Engine 3: MongoDB Telescope (Environmental & Hardware Health)
| Metric Name | Type | Description | Key Enriched Labels |
| :--- | :--- | :--- | :--- |
| `netris_sensor_temperature_celsius` | Gauge | Thermal sensor readings in °C | `site`, `device_name`, `sensor_name`, `sensor_type` (asic, chassis) |
| `netris_sensor_fan_speed_rpm` | Gauge | Fan tray tachometer speed in RPM | `site`, `device_name`, `fan_name` |
| `netris_sensor_psu_status` | Gauge | Power Supply Unit (PSU) operational status | `site`, `device_name`, `psu_id` |
| `netris_port_bit_error_rate` | Gauge | Physical layer Bit Error Rate (Pre/Post-FEC BER) | `site`, `device_name`, `port` |
| `netris_daemon_health_status` | Gauge | Switch NOS critical daemons (`switchd`, `frr`, `syscd`)| `site`, `device_name`, `daemon_name` |
| `netris_agent_heartbeat` | Gauge | Netris node agent heartbeat liveness | `site`, `device_name`, `device_role`, `fabric_type` |
| `netris_node_component_health` | Gauge | Continuous hardware subcomponent diagnostics | `site`, `device_name`, `device_role`, `fabric_type`, `check_name`, `detail` |
| `netris_topology_wiring_valid` | Gauge | Continuous Active Assurance: LLDP cabling validation | `site`, `device_name`, `port`, `message` |
| `netris_bgp_session_state` | Gauge | Underlay fabric BGP session consistency | `site`, `device_name`, `port`, `bgp_type`, `peer_info` |

---

## 8. Pre-Sales & Demo Talk Track

When demonstrating this integration to prospective customers:

1. **Instant, Production-Grade Demo Environment:**
   > *"Notice how the dashboard doesn't start with blank or flat charts. With one command (`./start.sh --sim`), we synthesize 90 minutes of high-resolution historical telemetry across all 86 devices, switches, GPU servers, and transits, with real-time streaming taking over immediately."*
2. **The Context Gap in Legacy Monitoring:**
   > *"If an SRE looks at a traditional SNMP dashboard and sees `swp1s0 on 10.253.128.11 has drops`, they have to spend 20 minutes tracing spreadsheets. With our enriched Prometheus exporter, Grafana immediately shows that `swp1s0` is connected to GPU server `hgx-pod00-su0-h09` under the `slurm-job-1002` cluster."*
3. **Proactive Cable Assurance:**
   > *"Point out the LLDP Cabling Validation panel. Netris Continuous Active Assurance detects miswired cables and bad transceivers immediately upon physical connection, preventing packet drops from failing multi-day training runs."*
