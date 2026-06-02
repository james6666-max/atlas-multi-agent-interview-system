# Atlas · 多智能体 AI 面试助手

> 本地优先的多 Agent 实时面试辅助 —— 覆盖 **面试前准备 → 面试中辅助 → 面试后复盘** 全链路。

Atlas 把"面试"拆成多个协作的 Agent(感知 / 简历画像 / 检索 / 技术 / 行为 / 评审),通过共享黑板事件总线协同,围绕求职的三个阶段陪你走完整个过程。中英双语,本地优先,可选接入云端模型。

**当前状态**:后端 112 单测通过 · 50 题评测 250/250 · 可打包为 Windows 安装包(内置后端,开箱即用)。

---

## ✨ 功能特性

- **三幕闭环**:模拟面试陪练 → 实时问答辅助 → 复盘报告,一个应用走完。
- **多 Agent 协同**:Perception → Resume + RAG → Tech / Behavioral → Critic,事件驱动、可观测(真实 trace)。
- **分级 LLM 路由**:本地 Ollama + 云端 OpenAI 兼容服务(Groq / DeepSeek / 通义千问…),`hybrid` 云端优先、失败回落本地;支持 **SSE 流式**输出。
- **隐私守护**:本地优先存储;发往云端前对邮箱 / 手机号 / 密钥做**出站脱敏**。
- **多模态输入**:文字、截图 OCR(本地 RapidOCR)、语音 STT(本地 faster-whisper)。
- **候选人资料**:简历 / JD 可粘贴或上传(支持 **PDF / TXT / DOCX** 解析),填写目标公司 / 职位 / 重点 → 结合信息**定制出题**。
- **陪练评分**:逐题规则化评审(AI 腔 / 隐私 / 长度 / 简历事实 / 技术质量),自适应追问,复盘报告。
- **中 / EN 全局切换**:界面文案、模拟题目、回答语言一键切换。
- **实战体验**:全局热键、Markdown 渲染、防截屏隐形悬浮窗、顶层 ErrorBoundary 防白屏。

---

## 🧭 三幕用法

| 阶段 | 做什么 |
|---|---|
| **① 面试前 · 准备** | 填候选人资料(公司/职位/简历必填,可上传 PDF)→ 选题数 → 开始模拟面试 → 逐题评分 + 自适应追问 → 复盘报告 |
| **② 面试中 · 实战** | 文字 / 截图 / 语音提问 → 秒级**流式**给出「要点 + 简历素材 + 可能追问」+ Critic 评审 + Agent 链路 |
| **③ 面试后 · 复盘** | 回看历史与逐题评分 → 生成 / 导出复盘报告 |

---

## 🏗️ 技术架构

```
Electron + React 前端 (三幕界面 / 流式渲染 / 中英 i18n)
        │  REST + SSE  (127.0.0.1:8000)
        ▼
FastAPI 后端 (orchestrator_v0:app)
  ├─ Blackboard 事件总线 (内存) + Orchestrator 链式分发
  ├─ Agents: Perception → Resume → RAG → Tech / Behavioral → Critic
  ├─ LLM 路由: 本地 Ollama  +  云端 OpenAI 兼容 (hybrid / 回落 / 脱敏)
  ├─ Coaching: 简历/JD/公司职位 驱动出题 + 评分 + 复盘
  └─ 多模态: RapidOCR (截图) · faster-whisper (语音)
```

**主要接口**:`/ask`、`/ask_stream`(SSE)、`/ask_image_file`、`/ask_audio`、`/practice/{start,answer,state,report}`、`/profile`、`/profile/parse_file`、`/config/llm`(GET/POST)、`/config/llm/test`、`/trace/{session_id}`、`/report/session`、`/blackboard`。

---

## 🧱 技术栈

- **后端**:Python · FastAPI · Uvicorn · Pydantic · faster-whisper · rapidocr-onnxruntime · pypdf
- **前端**:Electron · React 18 · TypeScript · Vite · react-markdown
- **模型**:本地 Ollama(如 `qwen2.5:7b`)/ 任意 OpenAI 兼容云端服务
- **打包**:PyInstaller(后端 sidecar)+ electron-builder(NSIS 安装包)

---

## 📁 目录结构

