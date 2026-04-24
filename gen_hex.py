import subprocess
import os

def generate_hex(file_name, board_type="atmega8"):
    """
    Compiles a .c file into an .elf and then extracts the .hex file.
    Assumes file_name is provided without the extension (e.g., 'calculator').
    """
    board_map = {
        "atmega8": {"mcu": "atmega8"},
        "atmega328p": {"mcu": "atmega328p"},
        "atmega32": {"mcu": "atmega32"}
    }
    
    specs = board_map.get(board_type, board_map["atmega8"])
    c_file = f"{file_name}.c"
    elf_file = f"{file_name}.elf"
    hex_file = f"{file_name}.hex"

    # Quick check if the source file even exists
    if not os.path.exists(c_file):
        return f"Error: Source file {c_file} not found."

    try:
        # 1. Compile to ELF
        print(f"Building {elf_file}...")
        subprocess.run([
            "avr-gcc", f"-mmcu={specs['mcu']}", "-Os", 
            "-o", elf_file, c_file
        ], check=True, capture_output=True, text=True)

        # 2. Convert ELF to HEX
        print(f"Generating {hex_file}...")
        subprocess.run([
            "avr-objcopy", "-O", "ihex", "-R", ".eeprom", 
            elf_file, hex_file
        ], check=True, capture_output=True, text=True)
        
        return f"Success: {hex_file} created."

    except subprocess.CalledProcessError as e:
        # This returns the actual compiler error (syntax errors, etc.)
        return f"Build Failed!\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}"

# Example Usage:
# result = generate_hex("calculator")
# print(result)