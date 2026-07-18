"""Launch CyberWatch backend from compiled bytecode modules."""
import importlib.util
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = Path(__file__).resolve().parent
BYTECODE_ROOT = BACKEND_ROOT / "bytecode"

# The editable feed and enrichment packages live alongside this launcher.
# The compiled core still imports them by their original top-level names.
sys.path.insert(0, str(BACKEND_ROOT))


def load_pyc(name: str):
    path = BYTECODE_ROOT / f"{name}.cpython-313.pyc"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# `scheduler` imports `cars`; load the dependency first now that the compiled
# files are no longer in the repository root.
for module in ("models", "normalize", "ws_manager", "cars", "scheduler", "main"):
    load_pyc(module)

if __name__ == "__main__":
    import uvicorn

    # Keep the database and .env file at the repository root.
    os.chdir(PROJECT_ROOT)
    uvicorn.run(sys.modules["main"].app, host="127.0.0.1", port=8000)