```
.
├─ blackboard_day5_7/              # 后端 (FastAPI)
│  ├─ orchestrator_v0.py           #   应用入口 app + 路由 + 多模态
│  ├─ run_backend.py               #   冻结打包入口
│  ├─ atlas_backend.spec           #   PyInstaller 配置
│  ├─ app/                         #   agents / blackboard / orchestrator / llm / rag / resume / coaching / critic / paths
│  ├─ evals/ · scripts/ · tests/   #   评测 / 冒烟+检查脚本 / 单测
│  └─ resume.txt · jd.txt · knowledge.txt · blackboard_schema.json
├─ interview-assistant-stage4-whisper/   # 前端 (Electron + React)
│  ├─ src/                         #   pages / components / hooks / i18n / api
│  └─ electron/                    #   main · preload · shortcuts · backend-launcher
├─ docs/                           # 文档 (本地测试 / 打包 runbook / 使用说明.pdf …)
├─ start-all.bat                   # 一键本地启动 (后端 + 前端 dev)
└─ build-windows.bat               # 一键 Windows 打包
```

---

## 🚀 快速开始(开发)

**前置**:Python(conda 环境,示例名 `chuangxin`)、Node 18+;LLM 二选一(本地 [Ollama](https://ollama.com) 或一个云端 API Key)。

```bat
:: 后端依赖
conda activate chuangxin
pip install -r blackboard_day5_7\requirements.txt

:: 前端依赖
cd interview-assistant-stage4-whisper && npm install && cd ..

:: 一键启动(后端 :8000 + 前端 dev :54321,自动拉起 Electron)
start-all.bat
```

启动后右上角「后端」状态点变绿即就绪。打开 **Settings** 配置回答引擎(见下)。

---

## 🤖 LLM 配置

打开 **Settings → Atlas 回答引擎**:

- **混合 / 云端**(推荐,快):选预设(Groq / DeepSeek / 通义千问)填 API Key → 保存 → 点「测试连接」应显示 `✓ cloud`。
- **纯本地**(零成本/最私密):需 `ollama pull qwen2.5:7b`,选 Local only。

> Key 仅存于本机后端,不回显、不上传到所配置服务商之外的任何地方。

---

## ✅ 测试

```bat
cd blackboard_day5_7
set USE_OLLAMA=false
python scripts\check_phase2.py
```
成功基线:`112 passed` · `accuracy: 1.0`(250/250)· `smoke passed`。
前端:`npm run typecheck` + `npm run build`。详见 `docs/LOCAL_TESTING.md`。

---

## 📦 打包(Windows 安装包)

```bat
:: 仓库根目录,一条命令:装依赖 → PyInstaller 冻结后端 → electron-builder 出 NSIS 安装包
build-windows.bat
```
产物:`interview-assistant-stage4-whisper\release\Interview Assistant-Windows-<版本>.exe`(**单文件安装包,内置后端**)。详见 `docs/RUNBOOK_PACKAGING.md`。

> 分发给测试者:发该 `.exe` 即可;首次运行若有 SmartScreen 提示(尚未代码签名)→「更多信息 → 仍要运行」。

---

## ⌨️ 快捷键

| 快捷键 | 作用 |
|---|---|
| `Ctrl + Shift + A` | 截图问答(OCR → 答案) |
| `Ctrl + Shift + V` | 剪贴板题目 → 流式作答 |
| `Ctrl + B` | 显示 / 隐藏窗口(对屏幕共享不可见) |
| `Ctrl + Q` | 退出 |
| `Ctrl + [ / ]` | 调整窗口不透明度 |
| `Ctrl + 方向键` | 移动窗口 |

---

## 🔒 数据与隐私

- 用户数据(简历 / JD / 资料 / 问答记录)默认本地存储:
  - 开发态:`blackboard_day5_7/`
  - 打包态:`%APPDATA%` 下应用 userData 目录中的 `atlas_data\`(后端日志 `atlas-backend.log` 也在该 userData 目录)
- 仅在你主动配置云端模型时才联网;联网前对 PII / 密钥脱敏。

---

## 📚 文档

- `docs/Atlas_使用说明.pdf` —— 面向使用者的图文说明
- `docs/LOCAL_TESTING.md` —— 本地测试详细流程
- `docs/RUNBOOK_PACKAGING.md` —— Windows 打包手册
- `PROJECT_STRUCTURE.md` —— 结构说明

---

## 📄 许可与致谢

前端客户端外壳基于开源的 interview-coder 项目改写(AGPL-3.0)。本仓库整体沿用 **AGPL-3.0-or-later**。多模态与多 Agent 后端为本项目自研。
