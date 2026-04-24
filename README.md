# Web-Based Terminal & AVR Flasher

A custom Python-based web server that provides a web terminal interface and AVR build/flash capabilities.

## Features

- **Web Terminal**: Execute raw shell commands via the `/run` endpoint.
- **AVR Toolchain Integration**:
  - Generate ELF files.
  - Generate HEX files.
  - Flash AVR boards (e.g., atmega8) directly from the web interface.
- **System Info**: An `/about` page that displays system information using `fastfetch`.
- **Lightweight Server**: Built using Python's `socket` module for minimal overhead.

## Getting Started

### Prerequisites
- Python 3
- `fastfetch` (for the `/about` page)
- AVR toolchain (if using the flashing features)

### Running the Project
To start the server, run:
```bash
python main.py
```
Once started, visit `http://localhost:8090` in your browser.

**Note:** The project will not work by simply opening `index.html` in a browser; you must run the Python server for the terminal and AVR features to function.

## Project Structure
- `main.py`: The core web server handling requests and routing.
- `flash_avr.py`: Logic for flashing and generating AVR files.
- `gen_elf.py` / `gen_hex.py`: Helper scripts for file generation.
- `index.html`: The frontend terminal interface.
