from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from .utils import console
from .adb_helper import AdbHelper
from rich.prompt import Prompt, IntPrompt

class PackageWizard:

    def __init__(self, serial=None):
        self.serial = serial

    def run_wizard(self):
        console.print('[info]Fetching package list...')
        apps = AdbHelper.get_installed_apps(serial=self.serial)
        if not apps:
            console.print('[error]No apps found or ADB error.[/]')
            return None
        apps.sort(key=lambda x: x['package'])
        while True:
            search = Prompt.ask("\n[highlight]Search packages[/] (empty for all, 'q' to quit)")
            if search.lower() == 'q':
                return None
            filtered = [a for a in apps if search.lower() in a['package'].lower()]
            if not filtered:
                console.print('[warning]No packages match your search.[/]')
                continue
            table = Table(title=f'Select Package ({len(filtered)} found)')
            table.add_column('Idx', justify='right', style='dim')
            table.add_column('Package', style='success')
            table.add_column('UID', style='highlight')
            display_count = min(50, len(filtered))
            for i in range(display_count):
                table.add_row(str(i + 1), filtered[i]['package'], str(filtered[i]['uid']))
            console.print(table)
            if len(filtered) > 50:
                console.print(f'[dim]... and {len(filtered) - 50} more. Refine your search.[/]')
            choice = Prompt.ask("Select Index (or 'b' to go back)")
            if choice.lower() == 'b':
                continue
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(filtered):
                    return filtered[idx]['package']
            except:
                console.print('[error]Invalid selection.[/]')