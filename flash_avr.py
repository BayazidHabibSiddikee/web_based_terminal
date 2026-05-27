"""
AVR Toolchain — Cross-platform build & flash logic.
v3.4 — Added programmer selection, Arduino as ISP support, correct baud rates.
"""

import subprocess
import sys
import os
import shutil
import platform


def get_platform():
    if sys.platform.startswith("win"):
        return "windows"
    if "TERMUX_VERSION" in os.environ or os.path.exists("/data/data/com.termux"):
        return "android"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def default_port():
    p = get_platform()
    if p == "windows":
        return "COM3"
    if p == "android":
        return "/dev/ttyUSB0"
    return "/dev/ttyACM0"


def tool(name):
    found = shutil.which(name)
    if found:
        return name
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
        "linux": "  Ubuntu/Debian: sudo apt install avr-gcc avr-libc avrdude\n  Fedora:        sudo dnf install avr-gcc avr-libc avrdude\n  Arch:          sudo pacman -S avr-gcc avr-libc avrdude",
        "mac":   "  brew install avr-gcc avrdude",
        "windows": "  Option 1: WinAVR from winavr.sourceforge.net\n  Option 2: scoop install avr-gcc avrdude\n  Option 3: choco install avr-gcc avrdude",
        "android": "  pkg install avr-toolchain avrdude",
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

# Fuse hints for internal oscillator
FUSE_HINTS = {
    "atmega8":    {"8MHz": "lfuse=0xE4", "4MHz": "lfuse=0xE2", "1MHz": "lfuse=0xE1"},
    "atmega16":   {"8MHz": "lfuse=0xE4", "4MHz": "lfuse=0xE2", "1MHz": "lfuse=0xE1"},
    "atmega32":   {"8MHz": "lfuse=0xE4", "4MHz": "lfuse=0xE2", "1MHz": "lfuse=0xE1"},
    "atmega32a":  {"8MHz": "lfuse=0xE4", "4MHz": "lfuse=0xE2", "1MHz": "lfuse=0xE1"},
    "atmega328p": {"8MHz": "lfuse=0xE2", "4MHz": "lfuse=0xE2", "1MHz": "lfuse=0x62"},
    "atmega168":  {"8MHz": "lfuse=0xE2", "4MHz": "lfuse=0xE2", "1MHz": "lfuse=0x62"},
    "attiny85":   {"8MHz": "lfuse=0xE2", "4MHz": "lfuse=0xE2", "1MHz": "lfuse=0x62"},
    "attiny84":   {"8MHz": "lfuse=0xE2", "4MHz": "lfuse=0xE2", "1MHz": "lfuse=0x62"},
}

# ── Programmer definitions with correct baud rates ────────────────────────────
# Each programmer has its own baud rate and protocol

PROGRAMMERS = {
    "arduino": {
        "id": "arduino",
        "baud": "115200",
        "desc": "Arduino Uno/Nano (Bootloader — talks to onboard chip)",
        "needs_port": True,
    },
    "arduinoisp": {
        "id": "stk500v1",
        "baud": "19200",
        "desc": "Arduino as ISP (Standard — 19200 baud)",
        "needs_port": True,
    },
    "arduinoisp_leonardo": {
        "id": "arduinoisp",
        "baud": "19200",
        "desc": "Arduino as ISP (Leonardo/Micro/Mega)",
        "needs_port": True,
    },
    "usbasp": {
        "id": "usbasp",
        "baud": None,
        "desc": "USBasp (USB device)",
        "needs_port": False,
    },
    "usbtiny": {
        "id": "usbtiny",
        "baud": None,
        "desc": "USBtinyISP (USB device)",
        "needs_port": False,
    },
    "avrispmkII": {
        "id": "avrispmkII",
        "baud": None,
        "desc": "AVRISP mkII",
        "needs_port": True,
    },
}


def _resolve_paths(file_name):
    file_name = file_name.strip().replace("\\", "/")
    if file_name.endswith(".c"):
        file_name = file_name[:-2]
    if os.path.isabs(file_name):
        abs_path = file_name
    else:
        abs_path = os.path.abspath(file_name)
    return os.path.dirname(abs_path), os.path.basename(abs_path)


def _fcpu_label(f_cpu):
    if not f_cpu:
        return "External (default)"
    mhz = int(f_cpu) / 1000000
    if mhz < 1:
        return f"{int(mhz * 1000)} KHz"
    return f"Internal {int(mhz)} MHz" if mhz <= 8 else f"External {int(mhz)} MHz"


def _fuse_hint(board_type, f_cpu):
    if not f_cpu:
        return None
    mhz = int(f_cpu) / 1000000
    hints = FUSE_HINTS.get(board_type, {})
    for freq_str in ["8MHz", "4MHz", "1MHz"]:
        if abs(mhz - int(freq_str.replace("MHz", ""))) < 0.1:
            fuse = hints.get(freq_str)
            if fuse:
                return fuse
    return None


def list_ports():
    """Returns a list of potential serial ports."""
    plat = get_platform()
    ports = []
    try:
        if plat == "windows":
            import serial.tools.list_ports
            ports = [p.device for p in serial.tools.list_ports.comports()]
        elif plat == "android":
            if os.path.exists("/dev/ttyUSB0"): ports.append("/dev/ttyUSB0")
            if os.path.exists("/dev/ttyUSB1"): ports.append("/dev/ttyUSB1")
        else:
            import glob
            ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
            if not ports and plat == "mac":
                ports = glob.glob("/dev/tty.usb*")
    except ImportError:
        # Fallback if pyserial is not installed
        if plat == "windows":
            ports = ["COM1", "COM2", "COM3", "COM4"]
    except Exception:
        pass
    return ports


