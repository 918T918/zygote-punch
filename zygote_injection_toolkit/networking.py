from .utils import console
from .stage2 import Stage2Exploit

class NetworkTools:

    def __init__(self, stage2: Stage2Exploit):
        self.s2 = stage2

    def enable_wireless_adb(self, port: int=5555):
        console.print(f'[info]Enabling ADB over TCP/IP on port {port}...')
        self.s2.session.run_command(f'setprop service.adb.tcp.port {port}')
        self.s2.session.run_command('stop adbd')
        self.s2.session.run_command('start adbd')
        console.print('[success]ADB over Network enabled (until reboot).[/]')

    def set_global_proxy(self, host: str, port: int):
        console.print(f'[info]Setting global proxy to {host}:{port}...')
        self.s2.session.run_command(f'settings put global http_proxy {host}:{port}')
        console.print('[success]Global proxy configured.[/]')

    def clear_global_proxy(self):
        console.print('[info]Clearing global proxy...')
        self.s2.session.run_command('settings delete global http_proxy')
        self.s2.session.run_command('settings delete global global_http_proxy_host')
        self.s2.session.run_command('settings delete global global_http_proxy_port')
        console.print('[success]Global proxy cleared.[/]')