import unittest

from gateway.firewall import CommandResult, FirewallError, NftablesFirewall
from gateway.service import GatewayConfig


class SingleCableHostRunner:
    """A host with only enp1s0 cabled.

    The default route is on enp1s0 and enp2s0 has no gateway address.
    """

    def __init__(self):
        self.commands = []

    def run(self, command, *, input_text=None, check=True):
        self.commands.append(list(command))
        if command[:3] == ["ip", "link", "show"]:
            return CommandResult(0, "", "")
        if command == ["cat", "/proc/sys/net/ipv4/ip_forward"]:
            return CommandResult(0, "1\n", "")
        if command[:5] == ["ip", "-4", "-o", "addr", "show"]:
            return CommandResult(0, "", "")
        if command == ["ip", "-4", "route", "show", "default"]:
            return CommandResult(
                0, "default via 192.168.4.1 dev enp1s0 proto dhcp\n", ""
            )
        return CommandResult(1, "", "")


READ_ONLY = (
    ("ip", "link", "show"),
    ("ip", "-4", "-o", "addr", "show"),
    ("ip", "-4", "route", "show"),
    ("cat",),
)


class DefaultTopologyTest(unittest.TestCase):
    def test_fixed_topology_uses_enp2s0_for_lan_and_enp1s0_for_wan(self):
        self.assertEqual(
            GatewayConfig("enp2s0", "enp1s0", "192.168.50.0/24", 15, 45),
            GatewayConfig.fixed_topology(),
        )

    def test_single_cable_host_refuses_to_start_without_touching_the_firewall(self):
        runner = SingleCableHostRunner()
        firewall = NftablesFirewall(clock=lambda: 1_000.0, runner=runner)

        with self.assertRaisesRegex(FirewallError, "enp2s0 does not own"):
            firewall.enable(GatewayConfig.fixed_topology(), expires_at=1_045.0)

        not_read_only = [
            command
            for command in runner.commands
            if not any(tuple(command[: len(prefix)]) == prefix for prefix in READ_ONLY)
        ]
        self.assertEqual([], not_read_only)
        self.assertIsNone(firewall.config)


if __name__ == "__main__":
    unittest.main()
