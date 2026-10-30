"""
Hydrus Network - PixAI Tagger (Windows No-Console Launcher)
===========================================================
Filename: hydrus_pixai_tagger.pyw

Double-clicking this file executes `hydrus_pixai_tagger.py` without opening
or keeping a Windows command prompt / console window open in the background.
"""

from pathlib import Path
import runpy
import sys

if __name__ == "__main__":
    target = Path(__file__).resolve().with_suffix(".py")
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name="__main__")
