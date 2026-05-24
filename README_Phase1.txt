多Agent面试系统 Phase 1 验收成果

目录说明：

1. blackboard_day5_7
   FastAPI 后端 Orchestrator、Blackboard、Resume/JD/Knowledge Context、Mock Interview、Report 等。

2. interview-assistant-stage4-whisper
   Electron + React + Vite 前端源码。已排除 node_modules，需要在该目录执行 npm install 后再启动。

3. start-all.bat
   一键启动脚本。复制到桌面使用时，默认依赖桌面上的原项目路径；如果移动项目目录，需要同步修改脚本路径。

4. docs
   启动说明、演示脚本、最终验收记录和备份命令。

后续导入 Git / GitHub 建议：

- 不要提交 node_modules、__pycache__、临时音频、临时截图、模型缓存。
- 先创建 .gitignore，再 git init。
- GitHub 仓库建议命名：atlas-multi-agent-interview-system 或 atlas-interview-assistant-phase1。
