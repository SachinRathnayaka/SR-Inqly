"""Start SR Inqly from a source checkout."""
from pathlib import Path
import runpy
import sys

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / 'src'))
runpy.run_path(str(root / 'src' / 'launcher.py'), run_name='__main__')
