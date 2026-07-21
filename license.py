"""Compatibility wrapper for core.license."""

import runpy

from core.license import *  # noqa: F401,F403


if __name__ == "__main__":
    runpy.run_module("core.license", run_name="__main__")
