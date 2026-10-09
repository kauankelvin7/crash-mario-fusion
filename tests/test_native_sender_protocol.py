"""Exercise the production C coin sender over localhost, with no game assets.

Classification: VERIFIED_SYNTHETIC. This is not a running SM64 or Crash test.
"""
import os
import pathlib
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SESSION = "00112233445566778899aabbccddeeff"


class NativeSenderProtocolTests(unittest.TestCase):
    def test_production_c_sender_wire_format(self):
        cc = shutil.which("gcc")
        if cc is None:
            self.skipTest("GCC not installed or not on PATH; compile test requires GCC")
        with tempfile.TemporaryDirectory(prefix="cm64-native-sender-") as scratch:
            executable = pathlib.Path(scratch) / (
                "native_sender.exe" if os.name == "nt" else "native_sender"
            )
            cmd = [
                cc, "-std=c11", "-Wall", "-Wextra", "-Werror",
                "-I" + str(ROOT / "integration" / "sm64"),
                str(ROOT / "integration" / "sm64" / "cm64_coin.c"),
                str(ROOT / "tests" / "integration" / "native_sender.c"),
                "-o", str(executable),
            ]
            if os.name == "nt":
                cmd += ["-lws2_32"]
            build = subprocess.run(
                cmd, capture_output=True, text=True, timeout=45, check=False,
                cwd=ROOT,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)

            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
                receiver.bind(("127.0.0.1", 0))
                receiver.settimeout(5.0)
                port = receiver.getsockname()[1]
                environment = os.environ.copy()
                environment["CM64_SESSION"] = SESSION
                environment["CM64_PORT"] = str(port)
                with subprocess.Popen(
                    [str(executable)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=environment,
                ) as sender:
                    self.assertIsNotNone(sender.stdin)
                    sender.stdin.write(b"c")
                    sender.stdin.flush()
                    packet, addr = receiver.recvfrom(256)
                    sender.stdin.close()
                    result = sender.wait(timeout=5.0)
                    self.assertEqual(result, 0)
                self.assertEqual(addr[0], "127.0.0.1")
                self.assertEqual(len(packet), 52)
                self.assertEqual(packet[:4], b"CMJ1")
                self.assertEqual(packet[4:20], bytes.fromhex(SESSION))
                self.assertEqual(struct.unpack(">I", packet[20:24])[0], 1)
                self.assertEqual(struct.unpack(">I", packet[24:28])[0], 42)
                self.assertEqual(struct.unpack(">i", packet[28:32])[0], 7)
                self.assertEqual(struct.unpack(">fff", packet[32:44]), (1.25, 2.5, -3.75))
                sent_at = struct.unpack(">Q", packet[44:52])[0]
                self.assertLess(abs(int(time.time() * 1000) - sent_at), 30000)


if __name__ == "__main__":
    unittest.main()
