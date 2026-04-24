import subprocess
import sys
import os
import shutil
import platform

# ── Platform detection ─────────────────────────────────────────────────────────
def get_platform():
    """Returns 'windows', 'linux', 'android' (Termux), or 'mac'"""
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
        return "COM3"          # User should override
    if p == "android":
        return "/dev/ttyUSB0"  # OTG USB-Serial on Android
    return "/dev/ttyACM0"      # Linux default (Arduino bootloader)

def tool(name):
    """
    Returns the tool name, ensuring it can be found.
    On Windows avr-gcc ships as avr-gcc.exe but subprocess finds it automatically.
    Raises RuntimeError if the tool is missing.
    """
    found = shutil.which(name)
    if not found:
        raise RuntimeError(
            f"'{name}' not found in PATH.\n"
            f"  Linux  : sudo dnf install avr-gcc avr-libc avrdude\n"
            f"  Windows: Install WinAVR or use Scoop: scoop install avr-gcc\n"
            f"  Android: pkg install avr-toolchain avrdude"
        )
    return name   # subprocess will resolve the full path itself

# ── Board map ──────────────────────────────────────────────────────────────────
BOARD_MAP = {
    "atmega8":    {"mcu": "atmega8",    "avrdude": "m8"},
    "atmega328p": {"mcu": "atmega328p", "avrdude": "m328p"},
    "atmega32":   {"mcu": "atmega32",   "avrdude": "m32"},
    "attiny85":   {"mcu": "attiny85",   "avrdude": "t85"},
}

# Programmer order to try when flashing
PROGRAMMERS = ["arduino", "stk500v1", "avrisp"]

# ── Core functions ─────────────────────────────────────────────────────────────

def _resolve_paths(file_name):
    """
    Accept either:
      - a bare project name:  'calculator'       → looks in CWD
      - an absolute path:     '/home/user/blink' or 'C:\\avr\\blink'
    Returns (dir, base_name) so we can chdir and compile cleanly.
    """
    file_name = file_name.strip()
    # Strip .c extension if the user included it
    if file_name.endswith(".c"):
        file_name = file_name[:-2]

    # If it's already an absolute path, use it. Otherwise, make it absolute.
    if os.path.isabs(file_name):
        abs_path = file_name
    else:
        abs_path = os.path.abspath(file_name)

    work_dir = os.path.dirname(abs_path)
    base     = os.path.basename(abs_path)
    return work_dir, base


def generate_elf(file_name, board_type="atmega8"):
    """Compile .c → .elf. Returns (success:bool, output:str)."""
    work_dir, base = _resolve_paths(file_name)
    specs = BOARD_MAP.get(board_type, BOARD_MAP["atmega8"])
    c_file  = os.path.join(work_dir, base + ".c")
    elf_file = os.path.join(work_dir, base + ".elf")

    if not os.path.exists(c_file):
        return False, f"Error: Source file not found:\n  {c_file}"

    log = [f"Platform : {get_platform()}",
           f"Compiling: {c_file}",
           f"MCU      : {specs['mcu']}"]
    try:
        r = subprocess.run(
            [tool("avr-gcc"), f"-mmcu={specs['mcu']}", "-Os", "-o", elf_file, c_file],
            capture_output=True, text=True, check=True
        )
        log.append(r.stdout)
        log.append(f"Success: {elf_file} generated.")
        return True, "\n".join(filter(None, log))
    except RuntimeError as e:
        return False, str(e)
    except subprocess.CalledProcessError as e:
        log.append(f"Compilation Failed!\n{e.stderr}")
        return False, "\n".join(filter(None, log))


def generate_hex(file_name, board_type="atmega8"):
    """Compile .c → .elf → .hex. Returns (success:bool, output:str)."""
    work_dir, base = _resolve_paths(file_name)
    ok, log = generate_elf(file_name, board_type)
    if not ok:
        return False, log

    elf_file = os.path.join(work_dir, base + ".elf")
    hex_file = os.path.join(work_dir, base + ".hex")

    try:
        r = subprocess.run(
            [tool("avr-objcopy"), "-O", "ihex", "-R", ".eeprom", elf_file, hex_file],
            capture_output=True, text=True, check=True
        )
        log += f"\nSuccess: {hex_file} created."
        return True, log
    except RuntimeError as e:
        return False, log + "\n" + str(e)
    except subprocess.CalledProcessError as e:
        return False, log + f"\nHEX conversion failed:\n{e.stderr}"


def flash_avr(file_name, board_type="atmega8", port=None):
    """
    Full pipeline: compile → hex → flash.
    Tries multiple programmers automatically.
    Returns (success:bool, output:str)
    """
    if port is None or port.strip() == "":
        port = default_port()

    work_dir, base = _resolve_paths(file_name)
    ok, log = generate_hex(file_name, board_type)
    if not ok:
        return False, log

    hex_file = os.path.join(work_dir, base + ".hex")
    specs    = BOARD_MAP.get(board_type, BOARD_MAP["atmega8"])

    log += f"\nFlashing to {port} ({specs['avrdude']})..."

    last_error = ""
    for prog in PROGRAMMERS:
        try:
            r = subprocess.run(
                [tool("avrdude"),
                 "-c", prog,
                 "-p", specs["avrdude"],
                 "-P", port,
                 "-b", "115200",
                 "-U", f"flash:w:{hex_file}:i"],
                capture_output=True, text=True
            )
            if r.returncode == 0:
                log += f"\nFlash Successful! (programmer: {prog})"
                return True, log
            last_error = r.stderr or r.stdout
        except RuntimeError as e:
            return False, log + "\n" + str(e)

    return False, log + f"\nAll programmers failed.\nLast error:\n{last_error}"