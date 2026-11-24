import sys
import shlex

class ReplSkin:
    """HKUDS ReplSkin banner and prompt styling for interactive REPL."""

    BANNER = r"""
  ____ _     ___       _                      _   _     _             
 / ___| |   |_ _|     / \   _ __  _   _ _ __ | |_| |__ (_)_ __   __ _ 
| |   | |    | |     / _ \ | '_ \| | | | '_ \| __| '_ \| | '_ \ / _` |
| |___| |___ | |    / ___ \| | | | |_| | | | | |_| | | | | | | | (_| |
 \____|_____|___|  /_/   \_\_| |_|\__, |_| |_|\__|_| |_|_|_| |_|\__, |
                                  |___/                          |___/ 
      Gemini Desktop Agent Harness (HKUDS/CLI-Anything v0.4.1)
"""

    def __init__(self, cli_group):
        self.cli_group = cli_group

    def print_banner(self):
        print(self.BANNER)
        print("Type 'help' for available commands, or 'exit' / 'quit' to leave.")
        print("-" * 70)

    def run(self):
        self.print_banner()
        while True:
            try:
                line = input("gemini-desktop> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting REPL.")
                break

            if not line:
                continue

            if line.lower() in ("exit", "quit", "q"):
                print("Goodbye.")
                break

            try:
                args = shlex.split(line)
            except ValueError as e:
                print(f"Error parsing input: {e}")
                continue

            try:
                self.cli_group.main(args=args, standalone_mode=False)
            except Exception as e:
                print(f"Command error: {e}")
