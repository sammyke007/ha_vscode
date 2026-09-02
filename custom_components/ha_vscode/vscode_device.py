"""VS Code CLI management; all blocking methods run outside HA's event loop."""

import asyncio
import logging
import os
import re
import signal
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path
from threading import RLock, Thread
from urllib.request import urlopen

from .const import PACKAGE_NAME
from .exceptions import HAVSCodeDownloadException

LOGGER = logging.getLogger(PACKAGE_NAME)
architecture_map = {
    "x86_64": "alpine-x64",
    "armv7l": "linux-armhf",
    "aarch64": "alpine-arm64",
}


class VSCodeDeviceAPI:
    """Own exactly one CLI process and its output reader."""

    def __init__(self, storage_dir):
        self.storage_dir = storage_dir
        self.exePath = os.path.join(storage_dir, "code")
        self.proc = None
        self.thread = None
        self.oauthToken = None
        self.devURL = None
        self.lock = RLock()

    def install(self):
        """Download with TLS verification and extract only the CLI executable."""
        target = Path(self.exePath)
        if target.is_file():
            return
        architecture = architecture_map.get(os.uname().machine)
        if architecture is None:
            raise HAVSCodeDownloadException()
        target.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://code.visualstudio.com/sha/download?build=stable&os=cli-{architecture}"
        try:
            with tempfile.TemporaryDirectory(dir=target.parent) as directory:
                archive = Path(directory) / "cli.tar.gz"
                with urlopen(url, timeout=60) as response, archive.open("wb") as output:
                    total = 0
                    while chunk := response.read(1024 * 1024):
                        total += len(chunk)
                        if total > 100 * 1024 * 1024:
                            raise ValueError("CLI archive exceeds size limit")
                        output.write(chunk)
                with tarfile.open(archive, "r:gz") as tar:
                    members = [
                        m
                        for m in tar.getmembers()
                        if m.name in ("code", "./code") and m.isfile()
                    ]
                    if len(members) != 1 or members[0].size > 150 * 1024 * 1024:
                        raise ValueError("Invalid CLI archive")
                    staged = Path(directory) / "code"
                    with (
                        tar.extractfile(members[0]) as source,
                        staged.open("wb") as output,
                    ):
                        while chunk := source.read(1024 * 1024):
                            output.write(chunk)
                    staged.chmod(0o755)
                    staged.replace(target)
        except (OSError, ValueError, tarfile.TarError) as err:
            raise HAVSCodeDownloadException() from err

    def reader(self, proc):
        """Iteration ends at EOF instead of spinning on empty readline results."""
        try:
            for line in proc.stdout:
                if not self.checkForOauthToken(line):
                    self.checkForDevURL(line)
        except (OSError, ValueError):
            LOGGER.debug("Tunnel output closed")

    def startTunnel(self):
        with self.lock:
            if self.isRunning():
                return
            self.stopTunnel()
            self.oauthToken = None
            self.devURL = None
            self.proc = subprocess.Popen(
                [
                    self.exePath,
                    "tunnel",
                    "--random-name",
                    "--accept-server-license-terms",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                start_new_session=True,
            )
            self.thread = Thread(target=self.reader, args=(self.proc,), daemon=True)
            self.thread.start()

    def stopTunnel(self):
        with self.lock:
            proc = self.proc
            if proc is None:
                return
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            # Also terminate descendants that kept stdout open after CLI exit.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=5)
            if self.thread is not None:
                self.thread.join(timeout=2)
            if self.thread is None or not self.thread.is_alive():
                proc.stdout.close()
            self.thread = None
            self.proc = None

    def isRunning(self):
        return self.proc is not None and self.proc.poll() is None

    def checkForOauthToken(self, line):
        match = re.search(
            r"https://github\.com/login/device.*?\b([A-Z0-9]{4}-[A-Z0-9]{4})\b", line
        )
        if match:
            self.oauthToken = match[1]
            return self.oauthToken
        return None

    def checkForDevURL(self, line):
        match = re.search(r"https://vscode\.dev/tunnel/[A-Za-z0-9_-]+/?", line)
        if match:
            self.devURL = match[0]
            return self.devURL
        return None

    async def _wait_for(self, attribute, timeout):
        deadline = time.monotonic() + timeout
        while True:
            value = getattr(self, attribute)
            if value is not None:
                return value
            if time.monotonic() >= deadline:
                return None
            await asyncio.sleep(0.1)

    async def getOAuthToken(self, timeout=3.0):
        return await self._wait_for("oauthToken", timeout)

    async def getDevURL(self, timeout=5.0):
        return await self._wait_for("devURL", timeout)

    async def activate(self, timeout=5.0):
        return await self.getDevURL(timeout)

    async def register(self, timeout=5.0):
        await asyncio.to_thread(self.install)
        await asyncio.to_thread(self.startTunnel)
        return await self.getOAuthToken(timeout)
