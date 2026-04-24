import subprocess
import os

def generate_elf(file_name, board_type="atmega8"):
    """
    Compiles a .c file into an .elf file only.
    Useful for checking code size and debugging.
    """
    board_map = {
        "atmega8": {"mcu": "atmega8"},
        "atmega328p": {"mcu": "atmega328p"},
        "atmega32": {"mcu": "atmega32"}
    }
    
    specs = board_map.get(board_type, board_map["atmega8"])
    c_file = f"{file_name}.c"
    elf_file = f"{file_name}.elf"

    if not os.path.exists(c_file):
        return f"Error: {c_file} not found."

    try:
        # Compile to ELF
        print(f"Compiling {c_file} to {elf_file}...")
        result = subprocess.run([
            "avr-gcc", f"-mmcu={specs['mcu']}", "-Os", 
            "-o", elf_file, c_file
        ], check=True, capture_output=True, text=True)
        
        return f"Success: {elf_file} generated."

    except subprocess.CalledProcessError as e:
        return f"Compilation Failed!\n{e.stderr}"

# Example Usage:
# print(generate_elf("calculator"))