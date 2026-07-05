import runpy
import os
import sys

if __name__ == "__main__":
    print("[SERVER] Iniciando KI-TIAN backend para nube (Render)...")
    runpy.run_path("kitian_http_standalone_real.py", run_name="__main__")
