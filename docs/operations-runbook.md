# Operations Runbook

Day-2 operational procedures for the AI fabric. The intended audience is a network engineer responsible for keeping the fabric healthy, or a peer evaluating the operational maturity of this design.

## Health verification

### Quick health check (automated)

```bash
cd ~/ai-fabric-lab/validation
source ../ansible/venv/bin/activate
pyats run job jobs/full_fabric_validation.py --testbed-file testbed.yml
```

Expected: all sections PASSED. This runs 5 test cases covering BGP sessions, ECMP paths, EVPN sessions, VTEP discovery, and end-to-end ping. A failure in any section is a real problem worth investigating before proceeding.

### Manual checks (when you suspect a specific issue)

**Underlay BGP health**
```
leaf1#show ip bgp summary
```
All neighbors should show `Estab` state and a prefix count > 0.

**ECMP working**
```
leaf1#show ip route 10.0.0.124
```
Should show 2 next-hops (via both spines). If only 1, ECMP is broken.

**EVPN session health**
```
leaf1#show bgp evpn summary
```
2 sessions to spines, both Established.

**VTEP discovery**
```
leaf1#show vxlan vtep
```
Should show 3 remote VTEPs (the other 3 leaves' Loopback1 addresses).

**MAC table learning**
```
leaf1#show mac address-table
```
Local server MAC on Eth1, remote server MACs via Vx1.

**End-to-end reachability**
```
docker exec clab-ai-fabric-gpu-srv1 ping -c 3 10.100.0.14
```
Should succeed (containerlab is local, sub-ms RTT).

### Telemetry-based health

If the telemetry stack is running, browse to Grafana at `http://<automation-host>:3000`. Look for: all 6 switches visible, BGP session counts consistent, interface bandwidth showing baseline traffic, fabric
interface oper-state all up.

## Adding a new leaf

To add leaf5 to the fabric:

**1. Update inventory** at `ansible/inventory/hosts.yml`:

```yaml
leaf5:
  ansible_host: 192.168.100.25
  loopback0_ip: 10.0.0.25
  loopback1_ip: 10.0.0.125
  bgp_asn: 65025
  role: leaf
  rail: 5
  fabric_links:
    - { local_intf: Ethernet49, remote_node: spine1, remote_intf: Ethernet5, local_ip: 10.1.1.9, peer_ip: 10.1.1.8, peer_asn: 65000 }
    - { local_intf: Ethernet50, remote_node: spine2, remote_intf: Ethernet5, local_ip: 10.1.2.9, peer_ip: 10.1.2.8, peer_asn: 65000 }
```

**2. Update spine1 and spine2 fabric_links** with the new leaf entries.

**3. Add the new switch** to the containerlab topology (or rack hardware).

**4. Run the playbooks** scoped to affected devices:
```bash
cd ~/ai-fabric-lab/ansible && source venv/bin/activate
ansible-playbook playbooks/00-base.yml      --limit "leaf5,spine1,spine2"
ansible-playbook playbooks/01-underlay.yml  --limit "leaf5,spine1,spine2"
ansible-playbook playbooks/02-overlay.yml   --limit "leaf5,spine1,spine2"
```

**5. Validate** (update testbed.yml to include leaf5 first):
```bash
cd ../validation
pyats run job jobs/full_fabric_validation.py --testbed-file testbed.yml
```

## Common failures and resolution

### BGP session not establishing
**Symptoms:** `show ip bgp summary` shows `Idle` or `Active`.
**Diagnose:** interface up? (`show interface Ethernet49`); IP reachable?
(`ping <peer_ip>`); ASN match? (`show running-config | section router bgp`).
**Most common cause:** ASN mismatch. remote-as on one side must match local-as
on the other.

### EVPN session established but no routes
**Symptoms:** `show bgp evpn summary` shows Estab but prefix count is 0.
**Diagnose:** is `address-family evpn` activated for the neighbor? Is
`send-community extended` set?
**Most common cause:** missing `send-community extended` on one side. Both ends
must send extended communities for route-targets to propagate.

### Cross-leaf VXLAN not forwarding
**Symptoms:** EVPN sessions up, VTEPs discovered, but pings across fabric fail.
**Diagnose:** `show running-config | section router bgp` — check the L2VLAN
block for explicit `route-target both 30100:30100`.
**Most common cause:** `route-target both auto` doesn't propagate type-2 routes
correctly in this configuration. Use explicit route-target.

### MAC moves between leaves
**Symptoms:** same MAC bounces between Eth1 (local) and Vx1 (remote).
**Diagnose:** verify anycast gateway MAC identical on all leaves
(`show running-config | include virtual-router`); verify anycast IP identical.
**Most common cause:** inconsistent virtual MAC. All leaves must have the exact
same `ip virtual-router mac-address`.

### High latency or loss across fabric (containerlab)
**Most common cause:** automation-host CPU/disk saturation. The lab is
software-emulated; performance is bounded by host resources, not fabric design.

## Recovery from container crash

If containerlab containers exit (observed after extended uptime):

**1. Verify state**
```bash
sudo containerlab inspect --all
```

**2. Redeploy**
```bash
cd ~/ai-fabric-lab
sudo containerlab deploy -t ai-fabric.clab.yml --reconfigure
sleep 90
```

**3. Clear stale SSH host keys** (containers regenerate keys on --reconfigure;
stale keys cause Ansible/pyATS "connection refused"):
```bash
for ip in 192.168.100.11 192.168.100.12 192.168.100.21 192.168.100.22 192.168.100.23 192.168.100.24; do
    ssh-keygen -f ~/.ssh/known_hosts -R $ip
done
for ip in 192.168.100.11 192.168.100.12 192.168.100.21 192.168.100.22 192.168.100.23 192.168.100.24; do
    ssh-keyscan -H $ip >> ~/.ssh/known_hosts 2>/dev/null
done
```

**4. Reapply configuration via Ansible**
```bash
cd ~/ai-fabric-lab/ansible && source venv/bin/activate
ansible-playbook playbooks/00-base.yml
ansible-playbook playbooks/01-underlay.yml
ansible-playbook playbooks/02-overlay.yml
```

**5. Reconfigure GPU server IPs**
```bash
docker exec clab-ai-fabric-gpu-srv1 ip addr add 10.100.0.11/24 dev eth1
docker exec clab-ai-fabric-gpu-srv2 ip addr add 10.100.0.12/24 dev eth1
docker exec clab-ai-fabric-gpu-srv3 ip addr add 10.100.0.13/24 dev eth1
docker exec clab-ai-fabric-gpu-srv4 ip addr add 10.100.0.14/24 dev eth1
```

**6. Validate**
```bash
cd ~/ai-fabric-lab/validation
pyats run job jobs/full_fabric_validation.py --testbed-file testbed.yml
```

Total recovery time: ~10 minutes.

## Critical state to monitor (production-grade alerts)

If deployed to production, the following should trigger alerts:

- BGP session not established to either spine for > 60s
- EVPN session not established to either spine for > 60s
- Fabric interface down for > 30s
- VTEP not visible from another leaf for > 60s (type-3 propagation issue)
- Interface error rate increasing
- PFC pause frame rate > 0 sustained (sustained congestion)
- ECN marking rate increasing (approaching capacity)

In this lab, only the first four are observable. The last three require
hardware silicon to validate.
