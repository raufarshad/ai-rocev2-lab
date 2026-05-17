# Streaming Telemetry Stack

A gNMI based streaming telemetry pipeline for the AI fabric, collecting 
real time fabric state and exposing it via Grafana dashboards.

## Architecture
Arista cEOS switches (6x) [gNMI streaming on :6030] gnmic collector
│
│ exposes as
│ Prometheus metrics
▼
Prometheus (TSDB)
│
│ scraped by
▼
Grafana
(dashboards)

## Components

1 **gnmic**   gNMI client subscribing to switch state in stream mode
2 **Prometheus**   Time-series database, 15-second scrape interval
3 **Grafana**   Visualization layer with provisioned Prometheus datasource

## Prerequisites

1. cEOS switches with gNMI enabled:
   
management api gnmi
transport grpc default
no shutdown

3. Docker and Docker Compose installed on the collector host

4. Network reachability from collector to switches on port 6030 (gNMI)

## Usage

```bash
cd telemetry/
docker compose up -d

# Verify all containers are running
docker compose ps

# Watch gnmic subscribe to switches
docker logs gnmic-collector --tail 20

# Verify Prometheus is scraping gnmic
# Browse to http://<host-ip>:9090/targets
# gnmic target should show UP

# Access Grafana dashboards
# Browse to http://<host-ip>:3000
# Default credentials: admin / admin

## Customization

- Update "prometheus.yml" with your actual host IP for the gnmic target
- Add or modify subscription paths in "gnmic-config.yml" per the
  OpenConfig YANG model
- Add additional dashboards to "grafana/dashboards/"

## Architecture decision: gnmic over Telegraf

Chose gnmic as the collector because it's purpose-built for gNMI (the protocol Arista, Cisco, and Juniper all use for streaming telemetry). Telegraf works but adds an unnecessary translation layer. gnmic also produces cleaner metric 
names for AI fabric use cases.

## What this lab does NOT show

Production AI fabric operators monitor additional metrics not exposed by cEOS:
- PFC pause frame counts per priority
- ECN-marked packet counts per queue
- Per-queue depth at threshold crossings
- DLB rebalancing events

These require hardware silicon. Full telemetry validation requires hardware lab access (Arista 7280R3/7388X or Cisco Nexus 9300-FX2+).
