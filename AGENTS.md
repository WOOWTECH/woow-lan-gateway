# AGENTS.md

Rules for every agent and person who changes this repository. The full
release mechanism is described in the Woow_HA_App_Store README (section
"版本策略與同步") and in ADR-0005 of the WOOW addon pipeline.

1. **``main`` only changes through a pull request.** A ruleset blocks direct
   pushes, force pushes and deleting the branch, and nobody can bypass it.
   Push a branch, open a PR, wait for the required checks, then merge.
2. **A PR that changes an addon version is a release.** Merging it publishes
   that version to the WOOW App Store. It must pass every required check; the
   checks are the approval, there is no human review step. Every PR runs
   `Upgrade comparison / compare` (pipeline #89); treat a failure as blocking.
   It compares each addon whose version the PR changes with the latest Stable
   Release. A PR that changes no version passes it in seconds. The result is
   in the job summary. It also runs the upgrade test (pipeline #144): the
   Store rebuilds the latest Release and the PR for amd64, starts the Release
   under a mock Supervisor, then the PR's version on the same data, and fails
   when either does not start. For this addon the Store registry skips it
   permanently (`skip_upgrade_test`, owner decision in pipeline #158), so the
   summary shows it as not run with that reason. The upgrade test runs
   `host_network` addons on the runner's host network, but to start, the
   gateway also needs `NET_ADMIN`, the fixed interfaces `enp2s0` (LAN) and
   `enp1s0` (WAN), nftables and IPv4 forwarding that the host has already
   enabled (it only reads `net.ipv4.ip_forward`); a GitHub runner cannot give
   it these, and fake interfaces would only prove that it starts, not its NAT
   or fail-closed behaviour. On-device testing on
   the Enrollment LAN covers it instead (pipeline
   `.out-of-scope/lan-gateway-upgrade-test-on-runner.md`). Do not work around
   it with `upgrade-check/options.yaml` (for example `eth0`/`eth1`): that
   would not test the shipped defaults.
3. **Breaking changes must be declared in `upgrade-notes.yaml`** next to the
   addon's `config.yaml` (here `app/upgrade-notes.yaml`). Create the file only
   when the upgrade comparison asks for it; copy `change` and `key` from its
   report and write the migration path. The addons here are built on the
   device: the vulnerability comparison runs on the images the Store rebuilds
   for the upgrade comparison (pipeline #146), although their upgrade test is
   skipped permanently. The release puts these entries on the GitHub Release.
   Rules, change names and the file format: the Woow_HA_App_Store README,
   section "升版比對與 `upgrade-notes.yaml`".
