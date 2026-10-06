#!/usr/bin/env python3
"""
Netris Switch & Fabric Isolation Suite
A multi-stage, interactive CLI utility to audit, demonstrate, and verify
multi-tenancy isolation across North-South (EVPN/VXLAN) and East-West (Pure VRF) fabrics
on live Netris Controller infrastructure.
"""

import argparse
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import questionary
from questionary import Choice, Separator, Style
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from config_manager import load_config, settings_menu
from netris_api import NetrisAPI
from switch_inspector import SwitchInspector
from ping_orchestrator import PingOrchestrator, parse_su_host
import ui

console = Console()

custom_style = Style([
    ("qmark", "fg:#00d7af bold"),
    ("question", "bold fg:#ffffff"),
    ("answer", "fg:#00ffff bold"),
    ("pointer", "fg:#00d7af bold"),
    ("highlighted", "fg:#00d7af bold"),
    ("selected", "fg:#00d7af"),
    ("separator", "fg:#6c6c6c"),
    ("instruction", "fg:#8a8a8a italic"),
    ("text", "fg:#e4e4e4"),
])


def stage1_vpc_and_topology(
    api: NetrisAPI,
    selected_vpc_id: int,
    verbose: bool = False
) -> Tuple[Dict[str, Any], Dict[str, List[Dict[str, Any]]]]:
    """Stage 1: VPC Architecture & Physical Fabric Topology Screen."""
    ui.print_banner(subtitle="Stage 1 of 4: VPC Architecture & Physical Fabric Topology", verbose=verbose)

    if verbose:
        ui.render_demo_commentary(
            stage_title="VPC Provisioning & Physical Port Mapping",
            explanation=(
                f"The Netris Controller provisions isolated multi-tenant VPC environments on demand. "
                f"Here we inspect the compute fleet allocated to VPC-{selected_vpc_id} and resolve their "
                f"physical leaf switch attachments across both East-West (GPU RoCE) and North-South planes."
            ),
            key_points=[
                "Each tenant VPC receives dedicated V-Nets and IP subnets.",
                "Hosts are physically wired to Top-of-Rack leaf switches running NVIDIA Cumulus Linux.",
                "Netris Controller automatically provisions switch port configs and VLAN/VNI bindings."
            ]
        )

    with console.status("[bold cyan]Querying Netris Controller for VPC cluster and link topology...[/bold cyan]", spinner="dots"):
        vpc_info = api.get_vpc_details(selected_vpc_id)
        servers = vpc_info.get("servers", [])
        server_names = [s["name"] for s in servers]
        topology_map = api.resolve_server_switch_links(server_names)

    # Clear Device Context
    cluster = vpc_info.get("cluster") or {}
    tenant_name = cluster.get("vpc", {}).get("tenant", {}).get("name", "Target Tenant")
    server_summary = f"{servers[0]['name']} .. {servers[-1]['name']} ({len(servers)} hosts)" if servers else "None"
    ui.render_device_context(
        "Target Environment & Device Inventory",
        [
            ("Target VPC", f"VPC-{selected_vpc_id} ({cluster.get('vpc', {}).get('name', 'N/A')})"),
            ("Tenant Assignment", tenant_name),
            ("Compute Fleet", server_summary),
            ("Physical Fabric", "NVIDIA Cumulus ToR Leaf Switches (Pure VRF East-West + EVPN North-South)")
        ]
    )

    ui.render_vpc_overview(vpc_info)

    return vpc_info, topology_map


