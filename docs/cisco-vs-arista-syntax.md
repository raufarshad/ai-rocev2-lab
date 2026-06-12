# Cisco NX-OS vs Arista EOS — Syntax Equivalence

This document maps the EVPN VXLAN fabric configuration from this lab (Arista
EOS) to its Cisco NX-OS equivalent. The purpose is to demonstrate that the
design is vendor-portable and to serve as a translation reference for engineers
who know one platform and need to work on the other.

The protocols are identical across vendors — eBGP underlay, BGP EVPN control
plane, VXLAN data plane, symmetric IRB. Only the CLI syntax differs.

> Note: NX-OS examples reflect standard Nexus 9000 EVPN configuration. Validate
> against your specific NX-OS version, as syntax has minor variations across
> releases. The Arista side is what this lab actually runs.

## 1. Enabling features

NX-OS requires explicit feature enablement; EOS does not.

**Arista EOS**
```
! No feature enablement required; capabilities are always present.
service routing protocols model multi-agent
```

**Cisco NX-OS**
```
feature bgp
feature interface-vlan
feature vn-segment-vlan-based
feature nv overlay
nv overlay evpn
```

## 2. Loopback interfaces

**Arista EOS**
```
interface Loopback0
   ip address 10.0.0.21/32
interface Loopback1
   ip address 10.0.0.121/32
```

**Cisco NX-OS**
```
interface loopback0
   ip address 10.0.0.21/32
interface loopback1
   ip address 10.0.0.121/32
```

Nearly identical. Both use prefix-length notation inline.

## 3. Fabric (underlay) interfaces

**Arista EOS**
```
interface Ethernet49
   no switchport
   mtu 9214
   ip address 10.1.1.1/31
   bfd interval 250 min-rx 250 multiplier 3
```

**Cisco NX-OS**
```
interface Ethernet1/49
   no switchport
   mtu 9216
   ip address 10.1.1.1/31
   bfd interval 250 min_rx 250 multiplier 3
   no shutdown
```

Differences: NX-OS interface naming includes slot (`Ethernet1/49`); NX-OS max
MTU is 9216 vs Arista 9214; NX-OS requires explicit `no shutdown`; BFD uses
`min_rx` (underscore) on NX-OS vs `min-rx` (hyphen) on EOS.

## 4. eBGP underlay

**Arista EOS**
```
router bgp 65021
   router-id 10.0.0.21
   no bgp default ipv4-unicast
   maximum-paths 64
   bgp bestpath as-path multipath-relax
   neighbor 10.1.1.0 remote-as 65000
   neighbor 10.1.1.0 bfd
   address-family ipv4
      neighbor 10.1.1.0 activate
      network 10.0.0.21/32
      network 10.0.0.121/32
```

**Cisco NX-OS**
```
router bgp 65021
   router-id 10.0.0.21
   address-family ipv4 unicast
      maximum-paths 64
      network 10.0.0.21/32
      network 10.0.0.121/32
   neighbor 10.1.1.0
      remote-as 65000
      bfd
      address-family ipv4 unicast
```

Differences: EOS disables default IPv4 activation globally
(`no bgp default ipv4-unicast`) then activates per-neighbor; NX-OS structures
address-family under the neighbor. `multipath-relax` on NX-OS is configured as
`maximum-paths` plus `bestpath as-path multipath-relax` under the address-family.

## 5. VXLAN VTEP interface

**Arista EOS**
```
interface Vxlan1
   vxlan source-interface Loopback1
   vxlan udp-port 4789
   vxlan vlan 100 vni 30100
   vxlan vrf ai-training vni 50000
```

**Cisco NX-OS**
```
interface nve1
   no shutdown
   source-interface loopback1
   host-reachability protocol bgp
   member vni 30100
      ingress-replication protocol bgp
   member vni 50000 associate-vrf
```

Conceptually identical (a VTEP sourced from loopback1) but NX-OS names the
interface `nve1`, requires `host-reachability protocol bgp`, and binds VNIs as
`member vni` statements. The L3VNI uses `associate-vrf`.

