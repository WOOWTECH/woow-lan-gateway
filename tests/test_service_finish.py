import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FINISH = ROOT / "app" / "rootfs" / "etc" / "services.d" / "woow-lan-gateway" / "finish"
SH = shutil.which("sh")


@unittest.skipUnless(SH, "needs a POSIX sh")
class ServiceFinishTest(unittest.TestCase):
    """Runs the s6 ``finish`` script the way s6-supervise does.

    ``$1`` is the exit code of ``run`` (256 when a signal stopped it) and
    ``$2`` the signal. Paths under ``/run`` are moved into a temporary root,
    and ``python3`` and ``halt`` only record that they were called.
    """

    def finish(self, exit_code, signal=0):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calls = root / "calls"
            bin_dir = root / "bin"
            halt = root / "run" / "s6" / "basedir" / "bin" / "halt"
            results = root / "run" / "s6-linux-init-container-results"
            for directory in (bin_dir, halt.parent, results):
                directory.mkdir(parents=True)
            for fake, name in ((bin_dir / "python3", "python3"), (halt, "halt")):
                fake.write_text(f'#!/bin/sh\necho "{name} $*" >> "{calls.as_posix()}"\n')
                fake.chmod(0o755)
            script = root / "finish"
            script.write_text(FINISH.read_text().replace("/run/", f"{root.as_posix()}/run/"))

            env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
            subprocess.run(
                [SH, str(script), str(exit_code), str(signal)], env=env, check=True
            )

            exitcode = results / "exitcode"
            return (
                [line.strip() for line in calls.read_text().splitlines()]
                if calls.exists()
                else [],
                exitcode.read_text().strip() if exitcode.exists() else None,
            )

    def test_startup_failure_cleans_up_and_halts_the_container(self):
        calls, exitcode = self.finish(1)

        self.assertEqual(["python3 -m gateway.cli cleanup", "halt"], calls)
        self.assertEqual("1", exitcode)

    def test_normal_stop_cleans_up_without_halting(self):
        calls, exitcode = self.finish(0)

        self.assertEqual(["python3 -m gateway.cli cleanup"], calls)
        self.assertIsNone(exitcode)

    def test_finish_has_time_to_clean_up_before_halting(self):
        # s6-supervise kills finish after timeout-finish ms (5000 when the
        # file is missing); a killed finish never reaches halt.
        timeout = FINISH.with_name("timeout-finish")

        self.assertTrue(timeout.exists())
        self.assertGreater(int(timeout.read_text()), 5000)

    def test_stop_by_signal_cleans_up_without_halting(self):
        calls, exitcode = self.finish(256, signal=15)

        self.assertEqual(["python3 -m gateway.cli cleanup"], calls)
        self.assertIsNone(exitcode)


if __name__ == "__main__":
    unittest.main()
