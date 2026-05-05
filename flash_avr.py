"""
AVR Toolchain — Cross-platform build & flash logic.
Works on Windows, Linux, macOS, and Android (Termux).
"""

import subprocess
import sys
import os
import shutil
import platform


# ── Platform detection ─────────────────────────────────────────────────────────

def get_platform():
    """Returns 'windows', 'linux', 'android' (Termux), or 'mac'."""
    if sys.platform.startswith("win"):
        return "windows"
    if "TERMUX_VERSION" in os.environ or os.path.exists("/data/data/com.termux"):
        return "android"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def default_port():
    """Guess the most likely serial port for this OS."""
    p = get_platform()
    if p == "windows":
        return "COM3"
    if p == "android":
        return "/dev/ttyUSB0"
    return "/dev/ttyACM0"


def tool(name):
    """
    Returns the tool name if found in PATH.
    On Windows, also checks common WinAVR paths.
    Raises RuntimeError with install instructions if missing.
    """
    found = shutil.which(name)
    if found:
        return name

    # Windows: check common WinAVR install locations
    if get_platform() == "windows":
        winavr_paths = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "WinAVR-20100110", "bin", name + ".exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "WinAVR-20100110", "bin", name + ".exe"),
            "C:\\WinAVR\\bin\\" + name + ".exe",
        ]
        for wp in winavr_paths:
            if os.path.isfile(wp):
                return wp

    install_hints = {
        "linux": (
            f"  Ubuntu/Debian: sudo apt install avr-gcc avr-libc avrdude\n"
            f"  Fedora:        sudo dnf install avr-gcc avr-libc avrdude\n"
            f"  Arch:          sudo pacman -S avr-gcc avr-libc avrdude"
        ),
        "mac": (
            f"  brew install avr-gcc avrdude"
        ),
        "windows": (
            f"  Option 1: Install WinAVR from winavr.sourceforge.net\n"
            f"  Option 2: scoop install avr-gcc avrdude\n"
            f"  Option 3: choco install avr-gcc avrdude"
        ),
        "android": (
            f"  pkg install avr-toolchain avrdude"
        ),
    }
    hint = install_hints.get(get_platform(), "  Check your package manager.")
    raise RuntimeError(f"'{name}' not found in PATH.\n{hint}")


# ── Board map ──────────────────────────────────────────────────────────────────

BOARD_MAP = {
    "atmega8":     {"mcu": "atmega8",     "avrdude": "m8"},
    "atmega8a":    {"mcu": "atmega8a",    "avrdude": "m8a"},
    "atmega16":    {"mcu": "atmega16",    "avrdude": "m16"},
    "atmega16a":   {"mcu": "atmega16a",   "avrdude": "m16a"},
    "atmega32":    {"mcu": "atmega32",    "avrdude": "m32"},
    "atmega32a":   {"mcu": "atmega32a",   "avrdude": "m32a"},
    "atmega328p":  {"mcu": "atmega328p",  "avrdude": "m328p"},
    "atmega328pa": {"mcu": "atmega328pa", "avrdude": "m328p"},
    "atmega88":    {"mcu": "atmega88",    "avrdude": "m88"},
    "atmega88p":   {"mcu": "atmega88p",   "avrdude": "m88p"},
    "atmega168":   {"mcu": "atmega168",   "avrdude": "m168"},
    "atmega168p":  {"mcu": "atmega168p",  "avrdude": "m168p"},
    "atmega644":   {"mcu": "atmega644",   "avrdude": "m644"},
    "atmega644p":  {"mcu": "atmega644p",  "avrdude": "m644p"},
    "atmega128":   {"mcu": "atmega128",   "avrdude": "m128"},
    "atmega1280":  {"mcu": "atmega1280",  "avrdude": "m1280"},
    "atmega2560":  {"mcu": "atmega2560",  "avrdude": "m2560"},
    "attiny85":    {"mcu": "attiny85",    "avrdude": "t85"},
    "attiny84":    {"mcu": "attiny84",    "avrdude": "t84"},
    "attiny84a":   {"mcu": "attiny84a",   "avrdude": "t84a"},
    "attiny841":   {"mcu": "attiny841",   "avrdude": "t841"},
    "attiny24":    {"mcu": "attiny24",    "avrdude": "t24"},
    "attiny44":    {"mcu": "attiny44",    "avrdude": "t44"},
    "attiny45":    {"mcu": "attiny45",    "avrdude": "t45"},
    "attiny25":    {"mcu": "attiny25",    "avrdude": "t25"},
    "attiny2313":  {"mcu": "attiny2313",  "avrdude": "t2313"},
    "attiny13":    {"mcu": "attiny13",    "avrdude": "t13"},
    "attiny13a":   {"mcu": "attiny13a",   "avrdude": "t13a"},
}

PROGRAMMERS = ["arduino", "stk500v1", "avrisp", "usbasp"]


# ── Path resolution ────────────────────────────────────────────────────────────

