import unittest

from gateway.service import (
    ConfigurationError,
    Decision,
    Flow,
    GatewayConfig,
    GatewayService,
    MemoryFirewall,
)


class MutableClock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now


class PartiallyFailingFirewall(MemoryFirewall):
    def enable(self, config, expires_at):
        super().enable(config, expires_at)
        raise RuntimeError("kernel rejected forwarding rules")


class GatewayLifecycleContractTest(unittest.TestCase):
    def test_start_opens_public_internet_but_not_private_networks(self):
        clock = MutableClock(1_000.0)
        firewall = MemoryFirewall(clock=clock)
        service = GatewayService(
            GatewayConfig.fixed_topology(), firewall=firewall, clock=clock
        )

        status = service.start()

        self.assertEqual("enabled", status.state)
        self.assertTrue(
            firewall.permits(
                Flow.forward("enp4s0", "enp2s0", "192.168.50.20", "8.8.8.8")
            )
        )
        for destination in ("10.0.0.1", "172.16.0.1", "192.168.4.1"):
            with self.subTest(destination=destination):
                self.assertFalse(
                    firewall.permits(
                        Flow.forward(
                            "enp4s0", "enp2s0", "192.168.50.20", destination
                        )
                    )
                )

    def test_stop_closes_public_internet_immediately(self):
        clock = MutableClock(1_000.0)
        firewall = MemoryFirewall(clock=clock)
        service = GatewayService(
            GatewayConfig.fixed_topology(), firewall=firewall, clock=clock
        )
        flow = Flow.forward("enp4s0", "enp2s0", "192.168.50.20", "8.8.8.8")
        service.start()

        status = service.stop()

        self.assertEqual("disabled", status.state)
        self.assertFalse(firewall.permits(flow))

    def test_crash_closes_public_internet_when_lease_expires(self):
        clock = MutableClock(1_000.0)
        firewall = MemoryFirewall(clock=clock)
        service = GatewayService(
            GatewayConfig.fixed_topology(), firewall=firewall, clock=clock
        )
        flow = Flow.forward("enp4s0", "enp2s0", "192.168.50.20", "8.8.8.8")
        service.start()

        clock.now += 44
        self.assertTrue(firewall.permits(flow))
        clock.now += 2
        self.assertFalse(firewall.permits(flow))

    def test_return_traffic_is_allowed_but_new_wan_connections_are_denied(self):
        clock = MutableClock(1_000.0)
        firewall = MemoryFirewall(clock=clock)
        service = GatewayService(
            GatewayConfig.fixed_topology(), firewall=firewall, clock=clock
        )
        service.start()

        self.assertTrue(
            firewall.permits(
                Flow.forward(
                    "enp2s0",
                    "enp4s0",
                    "8.8.8.8",
                    "192.168.50.20",
                    connection_state="established",
                )
            )
        )
        self.assertFalse(
            firewall.permits(
                Flow.forward(
                    "enp2s0",
                    "enp4s0",
                    "8.8.8.8",
                    "192.168.50.20",
                    connection_state="new",
                )
            )
        )

    def test_established_return_to_the_internal_management_network_is_allowed(self):
        clock = MutableClock(1_000.0)
        firewall = MemoryFirewall(clock=clock)
        GatewayService(
            GatewayConfig.fixed_topology(), firewall=firewall, clock=clock
        ).start()

        self.assertTrue(
            firewall.permits(
                Flow.forward(
                    "enp4s0",
                    "hassio",
                    "192.168.50.20",
                    "172.30.33.2",
                    connection_state="established",
                )
            )
        )
        self.assertFalse(
            firewall.permits(
                Flow.forward(
                    "enp4s0",
                    "hassio",
                    "192.168.50.20",
                    "172.30.33.2",
                    connection_state="new",
                )
            )
        )

    def test_lan_local_traffic_is_outside_the_gateway_policy(self):
        clock = MutableClock(1_000.0)
        firewall = MemoryFirewall(clock=clock)
        GatewayService(
            GatewayConfig.fixed_topology(), firewall=firewall, clock=clock
        ).start()

        decision = firewall.decision(
            Flow.forward("enp4s0", "enp4s0", "192.168.50.20", "192.168.50.21")
        )

        self.assertEqual(Decision.UNMANAGED, decision)

    def test_status_reports_rule_loss_and_heartbeat_repairs_it(self):
        clock = MutableClock(1_000.0)
        firewall = MemoryFirewall(clock=clock)
        service = GatewayService(
            GatewayConfig.fixed_topology(), firewall=firewall, clock=clock
        )
        service.start()
        firewall.simulate_external_rule_loss()

        degraded = service.status()
        repaired = service.heartbeat()

        self.assertEqual("degraded", degraded.state)
        self.assertEqual("enabled", repaired.state)
        self.assertEqual("enp4s0", repaired.lan_interface)
        self.assertEqual("enp2s0", repaired.wan_interface)
        self.assertEqual("192.168.50.0/24", repaired.source_cidr)
        self.assertTrue(repaired.rules_checksum)

    def test_partial_firewall_failure_is_cleaned_up(self):
        clock = MutableClock(1_000.0)
        firewall = PartiallyFailingFirewall(clock=clock)
        service = GatewayService(
            GatewayConfig.fixed_topology(), firewall=firewall, clock=clock
        )

        with self.assertRaisesRegex(RuntimeError, "kernel rejected"):
            service.start()

        self.assertFalse(firewall.healthy())
        self.assertEqual("disabled", service.status().state)

    def test_unsafe_heartbeat_configuration_fails_closed(self):
        clock = MutableClock(1_000.0)
        firewall = MemoryFirewall(clock=clock)
        config = GatewayConfig(
            lan_interface="enp4s0",
            wan_interface="enp2s0",
            source_cidr="192.168.50.0/24",
            heartbeat_interval=30,
            lease_timeout=45,
        )
        service = GatewayService(config, firewall=firewall, clock=clock)

        with self.assertRaisesRegex(ConfigurationError, "lease_timeout"):
            service.start()

        self.assertFalse(
            firewall.permits(
                Flow.forward("enp4s0", "enp2s0", "192.168.50.20", "8.8.8.8")
            )
        )

    def test_heartbeat_renews_the_fail_closed_lease(self):
        clock = MutableClock(1_000.0)
        firewall = MemoryFirewall(clock=clock)
        service = GatewayService(
            GatewayConfig.fixed_topology(), firewall=firewall, clock=clock
        )
        flow = Flow.forward("enp4s0", "enp2s0", "192.168.50.20", "8.8.8.8")
        service.start()
        clock.now += 30

        status = service.heartbeat()

        self.assertEqual(1_075.0, status.expires_at)
        clock.now = 1_074.0
        self.assertTrue(firewall.permits(flow))
        clock.now = 1_076.0
        self.assertFalse(firewall.permits(flow))


if __name__ == "__main__":
    unittest.main()