## 6. VLAN to VNI mapping

**Arista EOS**
```
vlan 100
   name AI-COMPUTE
! Mapping done in the Vxlan1 interface (see above)
```

**Cisco NX-OS**
```
vlan 100
   name AI-COMPUTE
   vn-segment 30100
```

NX-OS maps VLAN to VNI directly under the VLAN with `vn-segment`; EOS does it
in the VXLAN interface.

## 7. Tenant VRF and L3VNI

**Arista EOS**
```
vrf instance ai-training
ip routing vrf ai-training

router bgp 65021
   vrf ai-training
      rd 10.0.0.21:50000
      route-target import evpn 50000:50000
      route-target export evpn 50000:50000
      router-id 10.0.0.21
      redistribute connected
```

**Cisco NX-OS**
```
vrf context ai-training
   vni 50000
   rd auto
   address-family ipv4 unicast
      route-target both auto evpn

router bgp 65021
   vrf ai-training
      address-family ipv4 unicast
         advertise l2vpn evpn
         redistribute direct route-map ALL
```

NX-OS defines the VRF in `vrf context` with the VNI and route-targets there;
EOS configures the VRF route-targets under the BGP process.

## 8. Anycast gateway

**Arista EOS**
```
ip virtual-router mac-address 00:1c:73:00:00:01

interface Vlan100
   vrf ai-training
   ip address virtual 10.100.0.1/24
   mtu 9214
```

**Cisco NX-OS**
```
fabric forwarding anycast-gateway-mac 001c.7300.0001

interface Vlan100
   vrf member ai-training
   ip address 10.100.0.1/24
   fabric forwarding mode anycast-gateway
   mtu 9216
```

Differences: NX-OS uses dotted MAC notation (`001c.7300.0001`) vs EOS colon
notation; NX-OS marks the SVI with `fabric forwarding mode anycast-gateway`
vs EOS `ip address virtual`.

## 9. EVPN address-family

**Arista EOS**
```
router bgp 65021
   neighbor 10.1.1.0 send-community extended
   address-family evpn
      neighbor 10.1.1.0 activate
   vlan 100
      rd auto
      route-target both 30100:30100
      redistribute learned
```

**Cisco NX-OS**
```
router bgp 65021
   neighbor 10.1.1.0
      address-family l2vpn evpn
         send-community extended

evpn
   vni 30100 l2
      rd auto
      route-target import auto
      route-target export auto
```

NX-OS uses a dedicated top-level `evpn` block for L2VNI route-targets; EOS
configures them under `router bgp ... vlan 100`. NX-OS address-family is named
`l2vpn evpn`; EOS just `evpn`.

## 10. Common verification commands

| Purpose                  | Arista EOS                  | Cisco NX-OS                          |
|--------------------------|-----------------------------|--------------------------------------|
| BGP underlay summary     | `show ip bgp summary`       | `show ip bgp summary`                |
| EVPN summary             | `show bgp evpn summary`     | `show bgp l2vpn evpn summary`        |
| VTEP / NVE peers         | `show vxlan vtep`           | `show nve peers`                     |
| VNI status               | `show vxlan vni`            | `show nve vni`                       |
| MAC table                | `show mac address-table`    | `show mac address-table`             |
| EVPN routes              | `show bgp evpn`             | `show bgp l2vpn evpn`                |
| VRF routing table        | `show ip route vrf NAME`    | `show ip route vrf NAME`             |

## Summary

The design in this repository is fully portable between Arista EOS and Cisco
NX-OS. The protocol architecture — eBGP-everywhere underlay, BGP EVPN control
plane, VXLAN data plane with symmetric IRB, anycast gateway — is identical.
What changes is CLI syntax and a handful of platform conventions (feature
enablement on NX-OS, interface naming, MAC notation, where route-targets are
configured).

An engineer who understands the design on one platform can implement it on the
other by translating the syntax. This is the core competency a multi-vendor AI
fabric architect needs: the architecture is the durable knowledge; the CLI is
an implementation detail.