def _resolve_paths(file_name):
    """
    Accept:
      - bare name:        'blink'          → CWD
      - relative path:    'projects/blink' → CWD/projects
      - absolute path:    '/home/u/blink'  → as-is
      - Windows path:     'C:\\avr\\blink' → as-is
    Strips .c extension if included.
    Returns (work_dir, base_name)
    """
    file_name = file_name.strip().replace("\\", "/")
    if file_name.endswith(".c"):
        file_name = file_name[:-2]

    if os.path.isabs(file_name):
        abs_path = file_name
    else:
        abs_path = os.path.abspath(file_name)

    return os.path.dirname(abs_path), os.path.basename(abs_path)


# ── Core functions ─────────────────────────────────────────────────────────────

def generate_elf(file_name, board_type="atmega8"):
    """Compile .c → .elf. Returns (success, output_string)."""
    work_dir, base = _resolve_paths(file_name)
    specs = BOARD_MAP.get(board_type, BOARD_MAP["atmega8"])
    c_file  = os.path.join(work_dir, base + ".c")
    elf_file = os.path.join(work_dir, base + ".elf")

    if not os.path.exists(c_file):
        return False, f"Error: Source file not found:\n  {c_file}"

    log = [
        f"Platform : {get_platform()}",
        f"Compiling: {c_file}",
        f"MCU      : {specs['mcu']}",
        f"Command  : avr-gcc -mmcu={specs['mcu']} -Os -o {elf_file} {c_file}",
        ""
    ]

    try:
        gcc = tool("avr-gcc")
        r = subprocess.run(
            [gcc, f"-mmcu={specs['mcu']}", "-Os", "-Wall", "-o", elf_file, c_file],
            capture_output=True, text=True,
            cwd=work_dir
        )
        if r.returncode == 0:
            if r.stdout:
                log.append(r.stdout)
            # Show size info
            size_tool = shutil.which("avr-size")
            if size_tool:
                sr = subprocess.run([size_tool, elf_file], capture_output=True, text=True, cwd=work_dir)
                if sr.stdout:
                    log.append(sr.stdout)
            log.append(f"Success: {elf_file} generated.")
            return True, "\n".join(log)
        else:
            log.append("Compilation FAILED:")
            if r.stderr:
                log.append(r.stderr)
            if r.stdout:
                log.append(r.stdout)
            return False, "\n".join(log)
    except RuntimeError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"


def generate_hex(file_name, board_type="atmega8"):
    """Compile .c → .elf → .hex. Returns (success, output_string)."""
    work_dir, base = _resolve_paths(file_name)

    ok, log = generate_elf(file_name, board_type)
    if not ok:
        return False, log

    elf_file = os.path.join(work_dir, base + ".elf")
    hex_file = os.path.join(work_dir, base + ".hex")

    try:
        objcopy = tool("avr-objcopy")
        r = subprocess.run(
            [objcopy, "-O", "ihex", "-R", ".eeprom", elf_file, hex_file],
            capture_output=True, text=True,
            cwd=work_dir
        )
        if r.returncode == 0:
            log += f"\nSuccess: {hex_file} created."
            return True, log
        else:
            return False, log + f"\nHEX conversion failed:\n{r.stderr}"
    except RuntimeError as e:
        return False, log + "\n" + str(e)


def flash_avr(file_name, board_type="atmega8", port=None):
    """Full pipeline: compile → hex → flash. Returns (success, output_string)."""
    if not port or not port.strip():
        port = default_port()

    work_dir, base = _resolve_paths(file_name)

    ok, log = generate_hex(file_name, board_type)
    if not ok:
        return False, log

    hex_file = os.path.join(work_dir, base + ".hex")
    specs    = BOARD_MAP.get(board_type, BOARD_MAP["atmega8"])

    log += f"\n{'='*40}"
    log += f"\nFlashing to {port} (chip: {specs['avrdude']})..."
    log += f"\n{'='*40}\n"

    last_error = ""
    for prog in PROGRAMMERS:
        try:
            dude = tool("avrdude")
            cmd = [
                dude,
                "-c", prog,
                "-p", specs["avrdude"],
                "-P", port,
                "-b", "115200",
                "-U", f"flash:w:{hex_file}:i"
            ]
            log.append(f"Trying programmer: {prog}")
            log.append(f"  {' '.join(cmd)}\n")

            r = subprocess.run(
                cmd, capture_output=True, text=True,
                cwd=work_dir, timeout=60
            )
            if r.returncode == 0:
                log += f"\n{'='*40}"
                log += f"\nFlash Successful! (programmer: {prog})"
                log += f"\n{'='*40}"
                return True, log
            else:
                last_error = r.stderr or r.stdout or "(no output)"
                log.append(f"  Failed with {prog}: {last_error[:200]}\n")
        except RuntimeError as e:
            return False, log + "\n" + str(e)
        except subprocess.TimeoutExpired:
            last_error = "Timeout (60s) — check your serial connection"
            log.append(f"  Failed with {prog}: {last_error}\n")

    return False, log + f"\nAll programmers failed.\nLast error:\n{last_error}"