# Woow LAN Gateway

A Home Assistant App that gives the fixed factory-enrollment LAN fail-closed, Internet-only IPv4 egress.

## Install from GitHub

Add the following repository in Home Assistant under **Settings → Apps → App store → Repositories**:

```text
https://github.com/WOOWTECH/woow-lan-gateway
```

The App is also distributed through the consolidated [WoowTech HA App Store](https://github.com/WOOWTECH/Woow_HA_App_Store).

## Fixed topology

```text
LAN:        192.168.50.0/24
Gateway:    192.168.50.1
LAN NIC:    enp4s0
WAN NIC:    enp2s0
HA App:     local_woow_lan_gateway
Status:     HA Ingress or http://172.30.32.1:45987/health
```

N2840, J1900, and J6412 targets use the same egress policy. Dnsmasq remains responsible for DHCP and DNS; this App owns only forwarding, firewall policy, and NAT.

## Behavior

- Started and healthy: `.50` clients can initiate IPv4 connections to public destinations.
- Stopped normally: the App removes its nftables table and iptables chain immediately.
- Killed uncleanly: two nftables lease elements expire within 45 seconds and the remaining forwarding adapter is fail-closed.
- Restarted: stale state is removed and rebuilt idempotently.
- Rule loss or modification: the health endpoint returns `503 degraded`; the next 15-second heartbeat repairs the complete structure.
- Private destinations `10/8`, `172.16/12`, and `192.168/16` are blocked for LAN-to-WAN forwarding.
- New WAN-to-LAN connections are dropped. Established/related replies are allowed.
- Established replies to HA's internal management networks remain allowed, while new target-initiated management connections remain blocked.
- LAN-to-LAN switching, DHCP/DNS, and access to `192.168.50.1` are outside the forwarding policy.

The status service listens on TCP 45987 for Supervisor ingress/watchdog, while the nftables input guard drops access to that port from `enp2s0` and `enp4s0`.

## Fail-closed design

The deep module exposes one lifecycle interface: `start`, `heartbeat`, `status`, and `stop`. Kernel details sit behind a firewall adapter. Tests use `MemoryFirewall`; production uses `NftablesFirewall`.

The native nftables guard runs before the Docker-compatible iptables filter chain. A drop from the guard is final. A dedicated `WOOW_LAN_FORWARD` chain supplies the accepts required ahead of Docker's default `FORWARD DROP`, but those accepts cannot bypass an expired nft lease. NAT matches the same lease sets.

Two sets (`active_a` and `active_b`) are renewed in sequence, avoiding a complete policy gap during renewal. Structural health normalizes counters, handles, and expiring elements before checking the nft rules checksum; the iptables chain is checked against its exact expected rule set.

## App operation

Install slug:

```text
local_woow_lan_gateway
```

Recommended Supervisor settings:

```text
boot: auto
watchdog: true
```

Starting the App enables egress. Stopping it disables egress while DHCP, DNS, local HA access, and target-to-target LAN traffic remain available.

The App updates persistent notification `woow_lan_gateway_status` on start, failure, and normal stop. The Ingress/status response includes state, lease expiry, interfaces, CIDR, desired rules checksum, and packet counters.

## Tests

Run local contract tests:

```bash
PYTHONPATH=haos-lan-gateway/src \
  python3 -m unittest discover -s haos-lan-gateway/tests -v
```

Production validation covers:

- offline before App start;
- public DNS, TLS, GitHub API, and public-IP lookup after start;
- all RFC1918 forwarding blocked;
- local gateway access retained;
- two independent `.50` clients online;
- normal stop cleanup and immediate loss of egress;
- clean restart recovery;
- SIGKILL with lease-expiry fail-close;
- external lease loss and heartbeat repair;
- individual rule deletion, immediate `503 degraded`, and checksum repair;
- status TCP port blocked from the LAN;
- persistent notification delivery through the Home Assistant WebSocket query API.

## Rollback

1. Stop `local_woow_lan_gateway` in Settings → Apps.
2. Verify `table inet woow_lan_gateway` and `WOOW_LAN_FORWARD` are absent.
3. Uninstall the App if it is no longer wanted.
4. Remove `/data/apps/local/woow_lan_gateway` only after uninstalling it.

Stopping or uninstalling does not alter Dnsmasq, NetworkManager, HA configuration, target files, or existing LAN addresses.

## Research sources

- Home Assistant App configuration (`host_network`, `NET_ADMIN`, boot, startup, watchdog): https://developers.home-assistant.io/docs/apps/configuration
- Home Assistant App security ratings: https://developers.home-assistant.io/docs/apps/presentation
- Official OpenThread App as a maintained `host_network` + `NET_ADMIN` reference: https://github.com/home-assistant/addons/tree/master/openthread_border_router
- nftables element timeouts: https://wiki.nftables.org/wiki-nftables/index.php/Element_timeouts
- nftables NAT/masquerade: https://wiki.nftables.org/wiki-nftables/index.php/Performing_Network_Address_Translation_(NAT)
- nftables chain priority and final drop semantics: https://wiki.nftables.org/wiki-nftables/index.php/Configuring_chains