# ── Core functions ─────────────────────────────────────────────────────────────

def generate_elf(file_name, board_type="atmega8", f_cpu=None):
    work_dir, base = _resolve_paths(file_name)
    specs = BOARD_MAP.get(board_type, BOARD_MAP["atmega8"])
    c_file  = os.path.join(work_dir, base + ".c")
    elf_file = os.path.join(work_dir, base + ".elf")

    if not os.path.exists(c_file):
        return False, f"Error: Source file not found:\n  {c_file}"

    cmd = [tool("avr-gcc"), f"-mmcu={specs['mcu']}", "-Os", "-Wall"]
    if f_cpu:
        cmd.append(f"-DF_CPU={f_cpu}UL")
    cmd.extend(["-o", elf_file, c_file])

    log = [
        f"Platform : {get_platform()}",
        f"Compiling: {c_file}",
        f"MCU      : {specs['mcu']}",
        f"Clock    : {_fcpu_label(f_cpu)}",
        f"Command  : {' '.join(cmd)}",
        ""
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=work_dir)
        if r.returncode == 0:
            if r.stdout:
                log.append(r.stdout)
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


def generate_hex(file_name, board_type="atmega8", f_cpu=None):
    work_dir, base = _resolve_paths(file_name)
    ok, log = generate_elf(file_name, board_type, f_cpu)
    if not ok:
        return False, log

    elf_file = os.path.join(work_dir, base + ".elf")
    hex_file = os.path.join(work_dir, base + ".hex")

    try:
        objcopy = tool("avr-objcopy")
        r = subprocess.run(
            [objcopy, "-O", "ihex", "-R", ".eeprom", elf_file, hex_file],
            capture_output=True, text=True, cwd=work_dir
        )
        if r.returncode == 0:
            log += f"\nSuccess: {hex_file} created."
            return True, log
        else:
            return False, log + f"\nHEX conversion failed:\n{r.stderr}"
    except RuntimeError as e:
        return False, log + "\n" + str(e)


def flash_avr(file_name, board_type="atmega8", port=None, f_cpu=None,
              programmer_key=None, bitclock=None, do_fuses=False):
    """
    Full pipeline: compile -> hex -> flash.
    programmer_key: key from PROGRAMMERS dict
    bitclock: -B parameter for avrdude (e.g. '32' or '4')
    do_fuses: if True, ONLY write fuses based on f_cpu hint
    """
    if not port or not port.strip():
        port = default_port()

    work_dir, base = _resolve_paths(file_name)
    specs = BOARD_MAP.get(board_type, BOARD_MAP["atmega8"])

    log = ""
    if not do_fuses:
        ok, log = generate_hex(file_name, board_type, f_cpu)
        if not ok:
            return False, log
        hex_file = os.path.join(work_dir, base + ".hex")
    else:
        log = f"FUSE WRITE MODE\nChip: {specs['mcu']}\n"

    # Determine which programmers to try
    if programmer_key and programmer_key in PROGRAMMERS:
        prog_list = [programmer_key]
    else:
        prog_list = ["arduino", "arduinoisp"]

    log += f"\n{'='*48}\n"
    if not do_fuses:
        log += f"Flashing: {os.path.basename(hex_file)}\n"
    log += f"Chip    : {specs['mcu']} ({specs['avrdude']})\n"
    log += f"Port    : {port}\n"
    if bitclock:
        log += f"Bitclock: {bitclock} (-B)\n"
    log += f"{'='*48}\n"

    # Fuse logic
    fuse = _fuse_hint(board_type, f_cpu)
    if do_fuses and not fuse:
        return False, log + "[ERROR] No fuse hint found for this chip/clock combination."

    last_error = ""
    for pk in prog_list:
        prog = PROGRAMMERS[pk]
        try:
            dude = tool("avrdude")
            cmd = [dude, "-c", prog["id"], "-p", specs["avrdude"]]

            if prog["needs_port"]:
                cmd.extend(["-P", port])
                if prog["baud"]:
                    cmd.extend(["-b", prog["baud"]])

            if bitclock:
                cmd.extend(["-B", str(bitclock)])

            if do_fuses:
                # Set fuses
                cmd.extend(["-U", f"{fuse}:m"])
            else:
                # Flash program
                cmd.extend(["-U", f"flash:w:{hex_file}:i"])

            log += f"[{pk}] {prog['desc']}\n"
            log += f"  {' '.join(cmd)}\n\n"

            r = subprocess.run(cmd, capture_output=True, text=True, cwd=work_dir, timeout=60)

            if r.returncode == 0:
                log += f"{'='*48}\n"
                log += f"{'Fuse Write' if do_fuses else 'Flash'} Successful!\n"
                log += f"{'='*48}"
                return True, log
            else:
                last_error = r.stderr or r.stdout or "(no output)"
                if len(last_error) > 500:
                    last_error = last_error[:500] + "\n  ... (truncated)"
                log += f"  Failed: {last_error}\n\n"
        except RuntimeError as e:
            return False, log + "\n" + str(e)
        except subprocess.TimeoutExpired:
            last_error = "Timeout (60s) — check serial connection"
            log += f"  Failed: {last_error}\n\n"

    return False, log + f"All programmers failed.\nLast error:\n{last_error}"