def stage_switch_selection_menu(
    cfg: Dict[str, Any],
    selected_vpc_id: int,
    other_vpc_id: Optional[int],
    topology_map: Dict[str, List[Dict[str, Any]]],
    verbose: bool = False
) -> str:
    """
    Switch Device Inspection: Allows selecting any switch in the fabric to view its
    hardware isolation profile and mechanisms instantly without live SSH interrogation.
    Returns: 'ping' if the user chooses to proceed to ping testing, or 'back' to return.
    """
    # Discover ports mapped to this VPC per switch
    switches_found: Dict[str, Dict[str, Any]] = {}
    for host_name, links in topology_map.items():
        for l in links:
            s_name = l.get("switch_name")
            if s_name:
                if s_name not in switches_found:
                    switches_found[s_name] = {
                        "name": s_name,
                        "ports": set(),
                        "fabric_role": l.get("fabric_role", "Leaf Switch")
                    }
                if l.get("switch_port"):
                    switches_found[s_name]["ports"].add(l.get("switch_port"))

    # Switch profiles with detailed hardware capability mapping
    switch_profiles = {
        "ns-leaf-0": {
            "name": "ns-leaf-0",
            "ip": "10.3.0.1",
            "model": "NVIDIA Spectrum-3 SN3700C (32x100GbE)",
            "role": "North-South Leaf Switch",
            "fabric": "North-South EVPN / VXLAN Boundary",
            "vpc_id": selected_vpc_id,
            "ports": sorted(list(switches_found.get("ns-leaf-0", {}).get("ports", ["swp1", "swp2", "swp3"])))
        },
        "leaf-pod00-su0-r0": {
            "name": "leaf-pod00-su0-r0",
            "ip": "10.253.0.1",
            "model": "NVIDIA Spectrum-3 SN3700C (32x100GbE)",
            "role": "East-West RoCE Leaf (Rails 0 & 4)",
            "fabric": "East-West Pure VRF / L3VPN (RoCEv2)",
            "vpc_id": selected_vpc_id,
            "ports": sorted(list(switches_found.get("leaf-pod00-su0-r0", {}).get("ports", ["swp1s0", "swp2s0"])))
        },
        "leaf-pod00-su0-r1": {
            "name": "leaf-pod00-su0-r1",
            "ip": "10.253.0.2",
            "model": "NVIDIA Spectrum-3 SN3700C (32x100GbE)",
            "role": "East-West RoCE Leaf (Rails 1 & 5)",
            "fabric": "East-West Pure VRF / L3VPN (RoCEv2)",
            "vpc_id": selected_vpc_id,
            "ports": sorted(list(switches_found.get("leaf-pod00-su0-r1", {}).get("ports", ["swp1s0", "swp2s0"])))
        },
        "leaf-pod00-su0-r2": {
            "name": "leaf-pod00-su0-r2",
            "ip": "10.253.0.3",
            "model": "NVIDIA Spectrum-3 SN3700C (32x100GbE)",
            "role": "East-West RoCE Leaf (Rails 2 & 6)",
            "fabric": "East-West Pure VRF / L3VPN (RoCEv2)",
            "vpc_id": selected_vpc_id,
            "ports": sorted(list(switches_found.get("leaf-pod00-su0-r2", {}).get("ports", ["swp1s0", "swp2s0"])))
        },
        "leaf-pod00-su0-r3": {
            "name": "leaf-pod00-su0-r3",
            "ip": "10.253.0.4",
            "model": "NVIDIA Spectrum-3 SN3700C (32x100GbE)",
            "role": "East-West RoCE Leaf (Rails 3 & 7)",
            "fabric": "East-West Pure VRF / L3VPN (RoCEv2)",
            "vpc_id": selected_vpc_id,
            "ports": sorted(list(switches_found.get("leaf-pod00-su0-r3", {}).get("ports", ["swp1s0", "swp2s0"])))
        }
    }

    while True:
        ui.print_banner(subtitle="Switch Device Inspection (Select Switch Profile)", verbose=verbose)

        switch_choices = [
            Separator("── North-South EVPN / VXLAN Leaf Switch ─────────────"),
            Choice(
                title="ns-leaf-0          (NVIDIA Spectrum-3 SN3700C - 10.3.0.1)",
                value="ns-leaf-0",
                description="North-South EVPN/VXLAN VNI Isolation Boundary"
            ),
            Separator("── East-West GPU RoCE Fabric Leaf Switches ──────────"),
            Choice(
                title="leaf-pod00-su0-r0  (Pure VRF RoCE Leaf - Rail 0 & 4)",
                value="leaf-pod00-su0-r0",
                description="Dedicated GPU East-West Pure VRF Partitioning"
            ),
            Choice(
                title="leaf-pod00-su0-r1  (Pure VRF RoCE Leaf - Rail 1 & 5)",
                value="leaf-pod00-su0-r1",
                description="Dedicated GPU East-West Pure VRF Partitioning"
            ),
            Choice(
                title="leaf-pod00-su0-r2  (Pure VRF RoCE Leaf - Rail 2 & 6)",
                value="leaf-pod00-su0-r2",
                description="Dedicated GPU East-West Pure VRF Partitioning"
            ),
            Choice(
                title="leaf-pod00-su0-r3  (Pure VRF RoCE Leaf - Rail 3 & 7)",
                value="leaf-pod00-su0-r3",
                description="Dedicated GPU East-West Pure VRF Partitioning"
            ),
            Separator("─────────────────────────────────────────────────────"),
            Choice("Proceed to Ping Isolation Testing ➔", value="proceed_ping"),
            Choice("« Return to Stage 1 Overview", value="back")
        ]

        selected_sw = questionary.select(
            "Select a switch to view its hardware isolation profile (no live interrogation):",
            choices=switch_choices,
            style=custom_style
        ).ask()

        if selected_sw == "proceed_ping":
            return "ping"
        elif selected_sw in ("back", None):
            return "back"

        # Show switch profile card instantly
        profile = switch_profiles.get(selected_sw, {
            "name": selected_sw,
            "ip": "Dynamic",
            "model": "NVIDIA Spectrum-3 SN3700C (32x100GbE)",
            "role": "Fabric Leaf Switch",
            "fabric": "VPC Fabric Plane",
            "vpc_id": selected_vpc_id,
            "ports": []
        })
        ui.render_switch_hardware_profile(profile)

        post_action = questionary.select(
            "Next Action:",
            choices=[
                Choice("Proceed to Ping Isolation Testing ➔ (Direct Demo Flow)", value="proceed_ping"),
                Choice("Select Another Switch", value="again"),
                Choice("(Optional) Run Live vtysh Switch Interrogation (Show EVPN VNI)", value="interrogate"),
                Choice("« Return to Stage 1 Overview", value="back")
            ],
            style=custom_style
        ).ask()

        if post_action == "proceed_ping":
            return "ping"
        elif post_action == "back":
            return "back"
        elif post_action == "interrogate":
            stage2_switch_hardware_evidence(cfg, selected_vpc_id, other_vpc_id, verbose=verbose)
            sub_next = questionary.select(
                "Next Action:",
                choices=[
                    Choice("Proceed to Ping Isolation Testing ➔", value="proceed_ping"),
                    Choice("« Back to Switch Device Inspection", value="again")
                ],
                style=custom_style
            ).ask()
            if sub_next == "proceed_ping":
                return "ping"


