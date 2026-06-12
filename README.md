# AI/ML Data Center Fabric Reference Implementation

> Public reference build of an AI/ML training fabric: design, automation, validation, and observability end to end on Arista cEOS in containerlab.
> Built and documented as a network architect's deep-dive into modern AI infrastructure networking. Companion to the [LinkedIn build series](https://www.linkedin.com/in/raufarshad/).

![status](https://img.shields.io/badge/status-v1.0-blue)
![protocols](https://img.shields.io/badge/protocols-EVPN%20VXLAN%20%7C%20eBGP%20%7C%20RoCEv2-green)
![automation](https://img.shields.io/badge/automation-Ansible%20%7C%20pyATS-orange)
![telemetry](https://img.shields.io/badge/telemetry-gNMI%20%7C%20Prometheus%20%7C%20Grafana-purple)

## What this is

A complete, working reference implementation of a modern AI/ML training fabric, built from the ground up on Arista cEOS. The fabric design follows patterns documented in:

- The Cisco AI/ML Data Center Networking Blueprint (CVD)
- Arista AI Networking design guides
- Meta's SIGCOMM 2024 paper on RoCE for distributed AI training
- NVIDIA Spectrum-X reference architectures

Every layer is documented with the rationale behind the design decision, automated for repeatable deployment, validated by an automated test framework, and instrumented for production-grade observability.

This repository is the practical artifact of pivoting a 13-year enterprise data center networking career toward AI infrastructure. It is meant as both a learning resource for other network engineers making the same pivot, and as a demonstration of the depth I bring to AI fabric architecture work.

## What it demonstrates

- **AI fabric architecture**  2-spine / 4-leaf Clos, eBGP-everywhere underlay, EVPN VXLAN overlay with symmetric IRB, anycast gateway, BFD sub-second convergence
- **RoCEv2 QoS design**  DSCP/CoS marking, PFC/ECN thresholds aligned to the Cisco AI/ML CVD and Meta SIGCOMM 2024 findings
- **DLB design**  flowlet detection, dynamic load balancing for elephant flows, VXLAN inner-header hashing rationale
- **Infrastructure as code**  idempotent Ansible roles for base config, underlay, and overlay; inventory models the topology as data
- **Automated validation**  Cisco pyATS framework with 5 test cases  covering BGP, ECMP, EVPN, VTEP discovery, and end-to-end connectivity
- **Streaming telemetry**  gNMI subscriptions on all 6 switches, gnmic collector, Prometheus storage, Grafana dashboards
- **Multi-vendor portability**  Cisco NX-OS syntax equivalence documented for every major design element
- **Operational maturity**  runbook, recovery procedures, scale-out patterns documented for handover

## Topology

<img width="971" height="792" alt="image" src="https://github.com/user-attachments/assets/3197a0d2-5981-4244-9e7a-6a935c800655" />



| Component       | Count | Role                                          |
|-----------------|-------|-----------------------------------------------|
| Spine switches  | 2     | Arista cEOS, transit-only, shared ASN 65000   |
| Leaf switches   | 4     | Arista cEOS, VTEP, unique ASN 65021-65024     |
| GPU servers     | 4     | Ubuntu containers, one per rail               |
| Fabric links    | 8     | Full mesh between spine and leaf layers       |
| Automation host | 1     | Ansible, pyATS, telemetry stack               |

See [`docs/ip-schema.md`](docs/ip-schema.md) for full addressing.

## Repository structure

```
.
├── ai-fabric.clab.yml                 # containerlab topology
├── configs/
│   ├── day6-bgp-underlay/             # Manual configs (learning phase)
│   └── day7-evpn-overlay/             #
├── ansible/                           # Infrastructure as code
│   ├── ansible.cfg
│   ├── inventory/hosts.yml            # Topology modeled as data
│   ├── roles/
│   │   ├── eos_base/                  # Hostname, loopbacks
│   │   ├── eos_underlay/              # eBGP underlay
│   │   └── eos_overlay/               # EVPN VXLAN overlay
│   └── playbooks/
│       ├── 00-base.yml
│       ├── 01-underlay.yml
│       └── 02-overlay.yml
├── validation/                        # Automated testing
│   ├── testbed.yml                    # pyATS topology definition
│   ├── tests/
│   │   ├── test_underlay.py           # BGP + ECMP validation
│   │   └── test_overlay.py            # EVPN + VTEP + ping validation
│   └── jobs/full_fabric_validation.py # Test orchestration
├── telemetry/                         # Observability stack
│   ├── docker-compose.yml             # gnmic + Prometheus + Grafana
│   ├── gnmic/gnmic-config.yml
│   ├── prometheus/prometheus.yml
│   └── grafana/provisioning/
├── docs/                              # Design documentation
│   ├── architecture.md                # Design decisions + rationale
│   ├── ip-schema.md                   # Addressing, ASNs, VLANs, VNIs
│   ├── qos-design.md                  # RoCEv2 QoS, PFC/ECN thresholds
│   ├── dlb-design.md                  # Dynamic load balancing
│   ├── operations-runbook.md          # Day-2 ops, troubleshooting
│   └── cisco-vs-arista-syntax.md      # Multi-vendor translation
└── journal/                           # Build journal entries
    ├── day7-evpn-overlay.md
    └── day12-telemetry.md
```

## Documentation index

The documentation is the primary deliverable. Read these in order to follow the design end to end:

1. **[Architecture overview](docs/architecture.md)** — design decisions and rationale. Start here. Explains *why* each protocol choice was made.
2. **[IP and numbering schema](docs/ip-schema.md)** — ASNs, loopbacks, VLANs, VNIs, addressing. Reference for extending the design.
3. **[RoCEv2 QoS design](docs/qos-design.md)** — PFC/ECN thresholds, DSCP markings, why each value was chosen, citations to source papers.
4. **[Dynamic load balancing](docs/dlb-design.md)** — flowlet DLB, ECMP limitations for AI workloads, VXLAN hashing considerations.
5. **[Operations runbook](docs/operations-runbook.md)** — day-2 health checks, common failures, recovery procedures, adding new leaves.
6. **[Cisco NX-OS vs Arista EOS syntax](docs/cisco-vs-arista-syntax.md)** — the same design implemented in Cisco NX-OS, side-by-side translation.

## How to reproduce

This lab runs on a single Linux host with sufficient CPU/RAM (8 vCPU, 16GB RAM minimum). Tested on Ubuntu 26.04 with Python 3.14.

### Prerequisites

- Linux host (Ubuntu 22.04+ recommended)
- Docker and containerlab installed
- Arista cEOS image (downloaded from arista.com — requires free account)
- Python 3.10+ with pip
- ~20GB free disk

### 1. Deploy the fabric

```bash
git clone https://github.com/raufarshad/ai-rocev2-lab.git
cd ai-rocev2-lab

# Import the cEOS image
docker import cEOS-lab-4.32.2F.tar.xz ceos:4.32.2F

# Deploy the topology
sudo containerlab deploy -t ai-fabric.clab.yml
```

### 2. Apply configuration via Ansible

```bash
cd ansible
python3 -m venv venv && source venv/bin/activate
pip install ansible arista.eos paramiko

ansible-playbook playbooks/00-base.yml
ansible-playbook playbooks/01-underlay.yml
ansible-playbook playbooks/02-overlay.yml
```

Expected result: all hosts return `ok` with `changed=0` on a second run
(idempotency verified).

### 3. Validate

```bash
cd ../validation
pip install pyats[full]
pyats run job jobs/full_fabric_validation.py --testbed-file testbed.yml
```

Expected result: BGP sessions Established, ECMP paths present, EVPN
sessions Established, VTEPs discovered.

### 4. Bring up telemetry (optional)

```bash
cd ../telemetry
docker compose up -d
```

Browse to `http://<host>:9090/targets` to see Prometheus scraping gnmic.
Browse to `http://<host>:3000` (admin/admin) to access Grafana.

## What this lab does NOT validate

I've been deliberate about this. The lab uses Arista cEOS in containerlab,
which is software emulation. Control plane behavior is faithfully
reproduced; silicon-dependent behavior is not.

The following are documented in the design but **not** validated in this
environment:

- PFC pause frame generation and consumption
- ECN marking at queue depth thresholds
- DLB flowlet detection and per-flowlet rebalancing
- DCQCN response loop on host NICs
- Real congestion behavior under sustained AI workload

Threshold values for QoS and DLB are documented with citations to source
material (Cisco AI/ML CVD, Meta SIGCOMM 2024). Real validation requires
hardware (Arista 7280R3/7388X, Cisco Nexus 9300-FX/GX/H, or equivalent).

Anyone claiming to validate these on containerlab is overselling. Knowing
this gap exists — and being explicit about it — is part of what a senior
fabric architect should bring to an AI infrastructure conversation.

## Build journey

This was built incrementally over ~3 months, documented publicly on
LinkedIn as a learning-in-public exercise.

| Phase   | Focus                                              |
|---------|----------------------------------------------------|
| Days 1-7 | Foundation: containerlab, BGP underlay, EVPN overlay |
| Days 8-9 | RoCEv2 QoS and DLB design documentation              |
| Days 10-11 | Ansible automation and pyATS validation framework |
| Day 12  | Streaming telemetry stack (gNMI + Prometheus + Grafana) |
| Day 13  | Architecture, IP schema, and operations documentation |
| Day 14  | Cisco NX-OS syntax equivalence                     |
| Day 16  | v1.0 release                                       |

Read the LinkedIn article series for the narrative version:

- [Part 1 — Series kickoff](https://www.linkedin.com/in/raufarshad/)
- [Part 2 — End-to-end traffic flowing](https://www.linkedin.com/in/raufarshad/)
- [Part 3 — Automation, validation, and a 12-day recovery test](https://www.linkedin.com/in/raufarshad/)

## About the author

Rauf Arshad — Network Architect, dual CCIE (Security, Service Provider),
13 years in enterprise and service provider data center networking.
Currently consulting on production VXLAN EVPN deployments while
transitioning toward AI/ML infrastructure architecture roles.

- LinkedIn: [linkedin.com/in/raufarshad](https://www.linkedin.com/in/raufarshad/)
- GitHub: [github.com/raufarshad](https://github.com/raufarshad)

If you're working on AI fabric architecture, customer-facing solutions
engineering for AI infrastructure, or NeoCloud network design, I'd value
the conversation. Open to discussing design decisions in this repo, or
adjacent topics.

## License

This work is shared for educational and reference purposes. Configurations,
designs, and documentation in this repository may be reused with
attribution. Cited material (Cisco CVD, Meta SIGCOMM, NVIDIA whitepapers)
belongs to its respective authors.
