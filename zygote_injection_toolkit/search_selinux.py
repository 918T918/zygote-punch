import re

from typing import Optional, List, Dict

from pathlib import Path

from rich.table import Table

from .utils import console

LEVELFROM_NONE = "none"

LEVELFROM_APP = "app"

LEVELFROM_USER = "user"

LEVELFROM_ALL = "all"

SEAPP_PATHS = [

    "/system/etc/selinux/plat_seapp_contexts",

    "/plat_seapp_contexts",

    "/product/etc/selinux/product_seapp_contexts",

    "/product_seapp_contexts",

    "/vendor/etc/selinux/vendor_seapp_contexts",

    "/vendor_seapp_contexts",

    "/vendor/etc/selinux/nonplat_seapp_contexts",

    "/nonplat_seapp_contexts",

    "/odm/etc/selinux/odm_seapp_contexts",

    "/odm_seapp_contexts",

]

def parse_seapp_line(line: str) -> Optional[Dict]:

    p = line.strip()

    if not p or p.startswith("#"):

        return None

    cur = {

        "isSystemServer": False,

        "user": None,

        "seinfo": None,

        "name": None,

        "domain": None,

        "type": None,

        "levelFrom": None,

        "level": None,

        "path": None,

        "isPrivApp": False,

        "minTargetSdkVersion": 0,

    }

    tokens = re.split(r"[ \t]+", p)

    for token in tokens:

        if "=" not in token: continue

        name, value = token.split("=", 1)

        name = name.lower()

        if name == "issystemserver": cur["isSystemServer"] = value.lower() == "true"

        elif name == "user": cur["user"] = value

        elif name == "seinfo": cur["seinfo"] = value

        elif name == "name": cur["name"] = value

        elif name == "domain": cur["domain"] = value

        elif name == "type": cur["type"] = value

        elif name == "levelfrom": cur["levelFrom"] = value

        elif name == "level": cur["level"] = value

        elif name == "path": cur["path"] = value

        elif name == "isprivapp": cur["isPrivApp"] = value.lower() == "true"

        elif name == "mintargetsdkversion":

            try: cur["minTargetSdkVersion"] = int(value)

            except: pass

    return cur

class SELinuxAnalyzer:

    def __init__(self, adb_helper):

        self.adb = adb_helper

        self.rules = []

    def fetch_rules(self, serial: Optional[str] = None):

        for path in SEAPP_PATHS:

            content = self.adb.run_adb_command(["shell", "cat", path], serial=serial)

            if content:

                for line in content.splitlines():

                    rule = parse_seapp_line(line)

                    if rule:

                        rule["source"] = path

                        self.rules.append(rule)

    def find_best_contexts(self):

        interesting = []

        for r in self.rules:

            if r["domain"] and r["seinfo"]:

                interesting.append(r)

        return interesting

    def display_report(self):

        table = Table(title="SELinux seapp_contexts Analysis")

        table.add_column("seinfo", style="cyan")

        table.add_column("Domain", style="magenta")

        table.add_column("User", style="green")

        table.add_column("Source", style="dim")

        for r in self.find_best_contexts():

            table.add_row(

                str(r["seinfo"]),

                str(r["domain"]),

                str(r["user"]),

                str(r["source"])

            )

        console.print(table)
