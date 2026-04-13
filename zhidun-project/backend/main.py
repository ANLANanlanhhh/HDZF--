from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from typing import List
import os
import random
import sqlite3
import json

import edge_tts
from llm_service import stream_chat, MODEL, format_shanghai_now
from tts_cosyvoice import cosyvoice_sft_to_wav, tts_engine_label

app = FastAPI(title="智盾反诈骗系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源
    allow_credentials=False,  # 如果 allow_origins 为 ["*"]，这里必须是 False
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    message: str
    mode: str = "companion"
    response_time: float = 0

class StreamChatRequest(BaseModel):
    messages: List[dict]
    mode: str = "companion"


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class ScenarioRequest(BaseModel):
    scenario_id: str

# 三个智能体的简化实现
class CompanionAgent:
    """情感伴侣智能体"""
    def respond(self, message: str):
        # 情感计算：检测迟疑词汇
        hesitation_words = ["这...", "不太清楚", "嗯...", "呃...", "那个...", "我想想", "不确定"]
        is_hesitant = any(word in message for word in hesitation_words)

        if is_hesitant:
            empathy_responses = [
                "别着急，慢慢说，我听着呢。有什么不明白的，咱们一起琢磨。",
                "没关系的，这些事情确实挺复杂的。您先别担心，我陪着您呢。",
                "您这么谨慎是对的！遇到拿不准的事，多想想总是好的。"
            ]
            return random.choice(empathy_responses)

        responses = [
            "哎呀，您说得对！最近天气变化大，要注意保暖啊。",
            "我记得您上次说腿疼，现在好些了吗？",
            "您孙子考试考得怎么样啊？"
        ]
        return random.choice(responses)

class AttackerAgent:
    """蓝军攻击手智能体"""
    def attack(self, scenario: str):
        scenarios = {
            "qinqing": "喂，是妈妈吗？我是小明啊！我出车祸了，急需5万块钱！",
            "yangsheng": "阿姨您好，我是健康专家，您的体检报告显示有问题，需要购买我们的特效药...",
            "baoxian": "您好，我是支付宝客服，您的账户存在异常，需要验证码..."
        }
        return scenarios.get(scenario, "测试场景")

class GuardianAgent:
    """红军卫士智能体"""
    def check_risk(self, message: str):
        keywords = ["转账", "验证码", "银行卡", "密码", "汇款"]
        return any(k in message for k in keywords)

companion = CompanionAgent()
attacker = AttackerAgent()
guardian = GuardianAgent()

@app.get("/")
def root():
    return {"message": "智盾系统运行中"}


@app.get("/api/health")
def api_health():
    """用于确认后端已加载 DeepSeek 配置；日期以服务器北京时间为准。"""
    return {
        "ok": True,
        "llm": "deepseek",
        "model": MODEL,
        "shanghai_now": format_shanghai_now(),
        "tts": tts_engine_label(),
        "tts_voice": os.getenv("EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural"),
    }


@app.post("/api/tts")
async def api_tts(body: TTSRequest):
    """
    语音合成：若配置 COSYVOICE_URL 则优先走 CosyVoice（本地神经网络，音质更自然）；
    否则或未启用时使用 edge-tts（云端 MP3）。
    """
    text = body.text.strip()
    wav = await cosyvoice_sft_to_wav(text)
    if wav:
        return Response(content=wav, media_type="audio/wav")

    voice = os.getenv("EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")

    async def audio_stream():
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    return StreamingResponse(audio_stream(), media_type="audio/mpeg")

@app.post("/chat")
def chat(msg: ChatMessage):
    if guardian.check_risk(msg.message):
        return {
            "response": "⚠️ 警告！检测到高危词汇！请勿透露个人信息！",
            "alert": True
        }

    if msg.mode == "attack":
        return {"response": attacker.attack("qinqing"), "alert": False}

    # 检测回复缓慢（超过10秒）
    if msg.response_time > 10:
        slow_responses = [
            "您慢慢想，不着急。有什么疑问随时问我。",
            "看您想了这么久，是不是有什么顾虑？跟我说说呗。"
        ]
        return {"response": random.choice(slow_responses), "alert": False}

    return {"response": companion.respond(msg.message), "alert": False}

@app.get("/scenarios")
def get_scenarios():
    return [
        {"id": "qinqing", "name": "亲情陷阱", "difficulty": "中级"},
        {"id": "yangsheng", "name": "养生迷局", "difficulty": "初级"},
        {"id": "baoxian", "name": "百万保障", "difficulty": "高级"}
    ]

def _load_scenarios_from_json_file():
    """数据库未初始化时，从同目录 scenarios.json 读取，便于本地开发未执行 seed 时仍能加载剧本。"""
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "scenarios.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"categories": []}


@app.get("/api/scenarios")
def get_scenarios():
    conn = sqlite3.connect('zhidun.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT data FROM scripts WHERE id = 1')
        result = cursor.fetchone()
        
        if result:
            # 将数据库里存的文本转回 JSON 字典发送给前端
            return json.loads(result[0])
        else:
            return _load_scenarios_from_json_file()
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

@app.post("/start-scenario")
def start_scenario(req: ScenarioRequest):
    return {"message": attacker.attack(req.scenario_id)}

@app.get("/report")
def get_report():
    return {
        "radar": {
            "贪利防御值": random.randint(60, 90),
            "恐慌阈值": random.randint(50, 80),
            "权威祛魅力": random.randint(40, 70),
            "情感独立性": random.randint(30, 60),
            "信息甄别力": random.randint(50, 85),
            "法治逻辑": random.randint(55, 75)
        }
    }

@app.post("/chat/companion")
async def chat_companion(req: StreamChatRequest):
    return StreamingResponse(stream_chat(req.messages, "companion"), media_type="text/plain")

@app.post("/chat/attacker")
async def chat_attacker(req: StreamChatRequest):
    return StreamingResponse(stream_chat(req.messages, "attacker"), media_type="text/plain")

@app.post("/chat/guardian")
async def chat_guardian(req: StreamChatRequest):
    return StreamingResponse(stream_chat(req.messages, "guardian"), media_type="text/plain")

@app.get("/api/training/{scenario_id}/question/{q_id}")
def get_question(scenario_id: str, q_id: int):
    conn = sqlite3.connect('zhidun.db')
    c = conn.cursor()
    c.execute('SELECT background_text, question_text, options, correct, explanation FROM questions WHERE scenario_id=? AND q_id=?', (scenario_id, q_id))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "background": row[0],
            "question": row[1],
            "options": json.loads(row[2]),
            "correct": row[3],
            "explanation": row[4]
        }
    return {"error": "题目不存在"}

@app.get("/api/training/{scenario_id}/info")
def get_scenario_info(scenario_id: str):
    conn = sqlite3.connect('zhidun.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM questions WHERE scenario_id=?', (scenario_id,))
    count = c.fetchone()[0]
    conn.close()
    return {"total": count}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
