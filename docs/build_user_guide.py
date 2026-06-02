# -*- coding: utf-8 -*-
"""Generate the Atlas user guide PDF (Chinese) with reportlab CID fonts."""
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    HRFlowable, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

FONT = "STSong-Light"
pdfmetrics.registerFont(UnicodeCIDFont(FONT))

ACCENT = colors.HexColor("#5b4bbd")
MUTED = colors.HexColor("#444444")

styles = getSampleStyleSheet()
title = ParagraphStyle("zhTitle", parent=styles["Title"], fontName=FONT, fontSize=24, textColor=ACCENT, spaceAfter=6, leading=30)
subtitle = ParagraphStyle("zhSub", fontName=FONT, fontSize=11, textColor=MUTED, spaceAfter=14, leading=16)
h1 = ParagraphStyle("zhH1", fontName=FONT, fontSize=15, textColor=ACCENT, spaceBefore=14, spaceAfter=6, leading=20)
h2 = ParagraphStyle("zhH2", fontName=FONT, fontSize=12, textColor=colors.HexColor("#222222"), spaceBefore=8, spaceAfter=3, leading=16)
body = ParagraphStyle("zhBody", fontName=FONT, fontSize=10.5, textColor=colors.HexColor("#1a1a1a"), leading=17, alignment=TA_LEFT, spaceAfter=4)
note = ParagraphStyle("zhNote", fontName=FONT, fontSize=9.5, textColor=MUTED, leading=15, spaceAfter=4)


def P(t, s=body):
    return Paragraph(t, s)


def bullets(items, s=body):
    return ListFlowable(
        [ListItem(Paragraph(x, s), leftIndent=10, value="•") for x in items],
        bulletType="bullet", bulletFontName=FONT, bulletColor=ACCENT, leftIndent=14,
    )


def hr():
    return HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#dddddd"), spaceBefore=6, spaceAfter=6)


def kbd_table(rows):
    data = [[P("快捷键", h2), P("作用", h2)]] + [[P(k, body), P(v, body)] for k, v in rows]
    t = Table(data, colWidths=[55 * mm, 110 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, 0), ACCENT),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0eefb")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


story = []
story.append(P("Atlas 面试助手 · 使用说明", title))
story.append(P("本地多 Agent 实时面试辅助 —— 覆盖「面试前准备 → 面试中辅助 → 面试后复盘」全链路", subtitle))
story.append(hr())

story.append(P("一、它是什么", h1))
story.append(P("Atlas 是一个运行在你本机的多 Agent 面试助手。它把「感知 → 简历/JD 上下文 → 本地检索 → 生成 → 审核」拆成多个协作的 Agent,围绕三个阶段陪你走完整个求职过程:", body))
story.append(bullets([
    "<b>面试前 · 准备</b>:上传简历/JD,做模拟面试陪练,逐题评分并自适应追问,生成复盘报告。",
    "<b>面试中 · 实战</b>:文字 / 截图 / 语音提问,秒级流式给出「要点 + 简历素材 + 可能追问」。",
    "<b>面试后 · 复盘</b>:回看每题评分与问题,生成并导出复盘报告。",
]))
story.append(P("本地优先:简历、问答记录默认存在本机;接入云端模型前会对邮箱/手机号/密钥做脱敏。", note))

story.append(P("二、安装", h1))
story.append(bullets([
    "运行安装包 <b>Interview Assistant-Windows-1.1.0.exe</b>,按提示安装即可(后端已内置打包,无需单独装 Python)。",
    "首次运行可能出现 Windows SmartScreen 提示(因尚未代码签名):点「更多信息」→「仍要运行」。",
    "首次启动后端冷启动需数秒,界面右上角的「后端」状态点变绿即表示就绪。",
]))

story.append(P("三、首次配置(选择回答引擎)", h1))
story.append(P("点击右上角 <b>Settings</b>,在顶部「Atlas 回答引擎」选择模式:", body))
story.append(bullets([
    "<b>混合 / 云端</b>(推荐,速度快):选预设(Groq / DeepSeek / 通义千问等 OpenAI 兼容服务),填入 API Key 保存。可点「测试连接」确认显示 ✓ cloud。",
    "<b>纯本地</b>(零成本、最私密):需先安装 Ollama 并拉取模型(如 qwen2.5:7b);速度取决于本机 CPU。",
]))
story.append(P("Key 仅保存在本机后端,不会回显、不会上传到除所配置服务商以外的任何地方。", note))