def stage2_switch_hardware_evidence(
    cfg: Dict[str, Any],
    selected_vpc_id: int,
    other_vpc_id: Optional[int],
    verbose: bool = False
):
    """Stage 2: Switch Hardware Evidence (Live vtysh CLI with Engineer Highlights)."""
    ui.print_banner(subtitle="Stage 2 of 4: Live Switch Hardware Isolation Evidence", verbose=verbose)

    if verbose:
        ui.render_demo_commentary(
            stage_title="Top-of-Rack Switch Table Inspection (vtysh CLI)",
            explanation=(
                "Rather than relying purely on Controller state, we now log in directly to the physical leaf switches "
                "over their out-of-band management IPs. This provides indisputable proof from the actual switch ASICs "
                "showing how tenant traffic is partitioned in hardware."
            ),
            key_points=[
                "North-South Switch (ns-leaf-0: 10.3.0.1): Inspects EVPN VXLAN VNI tables.",
                "East-West Switch (leaf-pod00-su0-r0: 10.253.0.1): Inspects Pure VRF kernel routing tables.",
                "Observe the line highlights showing strictly dedicated VNIs and non-overlapping FIB subnets."
            ]
        )

    inspector = SwitchInspector(
        jump_host=cfg["ssh_jump_host"],
        jump_port=cfg["ssh_jump_port"],
        jump_user=cfg["ssh_jump_user"],
        jump_password=cfg["ssh_jump_password"],
        switch_user=cfg.get("ssh_switch_user", "cumulus"),
        switch_key_path=cfg.get("ssh_switch_key_path", "/home/ubuntu/.ssh/id_rsa")
    )

    try:
        with console.status("[bold cyan]Querying physical switch (ns-leaf-0: 10.3.0.1) over management plane (vtysh)...[/bold cyan]", spinner="dots"):
            ns_data = inspector.inspect_ns_evpn_tables(selected_vpc_id)
            ew_data = {}
            if verbose:
                ew_data = inspector.inspect_ew_vrf_tables(selected_vpc_id, other_vpc_id)

        ui.render_raw_switch_evidence(ns_data, ew_data, verbose=verbose)
    except Exception as e:
        console.print(f"[bold red]Error during switch inspection:[/bold red] {e}")
    finally:
        inspector.close()


