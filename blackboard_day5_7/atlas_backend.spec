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
# blackboard_instance.json is intentionally not bundled: it is dev-session
# state, and shipping it seeded demo history into fresh installs. The backend
# creates a clean instance on first launch instead.
for name in ["blackboard_schema.json", "resume.txt", "jd.txt", "knowledge.txt"]:
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
    excludes=[
        "tkinter", "matplotlib",
        # Size trim — none of these affect any shipped feature:
        # hf_xet: optional HF download accelerator; hub falls back to plain HTTP.
        "hf_xet",
        # Pillow AVIF codec (7.5MB): screenshots/uploads are PNG/JPG, AVIF unused.
        "PIL._avif", "PIL.AvifImagePlugin",
        # onnxruntime dev tooling + test trees, never imported at runtime.
        "onnxruntime.tools", "onnxruntime.transformers", "onnxruntime.quantization",
        "pytest", "_pytest", "jsonschema.tests", "jsonschema.benchmarks",
    ],
    cipher=block_cipher,
)

# OpenCV's ffmpeg video-IO DLL (~27MB) is loaded dynamically and only used by
# cv2.VideoCapture; OCR works on still images exclusively, so drop it from the
# bundle. (cv2 imports fine without it — only video decoding would fail.)
a.binaries = [b for b in a.binaries if "opencv_videoio_ffmpeg" not in b[0].lower()]
a.datas = [d for d in a.datas if "opencv_videoio_ffmpeg" not in d[0].lower()]

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
