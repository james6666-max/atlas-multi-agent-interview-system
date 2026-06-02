# Atlas — 本地测试详细流程 (dev)

分 6 层:环境自检 → 后端自动化 → 后端手动 API → 整体启动 → 功能逐项冒烟 → LLM 三模式。
命令以 Windows 为准(后端 conda 环境名假设为 `chuangxin`;前端目录 `interview-assistant-stage4-whisper`)。

---

## 0. 环境自检(一次性)
```bat
:: 后端
conda activate chuangxin
cd blackboard_day5_7
pip install -r requirements.txt
python -c "import fastapi, uvicorn, faster_whisper, rapidocr_onnxruntime, jsonschema, multipart; print('backend deps OK')"

:: 前端
cd ..\interview-assistant-stage4-whisper
node -v        & rem 需 18+
npm install

:: (可选) 本地 LLM
ollama --version
ollama pull qwen2.5:7b
```
检查端口空闲:`8000`(后端)、`54321`(前端 vite)。

---

## 1. 后端自动化测试(最快的回归,无需 LLM/联网)
`USE_OLLAMA=false` 时走 stub,不依赖 Ollama/云端,几秒跑完。
```bat
cd blackboard_day5_7
set USE_OLLAMA=false
python scripts\check_phase2.py
```
PowerShell:`$env:USE_OLLAMA="false"; python scripts\check_phase2.py`

**期望输出(成功基线):**
```
108 passed
Phase2 smoke passed.
accuracy: 1.0
failed_cases_count: 0
Phase2 check passed.
```
它串了:`py_compile` → 108 单测(pytest) → smoke(/config/status、技术题、行为题、ignored、blackboard) → 50 题评测 250/250。
> 该脚本会自动备份/还原 `blackboard_instance.json`、`atlas_settings.json`,不污染工作树。

单独跑某层:
```bat
python -m pytest tests -q            & rem 仅单测
python scripts\smoke_phase2.py       & rem 仅冒烟
python evals\run_phase2_eval.py      & rem 仅评测
```

---

## 2. 后端手动 API 测试(真实 LLM)
起后端(真实模型路径,需 Ollama 运行或已在 Settings 配云端 key):
```bat
cd blackboard_day5_7
python -m uvicorn orchestrator_v0:app --host 127.0.0.1 --port 8000
```
- 打开 `http://127.0.0.1:8000/docs` 用 Swagger 点接口。
- 状态:`GET /config/status`、`GET /config/llm`、`GET /blackboard`。
- 非流式问答:`POST /ask`  body `{"question":"What is a hash map?","language":"English"}`。
- 流式:`POST /ask_stream`(SSE,Swagger 看不出流式效果,用前端或 curl 看)。
- trace:先 `/ask` 拿 `session_id`,再 `GET /trace/{session_id}`。
- 陪练:`POST /practice/start` `{"num_questions":4,"language":"en"}` → `/practice/answer` → `/practice/report`。

> **注意(Windows Git Bash 坑)**:`curl -d` 里带**中文**会被 shell 编码搞乱 → 报 422/乱码。测中文请用 **Swagger UI**、**PowerShell** 或直接用前端;英文 curl 没问题。

---

## 3. 整体启动(前端 + 后端)
一键:
```bat
:: 项目根目录
start-all.bat
```
会开两个窗口:后端 uvicorn(:8000)+ 前端 `npm run dev`(:54321,vite-plugin-electron 自动拉起 Electron 单窗口)。

或手动两个终端:
```bat
:: 终端 A
cd blackboard_day5_7 && conda run -n chuangxin python -m uvicorn orchestrator_v0:app --port 8000
:: 终端 B
cd interview-assistant-stage4-whisper && npm run dev
```
**期望**:只弹**一个** Electron 窗口、无 "Cannot find module main.js" 错误框、控制台不再刷 `'input'` 报错。

---

## 4. 功能逐项冒烟(在 Electron 窗口里)

| # | 操作 | 期望结果 |
|---|---|---|
| 1 | 看右上角 Backend 状态 | Connected(绿)。否则查后端是否在 :8000 |
| 2 | **Settings** → Atlas 回答引擎 | 能选模式;填云端 key 保存后 toast 成功、key 不回显("key set") |
| 3 | **文字**标签输入 "解释一下哈希表" → 提交 | **流式**逐字出答案 + 首字/总耗时徽章 + Critic 评审 + 上下文/RAG + Agent 链路(真 trace) |
| 4 | **截图**标签 / 全局 `Ctrl+Shift+A` | 截图 → OCR → 出答案(切到 OCR 标签) |
| 5 | **语音**标签 → 录音 → 发送 | Whisper 转写 → 出答案(首次会下载模型,稍慢) |
| 6 | 复制剪贴板一道题 → `Ctrl+Shift+V` | 自动切文字标签、填入并流式作答 |
| 7 | Action Center 顶部**陪练** → 开始(5题) | 出题 → 作答评分 → 自适应追问 → 5 轮后复盘报告(雷达/逐题/建议) |
| 8 | 右上角 **中/EN** 切换 | 界面文案 + 练习题目 + 回答语言 hint 全部切换 |
| 9 | `Ctrl+B` | 窗口隐藏/显示;开 Zoom/腾讯会议共享屏幕,确认窗口对观众不可见 |
| 10 | 故意制造前端错误(如断后端再操作) | 不白屏(ErrorBoundary 兜底;后端断只显示 Disconnected) |

---

## 5. LLM 三模式分别验证
在 Settings → Atlas 回答引擎切换后,各问一题:
- **Hybrid + 云端 key**:首字 < 1s、流畅流式;Answer 面板 provider 徽章显示 `cloud`。
- **Local only**(需 Ollama):能出答案但偏慢(7B/CPU 秒级);provider 显示 `ollama`。
- **无 key 且无 Ollama**:`/ask` 会 fallback;`check_phase2`(USE_OLLAMA=false)用 stub —— 仅用于回归,不代表真实体验。
- **隐私**:配了云端 key 后,后端发云端前会对邮箱/手机号/key 做脱敏(`app/privacy`,有单测覆盖)。

---

## 6. 故障排查

| 现象 | 处理 |
|---|---|
| 启动弹 "Cannot find module main.js" | 已修(dev 脚本去掉了重复 electron 启动);确认用的是当前 `package.json` 的 `dev` 脚本,关掉残留 electron 进程重启 |
| 白屏 | 已修(formatPrice 容错 + ErrorBoundary);若仍白屏看控制台报错贴我 |
| Backend Disconnected | 后端没在 :8000;看终端 A 是否报错(缺依赖/端口占用) |
| 端口占用 | 关掉旧 uvicorn/electron;或换端口(前端固定 54321,后端可改 `--port` 但前端默认连 8000) |
| 中文 curl 422/乱码 | 用 Swagger/PowerShell/前端,别用 Git Bash 的 `curl -d` 传中文 |
| 语音/截图很慢或失败 | 首次会下载 Whisper 模型;`set ATLAS_WHISPER_MODEL=tiny` 加速;OCR 用本地 rapidocr |

---

## 7. 提交前最小清单
1. `set USE_OLLAMA=false && python scripts\check_phase2.py` → 108 passed / 250/250。
2. 前端 `npm run typecheck` + `npm run build` 通过。
3. 第 4 节冒烟手过一遍(尤其流式、陪练、中/EN、热键)。
4. 确认 `blackboard_instance.json` 未被意外改动、无 `atlas_settings.json` 泄露(已 gitignore)。

打包(Windows 安装包)流程见 `docs/RUNBOOK_PACKAGING.md`。