def stage3_intra_vpc_pings(
    orchestrator: PingOrchestrator,
    servers: List[Dict[str, Any]],
    selected_vpc_id: int,
    verbose: bool = False
) -> List[Dict[str, Any]]:
    """Stage 3: Intra-VPC Cluster Connectivity Screen with Drill-Down."""
    ui.print_banner(subtitle="Stage 3 of 4: Intra-VPC Cluster Connectivity Audit", verbose=verbose)

    if verbose:
        ui.render_demo_commentary(
            stage_title="Intra-Tenant Wire-Speed Fabric Probing (cluster-ping.sh)",
            explanation=(
                "We now execute wire-speed ping probes across all compute nodes inside this VPC. "
                "Each test probes all 8 RoCEv2 GPU rails (East-West fabric) plus North-South bond0 and IPMI. "
                "You can review the high-level matrix, and then select any specific host pair to drill down."
            ),
            key_points=[
                f"Probing leader node ({servers[0]['name']}) against all {len(servers) - 1} peer nodes in the VPC.",
                "Validates that all 8 RoCE rails operate at line rate with zero packet drops.",
                "High-level matrix gives an executive summary; drill-down gives low-level telemetry."
            ]
        )

    leader_name = servers[0]["name"]
    peer_names = [s["name"] for s in servers[1:]]
    ui.render_device_context(
        "Intra-Cluster Wire-Speed Probe Devices",
        [
            ("Probing Leader Host", f"[bold white]{leader_name}[/bold white] [dim](Target Tenant VPC-{selected_vpc_id})[/dim]"),
            ("Peer Target Fleet", f"[bold white]{', '.join(peer_names[:4])}{' ...' if len(peer_names) > 4 else ''}[/bold white] ({len(peer_names)} nodes)"),
            ("Fabric Planes Probed", "8x East-West RoCEv2 GPU Rails + North-South bond0 (EVPN)"),
            ("Underlay Switches", "leaf-pod00-su0-r0..r3 (GPU Fabric) | ns-leaf-0 (Management/EVPN)")
        ]
    )

    console.print(f"[bold green]Running cluster-ping across all {len(servers)} nodes in the VPC...[/bold green]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Testing intra-VPC cluster reachability...", total=len(servers) - 1)

        def cb(desc, current, total):
            progress.update(task, description=f"[cyan]Probing {desc} ({current}/{total})...", completed=current)

        intra_results = orchestrator.execute_intra_vpc_connectivity_matrix(servers, progress_callback=cb)

    ui.render_intra_vpc_ping_matrix(intra_results)

    # Interactive Drill-down Menu
    while True:
        drill_choices = []
        for idx, item in enumerate(intra_results):
            drill_choices.append(
                Choice(
                    title=f"Drill down into: {item['source']} ➔ {item['target']} (8 Rails + NS)",
                    value=idx
                )
            )
        drill_choices.append(Separator("─────────────────────────────────────────────────────"))
        drill_choices.append(Choice("Proceed to Stage 4: Cross-VPC Multi-Target Isolation Test ➔", value="next"))

        pick = questionary.select(
            "Select an option to inspect low-level rail telemetry or proceed:",
            choices=drill_choices,
            style=custom_style
        ).ask()

        if pick == "next" or pick is None:
            break
        else:
            ui.render_ping_drilldown(intra_results[pick])
            questionary.press_any_key_to_continue("Press any key to return to drill-down list...").ask()
            ui.print_banner(subtitle="Stage 3 of 4: Intra-VPC Cluster Connectivity Audit", verbose=verbose)
            ui.render_intra_vpc_ping_matrix(intra_results)

    return intra_results


