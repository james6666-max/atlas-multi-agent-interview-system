# PyInstaller spec — Atlas backend (LITE / 中期交付版, Option A).
# Build:  pyinstaller atlas_backend_lite.spec --noconfirm   ->  dist/atlas-backend/
#
# 与完整版 atlas_backend.spec 的区别:为把安装包压到 <200MB,本精简版【不打包语音 STT】
# (faster-whisper / ctranslate2 / av / tokenizers ~140MB),保留多 Agent 核心 + 截图 OCR。
# 这是打包期的取舍,不删除任何源码;完整版仍用 atlas_backend.spec 构建。

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# Kept: screenshot OCR (rapidocr + onnxruntime) + web/runtime deps. STT NOT bundled.
for pkg in [
    "rapidocr_onnxruntime",
    "onnxruntime",
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

hiddenimports += collect_submodules("app")
hiddenimports += ["orchestrator_v0", "blackboard_store", "run_backend"]
hiddenimports += collect_submodules("uvicorn")

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
    excludes=[
        "tkinter", "matplotlib",
        # voice STT stack (not bundled in the lite delivery)
        "faster_whisper", "ctranslate2", "av", "tokenizers", "huggingface_hub", "hf_xet",
        # unused onnxruntime tooling / test trees -> trim
        "onnxruntime.tools", "onnxruntime.transformers", "onnxruntime.quantization",
        "pytest", "_pytest", "jsonschema.tests", "jsonschema.benchmarks",
    ],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="atlas-backend",
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="atlas-backend",
)
