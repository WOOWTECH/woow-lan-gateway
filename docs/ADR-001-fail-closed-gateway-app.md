# ADR-001: Use a lease-gated HA App for enrollment-LAN egress

- Status: Accepted
- Date: 2026-09-02

## Context

The HAOS gateway has two physical interfaces and already supplies DHCP/DNS to `192.168.50.0/24`. HAOS has no official general-purpose LAN-to-WAN router App. One-shot iptables rules are not durable, have no reliable lifecycle, and can remain after the process that created them dies.

An external OpenWrt/OPNsense router remains the stronger long-term infrastructure design, but the selected deployment must use the existing HAOS hardware and expose an App start/stop control.

## Decision

Build `local_woow_lan_gateway` as a minimal-privilege local App with `host_network` and only `NET_ADMIN`.

Use a hybrid firewall:

1. Native nftables chains enforce private-destination blocks, inbound blocks, lease state, status-port isolation, and masquerade.
2. A dedicated iptables chain supplies positive forwarding accepts before Docker's default `FORWARD DROP`.
3. Two timeout-backed nft sets are renewed every 15 seconds with 45-second expiry. The nft guard drops traffic after expiry even if the compatibility chain remains after SIGKILL.
4. Normal shutdown removes both owned objects immediately.
5. Every heartbeat validates normalized nft structure and the exact iptables chain, then repairs divergence.

Treat the App's operator-selected state as authoritative. Fleet alignment may use a healthy, already-started App but may not start it or add temporary NAT while it is installed.

## Consequences

### Positive

- App start/stop directly controls target Internet.
- Crash behavior is bounded and fail-closed.
- Rules are isolated, inspectable, idempotent, and repairable.
- HAOS, Dnsmasq, and target LAN addressing require no redesign.
- Supervisor boot/watchdog and HA persistent notifications provide operational integration.

### Negative

- HAOS remains a router even though routing is not a primary HAOS role.
- `host_network` and `NET_ADMIN` lower the App security rating.
- Gateway reboot interrupts HA, DHCP/DNS, and target egress together.
- IPv6 egress is intentionally unsupported.
- An external router would provide stronger isolation, observability, and upgrade independence.

## Rejected alternatives

- Advanced SSH startup commands: no trustworthy crash cleanup or health contract.
- Dnsmasq configuration: Dnsmasq supplies DHCP/DNS but not general NAT/firewall lifecycle.
- NetworkManager shared mode: conflicts with the existing Dnsmasq DHCP service.
- Tailscale/WireGuard: VPN routing is not local physical-LAN WAN NAT.
- A single expiring nft set: lease renewal creates a small full-policy gap; two sets avoid it.
- iptables-only rules: no native rule TTL for fail-closed crash behavior.