def stage4_multi_target_cross_vpc(
    orchestrator: PingOrchestrator,
    source_node: str,
    api: NetrisAPI,
    selected_vpc_id: int,
    verbose: bool = False
):
    """Stage 4: Multi-Target Cross-VPC Isolation Drop Verification Screen."""
    ui.print_banner(subtitle="Stage 4 of 4: Multi-Target Cross-VPC Isolation Audit", verbose=verbose)

    if verbose:
        ui.render_demo_commentary(
            stage_title="Cross-Tenant Hardware Drop Verification",
            explanation=(
                "To prove complete multi-tenancy, we command our VPC node to attempt communication "
                "with multiple foreign hosts across the datacenter (hosts belonging to other tenant VPCs "
                "and separate physical Scalable Units). Hardware ASICs must drop 100% of probes on all planes."
            ),
            key_points=[
                "Probes multiple foreign destinations across different subnets and fabric pods.",
                "Proves that both East-West RoCE and North-South EVPN drop unauthorized traffic at wire speed.",
                "Confirms zero cross-tenant leakage across the entire datacenter fabric."
            ]
        )

    # Identify multi-targets across the fabric
    clusters = api.get_server_clusters()
    foreign_targets: List[Tuple[str, str]] = []

    for c in clusters:
        cVpc = c.get("vpc") or {}
        if cVpc.get("id") != selected_vpc_id:
            c_name = c.get("name", "Other VPC")
            v_id = cVpc.get("id", "N/A")
            for s in c.get("servers", [])[:2]:
                foreign_targets.append((s.get("name"), f"Alternate Tenant ({c_name} - VPC-{v_id})"))

    # Add a host from another SU (remote pod) if available
    foreign_targets.append(("hgx-pod00-su1-h00", "Remote Pod Node (Scalable Unit 1 - External Pod)"))

    target_descriptions = [f"{t[0]} [{t[1]}]" for t in foreign_targets]
    ui.render_device_context(
        "Cross-Tenant Hardware Drop Verification Devices",
        [
            ("Probing Source Device", f"[bold white]{source_node}[/bold white] [dim](Target Tenant VPC-{selected_vpc_id})[/dim]"),
            ("Foreign Target Devices", f"[bold yellow]{', '.join(target_descriptions[:2])}[/bold yellow]"),
            ("Hardware ASICs Tested", "NVIDIA Spectrum-3 / Spectrum-4 ToR Leaf ASICs"),
            ("Expected Verification", "[bold green]100% Hardware Drop (Zero Cross-Tenant Leakage)[/bold green]")
        ]
    )

    console.print(f"[bold red]Probing {len(foreign_targets)} foreign targets across the fabric from {source_node}...[/bold red]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[yellow]Injecting cross-tenant probe packets...", total=len(foreign_targets))

        def cb(desc, current, total):
            progress.update(task, description=f"[yellow]Probing {desc} ({current}/{total})...", completed=current)

        iso_results = orchestrator.execute_multi_cross_vpc_isolation_check(
            source_node,
            foreign_targets,
            progress_callback=cb
        )

    # Directly display highlighted ping telemetry for the Alternate Tenant simulation
    alt_tenant_item = next(
        (item for item in iso_results if "Alternate Tenant" in item.get("description", "")),
        iso_results[0] if iso_results else None
    )
    if alt_tenant_item:
        ui.render_isolation_ping_evidence(source_node, alt_tenant_item, selected_vpc_id)

    # Multi-target summary card
    ui.render_multi_cross_vpc_isolation_card(iso_results)

    # Interactive Drill-down Menu for Stage 4 targets
    while True:
        drill_choices = []
        for idx, item in enumerate(iso_results):
            drill_choices.append(
                Choice(
                    title=f"Inspect low-level drop output: {item['source']} ➔ {item['target']} ({item['description']})",
                    value=idx
                )
            )
        drill_choices.append(Separator("─────────────────────────────────────────────────────"))
        drill_choices.append(Choice("Complete Audit and Return to Main Menu ➔", value="done"))

        pick = questionary.select(
            "Select a target to inspect low-level drop telemetry or complete:",
            choices=drill_choices,
            style=custom_style
        ).ask()

        if pick == "done" or pick is None:
            break
        else:
            ui.render_isolation_ping_evidence(source_node, iso_results[pick], selected_vpc_id)
            questionary.press_any_key_to_continue("Press any key to return to drill-down list...").ask()
            ui.print_banner(subtitle="Stage 4 of 4: Multi-Target Cross-VPC Isolation Audit", verbose=verbose)
            ui.render_multi_cross_vpc_isolation_card(iso_results)


