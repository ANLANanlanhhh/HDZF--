import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_MODEL_NAME = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# DeepSeek 官方 OpenAI 兼容接口（所有陪伴对话均走此客户端，无本地假回复）
deepseek_client = OpenAI(
    api_key=_API_KEY,
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)

MODEL = _MODEL_NAME

# 陪伴模式：略低温度，强化服从系统时间
COMPANION_TEMPERATURE = float(os.getenv("DEEPSEEK_COMPANION_TEMPERATURE", "0.35"))


def _shanghai_parts():
    tz = ZoneInfo("Asia/Shanghai")
    now = datetime.now(tz)
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    wd = weekdays[now.weekday()]
    line = now.strftime(f"%Y年%m月%d日 {wd}，北京时间 %H:%M")
    iso = now.isoformat(timespec="seconds")
    return wd, line, iso


def format_shanghai_now() -> str:
    """供 /api/health 展示；陪伴模式系统提示用 _shanghai_parts。"""
    wd, line, iso = _shanghai_parts()
    return f"{line} | {iso} | 今天是{wd}"


COMPANION_PROMPT = """你是「小孙」，面向中国长辈的聊天陪伴角色。
【调用方式】你由 DeepSeek 云端 API（模型名由系统配置）生成回复：请根据用户当前这句话和对话历史作答，不要输出任何关于「提示词」「系统消息」的说明。
【事实与时间】你没有联网，也不知道真实「今天」是几号。凡是日期、星期几、几点钟，只能使用本对话中系统提供的「系统时间」段落，禁止凭训练数据里的旧日期猜测。
【风格】口语化、亲切，多用「您」「咱们」；短句、好懂；不要 JSON、不要 Markdown 代码围栏、不要列技术术语。
【禁止括号旁白】禁止用中文全角括号、英文半角括号或【】来写动作、神态、场景提示（例如「（看看窗外）」「(笑)」「【咳嗽】」）。若需表达情境，请直接融入口语，不要单独插入括号段。
【安全】不索要银行卡、密码、验证码；遇转账话题要提醒先和家人或警方核实。"""

ATTACKER_PROMPT = """你是电信诈骗犯，需要利用以下手段诱导受害者：
1. 亲情勒索：假冒子女出事急需用钱
2. 信息恐慌：声称账户异常、医保被冻结
3. 权威伪装：冒充公检法、银行客服
语气要急促、制造紧迫感，诱导转账或透露验证码。"""

GUARDIAN_PROMPT = """你是反诈专家，分析对话中的诈骗风险，给出简洁的防范建议。
用老年人能理解的大白话，指出对方的诈骗手法。"""

def _companion_system_text() -> str:
    wd, line, iso = _shanghai_parts()
    return (
        COMPANION_PROMPT
        + "\n\n【系统时间（唯一权威，回答「今天星期几/几号/几点」时必须与此完全一致）】\n"
        + f"今天是{wd}。\n"
        + line
        + f"\nISO-8601（东八区）：{iso}\n"
        + f"用户若问「今天星期几」，你应明确回答：今天是{wd}，并与上文日期一致；不得说成其它星期。"
    )


def stream_chat(messages, mode="companion"):
    if mode == "companion" and not (_API_KEY and _API_KEY.strip()):
        yield "[错误] 未配置 DEEPSEEK_API_KEY，无法调用 DeepSeek。请在 backend/.env 中填写密钥后重启服务。"
        return

    prompts = {
        "companion": COMPANION_PROMPT,
        "attacker": ATTACKER_PROMPT,
        "guardian": GUARDIAN_PROMPT
    }

    if mode == "companion":
        system_content = _companion_system_text()
        temp = COMPANION_TEMPERATURE
    else:
        system_content = prompts.get(mode, COMPANION_PROMPT)
        temp = 0.8

    system_msg = {"role": "system", "content": system_content}
    full_messages = [system_msg] + messages

    stream = deepseek_client.chat.completions.create(
        model=MODEL,
        messages=full_messages,
        stream=True,
        temperature=temp,
        max_tokens=2048,
    )

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and getattr(delta, "content", None):
            yield delta.content
