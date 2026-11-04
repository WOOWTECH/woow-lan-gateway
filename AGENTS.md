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
   when either does not start. Startup only: data is not checked yet.
3. **Breaking changes must be declared in `upgrade-notes.yaml`** next to the
   addon's `config.yaml` (here `app/upgrade-notes.yaml`). Create the file only
   when the upgrade comparison asks for it; copy `change` and `key` from its
   report and write the migration path. The addons here are built on the
   device, so the vulnerability comparison does not run for them yet (pipeline
   #90). The release puts these entries on the GitHub Release. Rules, change
   names and the file format: the Woow_HA_App_Store README, section
   "升版比對與 `upgrade-notes.yaml`".
