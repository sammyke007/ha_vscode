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


class TunnelBusyError(Exception):
    """A configuration flow owns the CLI."""


LOGGER = logging.getLogger(PACKAGE_NAME)
architecture_map = {
    "x86_64": "alpine-x64",
    "armv7l": "linux-armhf",
    "aarch64": "alpine-arm64",
}


class VSCodeDeviceAPI:
    """Own exactly one CLI process and its output reader."""

    def __init__(self, storage_dir, runtime_dir=None, tunnel_name="homeassistant"):
        self.storage_dir = storage_dir
        self.exePath = os.path.join(storage_dir, "code")
        self.runtime_dir = Path(runtime_dir or Path(storage_dir) / "runtime")
        self.cli_data_dir = self.runtime_dir / "cli"
        self.server_data_dir = self.runtime_dir / "server"
        self.extensions_dir = self.runtime_dir / "extensions"
        self.tunnel_name = tunnel_name
        self.proc = None
        self.thread = None
        self.oauthToken = None
        self.devURL = None
        self.lock = RLock()
        self.probe_owner = None
        self.last_error = None
        self.last_exit_code = None
        self.stopping = False
        self.retry_after_probe = False
        self.status_callback = None

    def set_status_callback(self, callback):
        """Register a non-blocking callback for process status changes."""
        with self.lock:
            self.status_callback = callback

    def _notify_status(self):
        callback = self.status_callback
        if callback is not None:
            callback()

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

    def prepare_runtime(self):
        """Create persistent VS Code storage with private permissions."""
        for directory in (
            self.runtime_dir,
            self.cli_data_dir,
            self.server_data_dir,
            self.extensions_dir,
        ):
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            directory.chmod(0o700)

    def tunnel_command(self):
        """Build a stable tunnel command with explicit persistent storage."""
        return [
            self.exePath,
            "--cli-data-dir",
            str(self.cli_data_dir),
            "tunnel",
            "--server-data-dir",
            str(self.server_data_dir),
            "--extensions-dir",
            str(self.extensions_dir),
            "--name",
            self.tunnel_name,
            "--accept-server-license-terms",
        ]

    def reader(self, proc):
        """Iteration ends at EOF instead of spinning on empty readline results."""
        try:
            for line in proc.stdout:
                # Never log raw CLI output: it can contain credentials or codes.
                line = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", line)
                if not self.checkForOauthToken(line) and not self.checkForDevURL(line):
                    for category, pattern in (
                        (
                            "authentication",
                            r"unauthorized|authentication failed|expired.*code|access denied",
                        ),
                        (
                            "network",
                            r"connection refused|timed out|dns|network unreachable",
                        ),
                        ("tls", r"certificate|tls handshake"),
                        ("platform", r"unsupported|glibc|musl|exec format"),
                    ):
                        if re.search(pattern, line, re.IGNORECASE):
                            self.last_error = category
                            LOGGER.debug("Tunnel diagnostic category: %s", category)
                            break
        except (OSError, ValueError):
            LOGGER.debug("Tunnel output closed")
        finally:
            code = proc.poll()
            self.last_exit_code = code
            if code is not None and not self.stopping:
                LOGGER.warning(
                    "Tunnel process exited (code=%s, category=%s)",
                    code,
                    self.last_error or "unknown",
                )
            self._notify_status()

    def claim_probe(self, owner):
        """Reserve this device before any executor work can start."""
        with self.lock:
            if self.probe_owner is not None or self.isRunning():
                raise TunnelBusyError()
            self.probe_owner = owner

    def release_probe(self, owner):
        with self.lock:
            if self.probe_owner is owner:
                self.stopTunnel()
                self.probe_owner = None

    def startTunnel(self, owner=None):
        with self.lock:
            if self.probe_owner is not owner:
                raise TunnelBusyError()
            if self.isRunning():
                return
            self.stopTunnel()
            self.install()
            self.prepare_runtime()
            self.oauthToken = None
            self.devURL = None
            self.last_error = None
            self.last_exit_code = None
            self.stopping = False
            self.proc = subprocess.Popen(
                self.tunnel_command(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                start_new_session=True,
            )
            self.thread = Thread(target=self.reader, args=(self.proc,), daemon=True)
            self.thread.start()

    def consume_retry_after_probe(self):
        """Allow one guarded retry after an authentication probe succeeded."""
        with self.lock:
            retry = self.retry_after_probe
            self.retry_after_probe = False
            return retry

    def stopTunnel(self):
        with self.lock:
            proc = self.proc
            if proc is None:
                return
            self.stopping = True
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
            self.devURL = None
            self.oauthToken = match[1]
            self._notify_status()
            return self.oauthToken
        return None

    def checkForDevURL(self, line):
        match = re.search(r"https://vscode\.dev/tunnel/[A-Za-z0-9_-]+/?", line)
        if match:
            self.oauthToken = None
            self.devURL = match[0]
            if self.probe_owner is not None:
                self.retry_after_probe = True
            self._notify_status()
            return self.devURL
        return None

    @property
    def status(self):
        """URL readiness is a CLI observation, not a network health check."""
        if not self.isRunning():
            return "stopped"
        if self.devURL:
            return "ready"
        if self.oauthToken:
            return "auth_required"
        return "starting"

    async def wait_status(self, timeout, after_auth=False):
        """Observe token and URL together, including late-arriving codes."""
        deadline = time.monotonic() + timeout
        previous_token = self.oauthToken
        while True:
            state = self.status
            if state in ("ready", "stopped"):
                return state
            if state == "auth_required" and (
                not after_auth or self.oauthToken != previous_token
            ):
                return state
            if time.monotonic() >= deadline:
                return state
            await asyncio.sleep(0.1)
