import subprocess
import re
import sys
from typing import List, Dict, Optional

class AdbHelper:

    @staticmethod
    def run_adb_command(command: List[str], serial: Optional[str]=None, transport_id: Optional[str]=None, usb: bool=False, tcpip: bool=False) -> str:
        try:
            cmd_prefix = ['adb']
            if transport_id:
                cmd_prefix.extend(['-t', transport_id])
            elif serial:
                cmd_prefix.extend(['-s', serial])
            elif usb:
                cmd_prefix.append('-d')
            elif tcpip:
                cmd_prefix.append('-e')
            full_cmd = cmd_prefix + command
            result = subprocess.run(full_cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            return ''
        except FileNotFoundError:
            return ''

    @staticmethod
    def get_connected_devices() -> List[Dict[str, str]]:
        output = AdbHelper.run_adb_command(['devices', '-l'])
        devices = []
        lines = output.strip().splitlines()
        if len(lines) > 1:
            for line in lines[1:]:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    serial = parts[0]
                    state = parts[1]
                    model = 'Unknown'
                    transport_id = 'Unknown'
                    conn_type = 'USB' if not (':' in serial and re.match('\\d+\\.\\d+\\.\\d+\\.\\d+', serial)) else 'TCP/IP'
                    for part in parts[2:]:
                        if part.startswith('model:'):
                            model = part.split(':')[1]
                        elif part.startswith('transport_id:'):
                            transport_id = part.split(':')[1]
                    devices.append({'serial': serial, 'state': state, 'model': model, 'transport_id': transport_id, 'type': conn_type})
        return devices

    @staticmethod
    def get_installed_apps(serial: Optional[str]=None) -> List[Dict[str, str]]:
        output = AdbHelper.run_adb_command(['shell', 'pm', 'list', 'packages', '-f', '-U'], serial=serial)
        apps = []
        regex = re.compile('package:(?P<path>.*?)=(?P<pkg>[\\w\\.]+)\\s+uid:(?P<uid>\\d+)')
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            match = regex.search(line)
            if match:
                apps.append({'package': match.group('pkg'), 'path': match.group('path'), 'uid': int(match.group('uid'))})
            else:
                pass
        return apps

    @staticmethod
    def get_target_apps(serial: Optional[str]=None) -> List[Dict[str, str]]:
        all_apps = AdbHelper.get_installed_apps(serial=serial)
        targets = []
        for app in all_apps:
            is_priv = '/priv-app/' in app['path']
            uid = app['uid']
            is_target_uid = uid in [1000, 1001]
            if is_priv or is_target_uid:
                app['type'] = []
                if is_priv:
                    app['type'].append('priv-app')
                if uid == 1000:
                    app['type'].append('system(1000)')
                if uid == 1001:
                    app['type'].append('radio(1001)')
                targets.append(app)
        targets.sort(key=lambda x: (x['uid'], x['package']))
        return targets

    @staticmethod
    def get_package_uid(package_name: str, serial: Optional[str]=None) -> Optional[int]:
        apps = AdbHelper.get_installed_apps(serial=serial)
        for app in apps:
            if app['package'] == package_name:
                return app['uid']
        return None

    @staticmethod
    def get_detailed_package_info(package_name: str, serial: Optional[str]=None) -> Dict[str, Optional[str]]:
        output = AdbHelper.run_adb_command(['shell', 'dumpsys', 'package', package_name], serial=serial)
        info = {'uid': None, 'seInfo': None}
        uid_match = re.search('userId=(\\d+)', output)
        if uid_match:
            info['uid'] = uid_match.group(1)
        seinfo_match = re.search('seInfo=([\\w:]+)', output)
        if seinfo_match:
            info['seInfo'] = seinfo_match.group(1)
        if not info['uid']:
            uid = AdbHelper.get_package_uid(package_name, serial=serial)
            if uid:
                info['uid'] = str(uid)
        return info

    @staticmethod
    def restart_adb_server():
        AdbHelper.run_adb_command(['kill-server'])
        AdbHelper.run_adb_command(['start-server'])

    @staticmethod
    def forward(local: str, remote: str, serial: Optional[str]=None, transport_id: Optional[str]=None, usb: bool=False, tcpip: bool=False):
        return AdbHelper.run_adb_command(['forward', local, remote], serial=serial, transport_id=transport_id, usb=usb, tcpip=tcpip)

    @staticmethod
    def remove_forward(local: str, serial: Optional[str]=None, transport_id: Optional[str]=None, usb: bool=False, tcpip: bool=False):
        return AdbHelper.run_adb_command(['forward', '--remove', local], serial=serial, transport_id=transport_id, usb=usb, tcpip=tcpip)