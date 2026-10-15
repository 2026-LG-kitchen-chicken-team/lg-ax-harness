"""Prepare Claude Code product files; does not install or invoke Claude."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"common"))
from install import main

if __name__=="__main__":
    raise SystemExit(main("claude"))
