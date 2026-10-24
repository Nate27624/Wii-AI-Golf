"""Installed package entrypoint: python -m wii_ai_golf."""
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