# ----------------------------------------------------------------------
# Master Isolation Audit Workflow
# ----------------------------------------------------------------------
def run_isolation_workflow(verbose: bool = False):
    """Main workflow executing the multi-stage switch & fabric isolation audit."""
    ui.print_banner(verbose=verbose)
    cfg = load_config()

    console.print("[bold yellow]Connecting to Netris Controller...[/bold yellow]")
    try:
        api = NetrisAPI(cfg["netris_url"], cfg["netris_username"], cfg["netris_password"])
        with console.status("[bold cyan]Authenticating and querying VPC inventory...[/bold cyan]", spinner="dots"):
            api.login()
            vpcs = api.get_vpcs()
    except Exception as e:
        console.print(f"\n[bold red]Error connecting to Netris Controller:[/bold red] {e}")
        console.print("[yellow]Please check your credentials in the Settings menu.[/yellow]\n")
        questionary.press_any_key_to_continue().ask()
        return

    if not vpcs:
        console.print("[bold red]No active VPCs found on this Netris Controller.[/bold red]")
        questionary.press_any_key_to_continue().ask()
        return

    # Select VPC (Searchable, use_jk_keys=False)
    vpc_choices = []
    for v in vpcs:
        vid = v.get("id")
        vname = v.get("name")
        vpc_choices.append(
            Choice(
                title=f"VPC-{vid}: {vname} (Tenant: {v.get('tenant', {}).get('name', 'N/A')})",
                value=vid,
                description=f"Inspect multi-tenancy and switch isolation for {vname}"
            )
        )
    vpc_choices.append(Separator("─────────────────────────────────────────────────────"))
    vpc_choices.append(Choice("« Cancel and Return to Main Menu", value="cancel"))

    selected_vpc_id = questionary.select(
        "Select target VPC to audit for switch & fabric isolation:",
        choices=vpc_choices,
        style=custom_style,
        use_search_filter=True,
        use_jk_keys=False
    ).ask()

    if not selected_vpc_id or selected_vpc_id == "cancel":
        return

    # Identify alternate VPC for comparative analysis
    other_vpc_id = None
    for v in vpcs:
        if v.get("id") != selected_vpc_id:
            other_vpc_id = v.get("id")
            break

    # ==================================================================
    # SCREEN 1: VPC Architecture & Provisioned Topology
    # ==================================================================
    vpc_info, topology_map = stage1_vpc_and_topology(api, selected_vpc_id, verbose=verbose)
    servers = vpc_info.get("servers", [])

    topology_expanded = False
    proceed_to_pings = False

    while True:
        topo_label = "[Collapse Physical Fabric Topology Table]" if topology_expanded else "[Expand / View Physical Fabric Topology Table]"
        choices = [
            Choice("Proceed to Ping Isolation Testing ➔ (Direct Demo Flow)", value="ping"),
            Choice("Switch Device Inspection (Select Switch Profile) ➔", value="switch"),
            Choice(topo_label, value="toggle_topology"),
            Separator("─────────────────────────────────────────────────────"),
            Choice("« Return to Main Menu", value="menu")
        ]

        step1_action = questionary.select(
            "Select Next Action:",
            choices=choices,
            style=custom_style
        ).ask()

        if step1_action == "menu" or step1_action is None:
            return
        elif step1_action == "toggle_topology":
            topology_expanded = not topology_expanded
            ui.print_banner(subtitle="Stage 1 of 4: VPC Architecture & Physical Fabric Topology", verbose=verbose)
            ui.render_vpc_overview(vpc_info)
            if topology_expanded:
                if servers:
                    ui.render_host_switch_topology(topology_map)
                else:
                    console.print("[bold yellow]Note: This VPC has no member servers allocated yet.[/bold yellow]")
        elif step1_action == "switch":
            result = stage_switch_selection_menu(cfg, selected_vpc_id, other_vpc_id, topology_map, verbose=verbose)
            if result == "ping":
                proceed_to_pings = True
                break
            # If "back", refresh Stage 1 view
            ui.print_banner(subtitle="Stage 1 of 4: VPC Architecture & Physical Fabric Topology", verbose=verbose)
            ui.render_vpc_overview(vpc_info)
            if topology_expanded and servers:
                ui.render_host_switch_topology(topology_map)
        elif step1_action == "ping":
            proceed_to_pings = True
            break

    if not proceed_to_pings:
        return

    # ==================================================================
    # SCREEN 3 & 4: Fabric Pings & Multi-Target Isolation Verification
    # ==================================================================
    if not servers:
        console.print("[bold yellow]This VPC has no compute nodes assigned; skipping ping verification.[/bold yellow]")
        questionary.press_any_key_to_continue().ask()
        return

    orchestrator = PingOrchestrator(
        jump_host=cfg["ssh_jump_host"],
        jump_port=cfg["ssh_jump_port"],
        jump_user=cfg["ssh_jump_user"],
        jump_password=cfg["ssh_jump_password"]
    )

    try:
        # SCREEN 3: Intra-VPC cluster ping with drill-down
        stage3_intra_vpc_pings(orchestrator, servers, selected_vpc_id, verbose=verbose)

        # SCREEN 4: Multi-Target Cross-VPC Isolation Drop Verification
        stage4_multi_target_cross_vpc(orchestrator, servers[0]["name"], api, selected_vpc_id, verbose=verbose)

    except Exception as e:
        console.print(f"[bold red]Error during ping execution:[/bold red] {e}")
    finally:
        orchestrator.close()

    console.print()
    questionary.press_any_key_to_continue("Audit complete. Press any key to return to main menu...").ask()


