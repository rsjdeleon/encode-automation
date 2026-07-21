"""Compatibility wrapper for scripts/generate_key.py."""

import os
import runpy


if __name__ == "__main__":
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "generate_key.py")
    runpy.run_path(script_path, run_name="__main__")