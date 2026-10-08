> **[WARNING] Demonstration Code Only**
> This repository contains unsupported demonstration code for architectural illustration. It is a **possible implementation pattern**, not an official Netris product or supported tool. Use at your own risk.

# NetBox ↔ Netris IPAM Sync

Containerised bi-directional synchronisation between NetBox (IPAM/DCIM planning source of truth) and the Netris Controller (network assignment and fabric execution source of truth).

---

## 1. What This Is
This integration solves the "split brain" problem between network planning and execution.
- Integrates **NetBox** and **Netris Controller**.
- Designed for Cloud Architects and Network Engineers automating IPAM.
- Provides a continuous, bi-directional sync loop keeping NetBox IP prefixes and Netris V-Nets perfectly aligned.

---

## 2. How It Works (Under the Hood)
*A step-by-step breakdown of how the code actually executes.*

1. **Initialization:** The `app/` service starts and reads configuration from `.env`.
2. **Authentication:** It authenticates against both the NetBox REST API and the Netris Controller REST API.
3. **State Sync:** It fetches the current IP prefixes from NetBox and compares them to the active V-Nets and subnets in Netris.
4. **Execution:** For every missing prefix in Netris, it executes a POST request to provision a V-Net. For every out-of-band subnet created in Netris, it provisions a matching Prefix in NetBox.
5. **Teardown/Refresh:** The loop repeats continuously, maintaining state alignment.

---

## 3. How to Run It (Quickstart)

### Prerequisites
- Docker & Docker Compose
- API Keys for NetBox and Netris

### Steps
1. **Clone the repository:**
   ```bash
   git clone https://github.com/iamjarvs/netbox-netris-integration.git
   cd netbox-netris-integration
   ```
2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```
3. **Start the tool:**
   ```bash
   ./start.sh
   ```
4. **Stop the tool:**
   ```bash
   ./stop.sh
   ```

---

## 4. How to Build Your Own Experience (For Developers)

If you want to modify this integration or build something similar, here is a roadmap of the codebase:

- **`.env.example`:** Configuration template.
- **`app/main.py`:** The core orchestration loop. Modify this file if you want to change *when* or *how* data is processed.
- **`app/netris_client.py`:** Contains the raw API calls to Netris.
- **`app/netbox_client.py`:** Contains the raw API calls to NetBox.

**Extending this code:**
To add support for syncing Route Targets or VRFs, simply copy the existing sync functions in `app/main.py` and point them at the appropriate endpoints in the respective client files.