story.append(P("四、三幕用法", h1))

story.append(P("① 面试前 · 准备", h2))
story.append(bullets([
    "填写「候选人资料」:<b>目标公司、目标职位、简历为必填</b>;简历/JD 可直接粘贴,或点「上传文件」选择 PDF/TXT/DOCX(后端自动解析为文本)。",
    "选择题数(3 / 5 / 7)→ 点「开始陪练」。系统会结合你的简历、JD、公司职位出题。",
    "逐题作答 → 自动评分 + 给出建议;回答较弱时会自适应追问。",
    "全部答完后生成复盘报告(总分、亮点、待改进、推荐练习、逐题回顾)。",
]))

story.append(P("② 面试中 · 实战", h2))
story.append(bullets([
    "<b>文字</b>:输入问题,流式逐字给出答案,并显示评审(Critic)、上下文/检索来源、Agent 链路。",
    "<b>截图</b>:对屏幕上的题目截图 → OCR 识别 → 给出答案(适合算法/系统设计题)。",
    "<b>语音</b>:录音 → 本地 Whisper 转写 → 给出答案(首次使用会下载语音模型,稍慢)。",
    "答案支持 Markdown 排版(标题、列表、代码块等)。窗口对屏幕共享不可见。",
]))

story.append(P("③ 面试后 · 复盘", h2))
story.append(bullets([
    "查看历史记录(每题的类型、Agent、评分、问题)。",
    "点「生成复盘报告」汇总本轮表现;可「导出 Markdown」保存;也可「清空历史 / 重置会话」。",
]))

story.append(P("五、快捷键", h1))
story.append(kbd_table([
    ("Ctrl + Shift + A", "截图问答(对屏幕题目截图 → OCR → 答案)"),
    ("Ctrl + Shift + V", "把剪贴板里的题目发给 Atlas(流式作答)"),
    ("Ctrl + B", "显示 / 隐藏窗口(隐形悬浮,对屏幕共享不可见)"),
    ("Ctrl + Q", "退出应用"),
    ("Ctrl + [ / ]", "降低 / 提高窗口不透明度"),
    ("Ctrl + 方向键", "移动窗口位置"),
]))

story.append(P("六、语言切换", h1))
story.append(P("右上角「中 / EN」一键切换:界面文案、模拟面试题目、以及回答语言都会随之切换。", body))

story.append(P("七、常见问题", h1))
story.append(bullets([
    "<b>右上「后端」点不变绿 / 一直转</b>:首次冷启动需等数秒;若长时间不绿,确认 8000 端口未被占用,或重启应用。",
    "<b>SmartScreen 拦截</b>:点「更多信息 → 仍要运行」(未签名所致,属正常)。",
    "<b>语音第一次很慢</b>:首次会下载 Whisper 模型;弱机可在系统环境变量设 ATLAS_WHISPER_MODEL=tiny 加速。",
    "<b>回答很慢</b>:多为「纯本地」模式 7B 模型在 CPU 上较慢;配置云端 Key 走「混合/云端」会快很多。",
    "<b>怎么退出</b>:Ctrl+Q;窗口看不见时多半是被 Ctrl+B 隐藏了,再按一次即可显示。",
]))

story.append(Spacer(1, 8))
story.append(hr())
story.append(P("数据目录(简历/JD/资料/记录)位于:%APPDATA%\\interview-assistant-v1\\atlas_data", note))
story.append(P("Atlas · 多智能体 AI 面试助手 · 使用说明 v1.1", note))

doc = SimpleDocTemplate(
    "Atlas_使用说明.pdf", pagesize=A4,
    leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=16 * mm,
    title="Atlas 面试助手 使用说明",
)
doc.build(story)
print("PDF written: Atlas_使用说明.pdf")
