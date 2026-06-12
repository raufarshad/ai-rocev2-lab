# IP and Numbering Schema

Compact reference for all addressing, ASNs, VLANs, and VNIs used in the fabric. Use this as the source of truth when extending the design.

## ASN allocation

| Role   | ASN   | Notes                          |
|--------|-------|--------------------------------|
| Spine  | 65000 | Both spines share the same ASN |
| leaf1  | 65021 | Unique per leaf                |
| leaf2  | 65022 |                                |
| leaf3  | 65023 |                                |
| leaf4  | 65024 |                                |

Range reserved for future leaves: 65025–65099.

Both spines sharing a single ASN is intentional. Spines are transit-only and present as a single layer to leaves. Multipath across spines works because `bgp bestpath as-path multipath-relax` allows ECMP across paths with
equivalent attributes.

## Loopback assignment

### Loopback0 — router ID

Used as BGP router-id and origin of underlay routing announcements.

| Device | Loopback0 IP |
|--------|--------------|
| spine1 | 10.0.0.11/32 |
| spine2 | 10.0.0.12/32 |
| leaf1  | 10.0.0.21/32 |
| leaf2  | 10.0.0.22/32 |
| leaf3  | 10.0.0.23/32 |
| leaf4  | 10.0.0.24/32 |

### Loopback1 — VTEP source (leaves only)

Used as the VXLAN tunnel source IP. Separating VTEP from router-id allows distributed-VTEP designs without disrupting BGP.

| Device | Loopback1 IP  |
|--------|---------------|
| leaf1  | 10.0.0.121/32 |
| leaf2  | 10.0.0.122/32 |
| leaf3  | 10.0.0.123/32 |
| leaf4  | 10.0.0.124/32 |

Range reserved for future VTEP loopbacks: 10.0.0.125–149.

## Fabric link addressing

Point-to-point /31 subnets between spine and leaf. Two parallel planes because each leaf has uplinks to both spines.

### Spine1 to leaves (10.1.1.0/24 plane)

| Link                       | Spine1 side  | Leaf side    |
|----------------------------|--------------|--------------|
| spine1 Eth1 ↔ leaf1 Eth49  | 10.1.1.0/31  | 10.1.1.1/31  |
| spine1 Eth2 ↔ leaf2 Eth49  | 10.1.1.2/31  | 10.1.1.3/31  |
| spine1 Eth3 ↔ leaf3 Eth49  | 10.1.1.4/31  | 10.1.1.5/31  |
| spine1 Eth4 ↔ leaf4 Eth49  | 10.1.1.6/31  | 10.1.1.7/31  |

### Spine2 to leaves (10.1.2.0/24 plane)

| Link                       | Spine2 side  | Leaf side    |
|----------------------------|--------------|--------------|
| spine2 Eth1 ↔ leaf1 Eth50  | 10.1.2.0/31  | 10.1.2.1/31  |
| spine2 Eth2 ↔ leaf2 Eth50  | 10.1.2.2/31  | 10.1.2.3/31  |
| spine2 Eth3 ↔ leaf3 Eth50  | 10.1.2.4/31  | 10.1.2.5/31  |
| spine2 Eth4 ↔ leaf4 Eth50  | 10.1.2.6/31  | 10.1.2.7/31  |

Convention: even-numbered IP on the spine side, odd-numbered on the leaf side.

## Overlay constants

| Parameter            | Value                |
|----------------------|----------------------|
| Compute VLAN         | 100                  |
| Compute VLAN name    | AI-COMPUTE           |
| L2VNI                | 30100                |
| Tenant VRF           | ai-training          |
| L3VNI                | 50000                |
| Anycast gateway IP   | 10.100.0.1/24        |
| Anycast gateway MAC  | 00:1c:73:00:00:01    |
| Compute subnet       | 10.100.0.0/24        |
| MTU (fabric)         | 9214                 |
| MTU (servers)        | 9000                 |

## GPU server addressing

| Server   | Attached leaf | Mgmt (eth0)    | Compute (eth1) |
|----------|---------------|----------------|----------------|
| gpu-srv1 | leaf1         | 192.168.100.31 | 10.100.0.11/24 |
| gpu-srv2 | leaf2         | 192.168.100.32 | 10.100.0.12/24 |
| gpu-srv3 | leaf3         | 192.168.100.33 | 10.100.0.13/24 |
| gpu-srv4 | leaf4         | 192.168.100.34 | 10.100.0.14/24 |

All servers default-route to 10.100.0.1 (anycast gateway).

## Management network

Used for SSH, gNMI streaming, Ansible automation, and out-of-band access.

| Function           | Network            |
|--------------------|--------------------|
| Management subnet  | 192.168.100.0/24   |
| Management gateway | 192.168.100.1      |
| automation-host    | 10.0.0.232 (DHCP)  |

### Switch management IPs

| Device | Management IP   |
|--------|-----------------|
| spine1 | 192.168.100.11  |
| spine2 | 192.168.100.12  |
| leaf1  | 192.168.100.21  |
| leaf2  | 192.168.100.22  |
| leaf3  | 192.168.100.23  |
| leaf4  | 192.168.100.24  |

## Route-target convention

Route-targets follow the pattern `<VNI>:<VNI>`:

| Resource                  | Route-target  |
|---------------------------|---------------|
| L2VNI 30100 (compute VLAN)| 30100:30100   |
| L3VNI 50000 (tenant VRF)  | 50000:50000   |

Note: `route-target both auto` did not propagate type-2 routes correctly across
leaves in this configuration. Explicit `route-target both 30100:30100` under
the L2VLAN BGP section is required.

## Reserved ranges for scale-out

| Resource         | Current        | Reserved range          |
|------------------|----------------|-------------------------|
| Leaf ASN         | 65021–65024    | 65025–65099             |
| Loopback0        | 10.0.0.21–24   | 10.0.0.25–99            |
| Loopback1 (VTEP) | 10.0.0.121–124 | 10.0.0.125–199          |
| Compute subnets  | 10.100.0.0/24  | 10.100.x.0/24 per tenant|
| L2VNI range      | 30100          | 30100–39999             |
| L3VNI range      | 50000          | 50000–59999             |
| Tenant VRFs      | ai-training    | Add as needed           |