def main():
    """Main application loop with command-line argument support and interactive mode toggling."""
    parser = argparse.ArgumentParser(description="Netris Switch & Fabric Isolation Suite")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Run in verbose mode (full architectural briefings and deep dives)"
    )
    parser.add_argument(
        "--terse",
        action="store_true",
        help="Run in terse mode (clean demo mode, default)"
    )
    args, _ = parser.parse_known_args()

    verbose_mode = False
    if args.verbose:
        verbose_mode = True

    while True:
        ui.print_banner(verbose=verbose_mode)

        mode_label = "Verbose (Full Deep Dive)" if verbose_mode else "Terse (Clean Demo)"
        toggle_label = "Switch to Terse Mode (Clean Demo)" if verbose_mode else "Switch to Verbose Mode (Full Deep Dive)"

        action = questionary.select(
            f"Main Menu [Active Mode: {mode_label}]:",
            choices=[
                Choice(f"1. Run Switch & Fabric Isolation Test [{mode_label}]", value="test"),
                Choice(f"2. Toggle Mode: {toggle_label}", value="toggle"),
                Choice("3. Settings (Netris Controller & Jump Host Credentials)", value="settings"),
                Separator("─────────────────────────────────────────────────────"),
                Choice("Exit", value="exit")
            ],
            style=custom_style
        ).ask()

        if action == "test":
            run_isolation_workflow(verbose=verbose_mode)
        elif action == "toggle":
            verbose_mode = not verbose_mode
        elif action == "settings":
            settings_menu()
        elif action in ("exit", None):
            console.print("\n[dim]Exiting Netris Isolation Tool. Goodbye![/dim]\n")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user. Exiting.[/yellow]")
        sys.exit(0)
