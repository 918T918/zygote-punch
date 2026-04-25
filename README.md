# Zygote Injection Toolkit (CVE-2024-31317)

[![Kali Compatible](https://img.shields.io/badge/Kali-Compatible-blueviolet.svg)](https://www.kali.org/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

An advanced command-line utility for security researchers and forensics professionals to exploit the **Android Zygote Injection** vulnerability (CVE-2024-31317). This toolkit allows for system-level access (UID 1000) on vulnerable Android devices, enabling private app data extraction, system modification, and bootloader unlocking bypasses.

> [!WARNING]
> **This tool is for educational and research purposes only.** Use it only on devices you own or have explicit permission to test. Exploiting devices without authorization is illegal.

## 🚀 Features

-   **Automatic Vulnerability Check:** Quickly determine if a connected device is susceptible.
-   **System-Level Access:** Gain a shell as `system` (UID 1000) or any specific app's UID.
-   **Data Extraction (Forensics):** Backup and Restore private app data (`/data/data/<package>`) even if `android:allowBackup="false"`.
-   **OEM Unlocking Bypass:** Attempt to lift carrier-imposed restrictions on OEM unlocking.
-   **Interactive Wizard:** A user-friendly CLI wizard for those who prefer not to use complex flags.
-   **Kali-Style Interface:** Rich terminal output with colors, tables, and progress indicators.

## 📦 Installation

The recommended way to install the toolkit is via `pipx`, which keeps it isolated and available globally.

```bash
# Install pipx if you haven't already
sudo apt update && sudo apt install pipx
pipx ensurepath

# Install Zygote Injection Toolkit directly from the repository
pipx install git+https://github.com/Anonymous941/zygote-injection-toolkit
```

Alternatively, for development:
```bash
git clone https://github.com/Anonymous941/zygote-injection-toolkit
cd zygote-injection-toolkit
pip install -e .
```

## 🛠 Usage

Ensure ADB is installed and USB Debugging is enabled on your target device.

### Interactive Mode (Recommended)
Simply run the toolkit without arguments to start the wizard:
```bash
zygote-punch
```

### Command Line Interface
```bash
zygote-punch [ACTION] [OPTIONS]
```

**Actions:**
*   `check`: Check if the device is susceptible.
*   `exploit`: Run Stage 1 & 2 (attempts OEM unlock by default).
*   `shell`: Open an interactive system shell.
*   `backup`: Backup private data of an app.
*   `restore`: Restore private data to an app.
*   `info`: Dump detailed system and exploit information.
*   `list-devices`: List all connected Android devices.
*   `analyze-selinux`: Run SELinux policy analysis.

**Examples:**
```bash
# Check vulnerability
zygote-punch check

# Get a system shell
zygote-punch shell

# Dump comprehensive device info
zygote-punch info

# Backup a specific app
zygote-punch backup -p com.android.providers.contacts -o contacts.tar.gz

# Target a specific device by serial
zygote-punch -s R58M123456X shell

# Target a device by Transport ID
zygote-punch -t 15 shell

# Force USB or TCP/IP device
zygote-punch -d shell  # USB
zygote-punch -e shell  # TCP/IP
```

## 🔍 How it Works

The exploit targets a logic flaw in the Zygote process's handling of the `hidden_api_blacklist_exemptions` system setting. By injecting specially crafted arguments into this setting, we can trick Zygote into spawning a new process with our arbitrary code (a netcat listener) running as the `system` user.

### Vulnerability Range
-   **Android Versions:** 10, 11, 12, 13, 14.
-   **Patch Level:** Devices with security patches *older* than **June 1, 2024**.

## 🛡️ About the Exploit
This is **not a root exploit**. It executes code as `uid=1000(system)`. While extremely powerful, it does not provide direct `uid=0(root)` access or the ability to modify read-only partitions (like `/system`). However, it is often a sufficient first step for further privilege escalation or data recovery.

## 🤝 Contributing
Contributions are welcome! Please feel free to submit Pull Requests or report issues.

## ⚖️ License
Distributed under the GPL-3.0 License. See `LICENSE` for more information.
