import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
src_dir = ROOT / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
