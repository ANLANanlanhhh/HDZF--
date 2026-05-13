"""
智盾后端可选接入 CosyVoice（Alibaba 开源）本地/内网服务。

CosyVoice 官方 FastAPI：`runtime/python/fastapi/server.py`
返回流式 int16 PCM，本模块拼成 WAV 供浏览器 <Audio> 播放。

环境变量：
- COSYVOICE_URL：例如 http://127.0.0.1:50000（不设则仅用 edge-tts）
- COSYVOICE_SPK_ID：默认中文女，需与所用预训练模型内置说话人一致
- COSYVOICE_SPK_ID_SHANDONG：山东话模式 speaker（可选，未设则用 COSYVOICE_SPK_ID）
- COSYVOICE_SPK_ID_SHANGHAI：上海话模式 speaker（可选，未设则用 COSYVOICE_SPK_ID）
- COSYVOICE_SAMPLE_RATE：默认 22050；若听感快慢不对，请改为模型 cosyvoice.yaml 中的 sample_rate（常见还有 24000）
- COSYVOICE_TIMEOUT：请求超时秒数，默认 120
"""

from __future__ import annotations

import io
import logging
import os
import wave
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


def pcm_s16le_to_wav(pcm: bytes, sample_rate: int, channels: int = 1) -> bytes:
    """将 CosyVoice FastAPI 返回的原始 s16le PCM 封装为 WAV。"""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def cosyvoice_enabled() -> bool:
    return bool((os.getenv("COSYVOICE_URL") or "").strip())


def cosyvoice_speaker_for_dialect(dialect: str = "mandarin") -> str:
    dialect_key = (dialect or "mandarin").strip().lower()
    env_key = {
        "shandong": "COSYVOICE_SPK_ID_SHANDONG",
        "shanghai": "COSYVOICE_SPK_ID_SHANGHAI",
    }.get(dialect_key)
    if env_key:
        speaker = (os.getenv(env_key) or "").strip()
        if speaker:
            return speaker
    return os.getenv("COSYVOICE_SPK_ID", "中文女")


async def cosyvoice_sft_to_wav(text: str, dialect: str = "mandarin") -> Optional[bytes]:
    """
    调用 CosyVoice /inference_sft，成功返回 WAV 字节；失败返回 None（由上层回退 edge-tts）。
    """
    base = (os.getenv("COSYVOICE_URL") or "").strip().rstrip("/")
    if not base:
        return None

    spk = cosyvoice_speaker_for_dialect(dialect)
    try:
        sr = int(os.getenv("COSYVOICE_SAMPLE_RATE", "22050"))
    except ValueError:
        sr = 22050
    try:
        timeout = float(os.getenv("COSYVOICE_TIMEOUT", "120"))
    except ValueError:
        timeout = 120.0

    t = (text or "").strip()
    if not t:
        return None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                f"{base}/inference_sft",
                data={"tts_text": t, "spk_id": spk},
            )
            r.raise_for_status()
            pcm = r.content
        if not pcm or len(pcm) < 4:
            logger.warning("CosyVoice 返回空音频")
            return None
        return pcm_s16le_to_wav(pcm, sr)
    except httpx.HTTPError as e:
        logger.warning("CosyVoice HTTP 失败，将回退 edge-tts: %s", e)
        return None
    except Exception as e:
        logger.warning("CosyVoice 合成异常，将回退 edge-tts: %s", e)
        return None


def tts_engine_label() -> str:
    return "cosyvoice" if cosyvoice_enabled() else "edge-tts"
