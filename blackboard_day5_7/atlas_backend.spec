# PyInstaller spec for the Atlas backend sidecar (onedir -> dist/atlas-backend/).
# Build on Windows:  pyinstaller atlas_backend.spec --noconfirm
#
# The ML deps (faster-whisper / rapidocr-onnxruntime / onnxruntime / ctranslate2)
# ship data files + native libs, so we collect_all() them. This is a best-effort
# starting point — expect to iterate on hidden imports for your exact versions.

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# Heavy / dynamically-loaded packages: pull in code, data and native libs.
for pkg in [
    "rapidocr_onnxruntime",
    "faster_whisper",
    "onnxruntime",
    "ctranslate2",
    "tokenizers",
    "uvicorn",
    "fastapi",
    "jsonschema",
    "pypdf",
]:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:  # pragma: no cover
        print(f"[spec] collect_all({pkg}) skipped: {exc}")

# Our own package + modules referenced via late/dynamic imports.
hiddenimports += collect_submodules("app")
hiddenimports += ["orchestrator_v0", "blackboard_store", "run_backend"]
hiddenimports += collect_submodules("uvicorn")

# Bundled read-only defaults (resolved at runtime via app.paths.resource_dir()).
for name in ["blackboard_schema.json", "blackboard_instance.json", "resume.txt", "jd.txt", "knowledge.txt"]:
    datas.append((name, "."))

block_cipher = None

a = Analysis(
    ["run_backend.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="atlas-backend",
    console=True,  # shows errors on a manual run; Electron hides it via windowsHide
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="atlas-backend",
)
