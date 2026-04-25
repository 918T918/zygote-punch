import socket

import time

from typing import Optional

class RemoteShellSession:

    def __init__(self, host: str = "127.0.0.1", port: int = 1234, timeout: int = 10):

        self.host = host

        self.port = port

        self.timeout = timeout

        self.socket: Optional[socket.socket] = None

    def connect(self):

        try:

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            self.socket.settimeout(self.timeout)

            self.socket.connect((self.host, self.port))

            self.socket.sendall(b"\n")

            time.sleep(0.1)

            self.read_all()

        except ConnectionRefusedError:

            raise ConnectionError(f"Could not connect to {self.host}:{self.port}. Is the exploit running?")

    def close(self):

        if self.socket:

            self.socket.close()

            self.socket = None

    def send_command(self, command: str):

        if not self.socket:

            raise ConnectionError("Not connected")

        if not command.endswith("\n"):

            command += "\n"

        self.socket.sendall(command.encode("utf-8"))

    def read_until(self, delimiter: str = "\n", timeout: float = 5.0) -> str:

        if not self.socket:

            raise ConnectionError("Not connected")

        buffer = b""

        start_time = time.time()

        while time.time() - start_time < timeout:

            try:

                chunk = self.socket.recv(1)

                if not chunk:

                    break

                buffer += chunk

                if delimiter.encode() in buffer:

                    return buffer.decode("utf-8")

            except socket.timeout:

                break

        return buffer.decode("utf-8")

    def read_all(self, timeout: float = 1.0) -> str:

        data = self.read_raw(timeout)

        return data.decode("utf-8", errors="replace")

    def read_raw(self, timeout: float = 1.0) -> bytes:

        if not self.socket:

            raise ConnectionError("Not connected")

        self.socket.settimeout(timeout)

        buffer = b""

        try:

            while True:

                chunk = self.socket.recv(4096)

                if not chunk:

                    break

                buffer += chunk

        except socket.timeout:

            pass

        finally:

            self.socket.settimeout(self.timeout)

        return buffer

    def run_command(self, command: str, wait_for_output: bool = True, timeout: float = 2.0) -> str:

        self.send_command(command)

        if wait_for_output:

            return self.read_all(timeout=timeout)

        return ""

    def __enter__(self):

        self.connect()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        self.close()
