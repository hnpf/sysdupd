import platform
import os
import subprocess
import getpass

def run_command(command):
    try:
        cmd_list = command.split()
        process = subprocess.run(cmd_list, capture_output=True, text=True, check=False)
        return process.stdout, process.stderr, process.returncode == 0
    except Exception as e:
        return "", str(e), False

def get_system_specs():
    specs = {
        "cpu": "unknown cpu",
        "gpu": "unknown gpu",
        "ram": "unknown ram",
        "user": getpass.getuser()
    }
    
    # cpu
    if os.path.exists("/proc/cpuinfo"):
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    # model name : Intel(R) Core(TM)...
                    specs["cpu"] = line.split(":")[1].strip()
                    break
    
    # ram
    if os.path.exists("/proc/meminfo"):
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if "MemTotal" in line:
                    total_kb = int(line.split(":")[1].strip().split()[0])
                    specs["ram"] = f"{round(total_kb / 1024 / 1024)} GB"
                    break

    # gpu - dynamic parsing
    if os.path.exists("/usr/bin/lspci"):
        stdout, _, _ = run_command("lspci")
        for line in stdout.splitlines():
            # look for vga compatible controller
            if "VGA" in line:
                # format usually: 00:02.0 VGA compatible controller: Intel Corporation ...
                parts = line.split(":", 2) 
                if len(parts) > 2:
                    gpu_name = parts[2].strip()
                    # optionally clean up common noise like (rev xx)
                    if "(" in gpu_name:
                        gpu_name = gpu_name.split("(")[0].strip()
                    specs["gpu"] = gpu_name
                break
    
    return specs

def detect_distro_and_package_manager():
    distro_name = "Linux"
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release", "r") as f:
            for line in f:
                if line.startswith("ID="):
                    distro_name = line.split("=")[1].strip('"').capitalize()
                    break
    
    if os.path.exists("/usr/bin/pacman"):
        return distro_name, "pacman", "pkexec pacman -Sy", "pkexec pacman -Syu --noconfirm", "pacman -Qu"
    
    return distro_name, "unknown", None, None, None

def check_flatpak_updates():
    if os.path.exists("/usr/bin/flatpak"):
        stdout, _, success = run_command("flatpak remote-ls --updates")
        if success:
            return [line.split()[0] for line in stdout.splitlines() if line]
    return []

def check_for_updates(distro_info):
    _, _, update_cmd, _, list_cmd = distro_info
    if not list_cmd: return []
    
    # refresh db
    run_command(update_cmd)
    
    # check updates
    stdout, _, _ = run_command(list_cmd)
    updates = []
    for line in stdout.splitlines():
        # arch output: package version -> new_version
        if " -> " in line:
            updates.append(line.split()[0])
            
    return updates

def apply_updates(distro_info):
    _, _, _, upgrade_cmd, _ = distro_info
    stdout, stderr, success = run_command(upgrade_cmd)
    return success, stdout if success else stderr