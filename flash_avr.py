import subprocess

def flash_avr(project_name, board_type="atmega8"):
    # Mapping friendly names to technical specs
    board_map = {
        "atmega8": {"mcu": "atmega8", "avrdude": "m8"},
        "atmega328p": {"mcu": "atmega328p", "avrdude": "m328p"},
        "atmega38": {"mcu": "atmega32", "avrdude": "m32"}
    }
    
    specs = board_map.get(board_type, board_map["atmega8"])
    
    try:
        # 1. Compile
        print(f"Compiling {project_name} for {specs['mcu']}...")
        subprocess.run([
            "avr-gcc", f"-mmcu={specs['mcu']}", "-Os", 
            "-o", f"{project_name}.elf", f"{project_name}.c"
        ], check=True)

        # 2. Extract Hex
        subprocess.run([
            "avr-objcopy", "-O", "ihex", "-R", ".eeprom", 
            f"{project_name}.elf", f"{project_name}.hex"
        ], check=True)

        # 3. Flash to Hardware
        subprocess.run([
            "avrdude", "-c", "avrisp", "-p", specs['avrdude'], 
            "-P", "/dev/ttyACM0", "-b", "19200", 
            "-U", f"flash:w:{project_name}.hex:i"
        ], check=True)
        
        return "Flash Successful!"
    except:
        try:
                    # 1. Compile
            print(f"Compiling {project_name} for {specs['mcu']}...")
            subprocess.run([
                "avr-gcc", f"-mmcu={specs['mcu']}", "-Os", 
                "-o", f"{project_name}.elf", f"{project_name}.c"
            ], check=True)

            # 2. Extract Hex
            subprocess.run([
                "avr-objcopy", "-O", "ihex", "-R", ".eeprom", 
                f"{project_name}.elf", f"{project_name}.hex"
            ], check=True)

            # 3. Flash to Hardware
            subprocess.run([
                "avrdude", "-c", "stk500v1", "-p", specs['avrdude'], 
                "-P", "/dev/ttyACM0", "-b", "19200", 
                "-U", f"flash:w:{project_name}.hex:i"
            ], check=True)
            
            return "Flash Successful!"
        except subprocess.CalledProcessError as e:
            return f"Error occurred: {e}"

# Example Usage:
# flash_avr("calculator", "atmega8")