"""Run the LoRa interactive console as a Python module."""

import typer

from tools.lora_chat.cli import main

if __name__ == "__main__":
    typer.run(main)
