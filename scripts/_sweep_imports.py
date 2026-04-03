"""Sweep all app modules for import errors."""

import sys, importlib, glob, traceback

sys.path.insert(0, ".")
sys.path.insert(0, "app/services")
sys.path.insert(0, "app/tabs")

files = sorted(
    glob.glob("app/services/*.py")
    + glob.glob("app/tabs/*.py")
    + glob.glob("app/ui/*.py")
    + glob.glob("app/utils/*.py")
    + glob.glob("app/core/*.py")
    + glob.glob("modules/*.py")
)

fails = []
for f in files:
    if "__pycache__" in f or f.endswith(".old") or f.endswith(".backup"):
        continue
    modpath = f.replace("/", ".").replace(".py", "")
    try:
        importlib.import_module(modpath)
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        origin = tb[-1] if tb else None
        loc = f'{origin.filename.split("printify_clean/")[-1]}:{origin.lineno}' if origin else "?"
        fails.append((modpath, type(e).__name__, str(e)[:150], loc))

print(f"\n=== {len(fails)} IMPORT FAILURES ===")
for mod, etype, emsg, loc in fails:
    print(f"\nFAIL [{etype}] {mod}")
    print(f"     at {loc}")
    print(f"     {emsg}")
print()
