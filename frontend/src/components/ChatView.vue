<template>
  <div class="chat-view" @pointerdown="onChatFirstInteract">
    <div class="chat-card">
      <header class="chat-card__head">
        <h2 class="chat-card__title">找小孙聊天</h2>
        <div class="chat-card__status-row">
          <span class="chat-card__online" title="服务可用"
            ><span class="chat-card__online-dot" aria-hidden="true" />在线</span
          >
          <span class="chat-card__mode">智能陪伴模式</span>
        </div>
        <div class="chat-card__divider" role="presentation" />
      </header>

      <div class="voice-panel">
        <div class="voice-actions">
          <button
            type="button"
            class="btn-phone"
            :class="{ active: voicePhoneActive }"
            @click="togglePhoneMode"
          >
            {{ voicePhoneActive ? '结束语音电话' : '语音电话' }}
          </button>
          <button
            type="button"
            class="btn-tts"
            :class="{ active: voiceOutputEnabled }"
            @click="toggleVoiceOutput"
          >
            语音播报：{{ voiceOutputEnabled ? '开' : '关' }}
          </button>
          <select
            v-model="dialectMode"
            class="btn-tts"
            aria-label="方言识别模式"
            @change="restartRecognitionForDialect"
          >
            <option v-for="item in DIALECT_PROFILES" :key="item.id" :value="item.id">
              {{ item.label }}
            </option>
          </select>
        </div>

        <div v-if="sttWarnText" class="stt-warn">
          {{ sttWarnText }}
        </div>
        <div v-else-if="sttUnsupported" class="stt-warn">
          当前浏览器不支持语音输入，请使用 Edge 或 Chrome，或改用文字输入。
        </div>
        <div v-else-if="sttNetworkWarn" class="stt-warn">
          语音识别需联网（Chrome/Edge 走云端）。若一直无反应，请检查网络、麦克风权限，或改用文字输入。
        </div>
      </div>

      <div class="chat-box" ref="chatBox">
        <div v-for="(msg, i) in messages" :key="msg.id" :class="['message', msg.type]">
          <div class="bubble">
            <template v-if="msg.type === 'ai' && !msg.text && isTyping && i === messages.length - 1">
              <strong class="ai-label">小花：</strong>
              <span class="typing-hint">小花正在回复…</span>
            </template>
            <template v-else-if="msg.type === 'ai'">
              <strong class="ai-label">小花：</strong>
              <span>{{ msg.text }}</span>
            </template>
            <template v-else>
              <span>{{ msg.text }}</span>
            </template>
          </div>
        </div>
      </div>

      <div v-if="showAlert" class="alert">
        警告！这是诈骗测试！请勿透露个人信息！
      </div>

      <div class="input-area">
        <input
          v-model="userInput"
          @keyup.enter="sendMessage()"
          type="text"
          autocomplete="off"
          placeholder="在这里输入您想说的话..."
        />
        <button type="button" class="input-area__send" @click="sendMessage()">发送</button>
      </div>

      <button type="button" class="btn-end-chat" @click="onEndChatReport">结束聊天</button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import { API_BASE } from '../apiBase.js'

const emit = defineEmits(['end-chat'])

function onEndChatReport() {
  emit('end-chat')
}

let msgIdSeq = 0
function nextMsgId() {
  return ++msgIdSeq
}

const messages = ref([
  {
    id: nextMsgId(),
    type: 'ai',
    text: '您好呀！我是您的数字小孙小花，今天您想和我聊聊天吗？最近身体怎么样？'
  }
])
const userInput = ref('')
const showAlert = ref(false)
const API_URL = API_BASE
const isTyping = ref(false)
/** 聊天请求超时（毫秒），避免卡住导致 isTyping 永远为 true、语音也无法再发 */
const CHAT_FETCH_MS = 120000
/** 略快于默认语速，接近日常对话（神经网络 TTS 用 audio.playbackRate，浏览器兜底用 utterance.rate） */
const TTS_CONVERSATION_RATE = 1.12
/** AI 流式回复中，攒到一句话就先播，减少“文字出来了但声音还没来”的等待 */
const STREAM_TTS_MIN_SENTENCE_CHARS = 10
const STREAM_TTS_MAX_SENTENCE_CHARS = 120

/** 板块一：问及身份/开发方/团队时统一口径，不调大模型（避免第三方模型自称公司名） */
const TEAM_IDENTITY_REPLY =
  '我是您的数字小孙小花，由"银龄智盾"团队倾情制作，愿为长辈多添一份安心❤'

function isTeamIdentityQuestion(raw) {
  const s = String(raw || '').replace(/\s/g, '')
  if (s.length > 96) return false
  if (/deepseek|深度求索/i.test(raw)) return true
  return /(你是谁|您是谁|你是什么人|你哪位|什么团队|哪个团队|哪家公司|什么公司|谁做的|谁开发|谁制作|谁研发|谁创造|谁做出来的|开发者是谁|作者是谁|你从哪来|从哪来|哪家单位|哪家做的|银龄智盾|谁做的你)/.test(
    s
  )
}

const chatBox = ref(null)

const voiceOutputEnabled = ref(true)
const voicePhoneActive = ref(false)
const isListening = ref(false)
const sttUnsupported = ref(false)
/** Chrome 等使用在线语音识别服务，断网或拦截会触发 network 错误 */
const sttNetworkWarn = ref(false)
const sttWarnText = ref('')
const DIALECT_PROFILES = [
  { id: 'mandarin', label: '普通话识别', hint: '普通话' },
  { id: 'shandong', label: '山东话识别', hint: '山东话' },
  { id: 'shanghai', label: '上海话识别', hint: '上海话' }
]
const dialectMode = ref('mandarin')

let recognition = null
let ttsBuffer = ''
let ttsPending = 0
let ttsChain = Promise.resolve()
/** 递增后，队列里旧的朗读任务会跳过，避免打断后仍播或两种 TTS 叠在一起 */
let ttsPlaySession = 0
/** 当前 <audio> 播放结束或被打断时的 resolver，供 cancelSpeech 结束挂起的 Promise */
let finishCurrentAudioPlayback = null
/** @type {HTMLAudioElement | null} */
let currentAudio = null
/** 朗读期间暂停麦克风，避免扬声器回声被识别成「用户说话」并误发消息 */
let suppressRecognitionRestart = false
let streamReplyTtsBuffer = ''
let speechCommitTimer = null
let lastVoiceSentText = ''
let lastVoiceSentAt = 0
let activeChatAbortController = null
let chatTurnSession = 0
const VOICE_INTERIM_COMMIT_MS = 650

function getSpeechRecognition() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

function getActiveDialectProfile() {
  return DIALECT_PROFILES.find((item) => item.id === dialectMode.value) || DIALECT_PROFILES[0]
}

function normalizeDialectTranscript(raw) {
  let s = String(raw || '').trim()
  if (!s) return s

  const commonRules = [
    [/为信/g, '微信'],
    [/微新/g, '微信'],
    [/转帐/g, '转账'],
    [/汇钱/g, '汇款'],
    [/打钱/g, '转账'],
    [/卡号/g, '银行卡号'],
    [/验证码/g, '验证码']
  ]
  const shandongRules = [
    [/俺们/g, '我们'],
    [/俺/g, '我'],
    [/恁们/g, '你们'],
    [/恁/g, '您'],
    [/咋办/g, '怎么办'],
    [/咋弄/g, '怎么处理'],
    [/咋回事/g, '怎么回事'],
    [/咋整/g, '怎么办'],
    [/咋/g, '怎么'],
    [/弄啥嘞/g, '做什么'],
    [/干啥/g, '做什么'],
    [/啥/g, '什么'],
    [/中不中/g, '行不行'],
    [/不中/g, '不行'],
    [/木有/g, '没有'],
    [/甭/g, '不用'],
    [/怪好/g, '挺好'],
    [/得劲/g, '舒服'],
    [/可不敢/g, '不敢']
  ]
  const shanghaiRules = [
    [/阿拉/g, '我们'],
    [/吾/g, '我'],
    [/侬/g, '你'],
    [/伊拉/g, '他们'],
    [/伊/g, '他'],
    [/伐晓得/g, '不知道'],
    [/勿晓得/g, '不知道'],
    [/伐要/g, '不要'],
    [/覅/g, '不要'],
    [/勿要/g, '不要'],
    [/勿/g, '不'],
    [/弗/g, '不'],
    [/伐/g, '吗'],
    [/啥体/g, '什么'],
    [/啥/g, '什么'],
    [/哪能办/g, '怎么办'],
    [/哪能/g, '怎么'],
    [/阿是/g, '是不是'],
    [/个么/g, '那么'],
    [/辰光/g, '时候'],
    [/老早/g, '以前'],
    [/一道/g, '一起'],
    [/老灵/g, '很好'],
    [/交关/g, '非常'],
    [/钞票/g, '钱']
  ]

  const rules =
    dialectMode.value === 'shandong'
      ? commonRules.concat(shandongRules)
      : dialectMode.value === 'shanghai'
        ? commonRules.concat(shanghaiRules)
        : commonRules

  for (const [pattern, replacement] of rules) {
    s = s.replace(pattern, replacement)
  }
  return s.replace(/\s+/g, ' ').trim()
}

function makeModelText(displayText, normalizedText) {
  if (dialectMode.value === 'mandarin') return displayText
  const dialectName = getActiveDialectProfile().hint
  const replyStyle =
    dialectMode.value === 'shandong'
      ? '本轮回复必须主要用山东话口吻，不要用普通话腔。优先用“俺、恁、咋、甭、怪好、木有、中不中、得劲”等常见说法，短句自然，长辈能听懂。'
      : '本轮回复必须主要用上海话口吻，不要用普通话腔。优先用“侬、阿拉、伐、勿、哪能、啥、老灵、交关、一道、辰光、覅”等常见说法，尽量避免“您、怎么样、什么、不要、很好”。'
  return `用户刚才用${dialectName}说：${displayText}\n普通话语义转写：${normalizedText}\n${replyStyle}\n不要解释自己正在使用方言，直接像日常聊天一样回答。`
}

function localizeAiReply(text) {
  let s = String(text || '')
  if (dialectMode.value === 'shanghai') {
    const rules = [
      [/您好/g, '侬好'],
      [/您/g, '侬'],
      [/你们/g, '侬伲'],
      [/你/g, '侬'],
      [/我们/g, '阿拉'],
      [/咱们/g, '阿拉'],
      [/他们/g, '伊拉'],
      [/怎么样/g, '哪能'],
      [/怎么/g, '哪能'],
      [/什么/g, '啥'],
      [/不要/g, '覅'],
      [/不用/g, '勿用'],
      [/不是/g, '伐是'],
      [/不知道/g, '伐晓得'],
      [/不/g, '伐'],
      [/非常/g, '交关'],
      [/很好/g, '老灵'],
      [/一起/g, '一道']
    ]
    for (const [pattern, replacement] of rules) s = s.replace(pattern, replacement)
  } else if (dialectMode.value === 'shandong') {
    const rules = [
      [/您好/g, '恁好'],
      [/您/g, '恁'],
      [/你们/g, '恁们'],
      [/你/g, '恁'],
      [/我们/g, '俺们'],
      [/我/g, '俺'],
      [/怎么/g, '咋'],
      [/怎么办/g, '咋办'],
      [/什么/g, '啥'],
      [/没有/g, '木有'],
      [/不要/g, '甭'],
      [/不用/g, '甭'],
      [/很好/g, '怪好'],
      [/舒服/g, '得劲'],
      [/行不行/g, '中不中']
    ]
    for (const [pattern, replacement] of rules) s = s.replace(pattern, replacement)
  }
  return s
}

function localCompanionFallbackReply() {
  const base =
    dialectMode.value === 'shanghai'
      ? '侬讲个我听到啦。阿拉慢慢来，伐着急；刚刚后台有点忙，侬再讲一句，我继续陪侬聊。'
      : dialectMode.value === 'shandong'
        ? '俺听着呢，恁先甭着急。刚才后台有点忙，恁再说一句，俺继续陪恁聊。'
        : '我在呢，您别着急。刚才后台有点忙，您再说一句，我继续陪您聊。'
  return base
}

function pickBestFinalTranscript(results, resultIndex, finalOnly = true) {
  const candidates = []
  for (let i = resultIndex; i < results.length; i++) {
    const r = results[i]
    if (finalOnly && !r.isFinal) continue
    if (!finalOnly && r.isFinal) continue
    for (let j = 0; j < r.length; j++) {
      const transcript = (r[j]?.transcript || '').trim()
      if (!transcript) continue
      const normalized = normalizeDialectTranscript(transcript)
      const changed = normalized !== transcript
      const confidence = typeof r[j]?.confidence === 'number' ? r[j].confidence : 0
      candidates.push({
        transcript,
        normalized,
        score: confidence + (r.isFinal ? 0.2 : 0) + (changed ? 0.15 : 0) + Math.min(normalized.length, 20) / 200
      })
    }
  }

  candidates.sort((a, b) => b.score - a.score)
  return candidates[0] || { transcript: '', normalized: '' }
}

function clearSpeechCommitTimer() {
  if (speechCommitTimer) {
    clearTimeout(speechCommitTimer)
    speechCommitTimer = null
  }
}

function getLastAiText() {
  const msg = [...messages.value].reverse().find((m) => m.type === 'ai' && m.text)
  return String(msg?.text || '')
}

function isLikelySpeakerEcho(text) {
  const t = String(text || '').replace(/\s/g, '')
  if (t.length < 4) return false
  const lastAi = stripParentheticals(getLastAiText()).replace(/\s/g, '')
  if (!lastAi) return false
  return lastAi.includes(t) || t.includes(lastAi.slice(0, Math.min(16, lastAi.length)))
}

function interruptCurrentTurnForVoice() {
  clearSpeechCommitTimer()
  chatTurnSession++
  if (activeChatAbortController) {
    activeChatAbortController.abort()
    activeChatAbortController = null
  }
  cancelSpeech()
  ttsBuffer = ''
  resetStreamReplySpeech()
  isTyping.value = false
  const last = messages.value[messages.value.length - 1]
  if (last && last.type === 'ai' && !String(last.text || '').trim()) {
    messages.value.pop()
  }
}

function commitVoiceTranscript(transcript, normalized) {
  clearSpeechCommitTimer()
  const text = String(transcript || '').trim()
  if (!text || isVoiceInputTooShort(text)) return

  const now = Date.now()
  const normalizedText = normalizeDialectTranscript(normalized || text)
  const lastNormalizedText = normalizeDialectTranscript(lastVoiceSentText)
  if (
    (text === lastVoiceSentText || (normalizedText && normalizedText === lastNormalizedText)) &&
    now - lastVoiceSentAt < 3000
  ) {
    return
  }

  const phoneBusy =
    voicePhoneActive.value && (isTyping.value || ttsPending > 0 || currentAudio || window.speechSynthesis.speaking)
  if (phoneBusy && isLikelySpeakerEcho(text)) return
  if (phoneBusy) {
    interruptCurrentTurnForVoice()
  } else if (isTyping.value || suppressRecognitionRestart || ttsPending > 0 || currentAudio || window.speechSynthesis.speaking) {
    return
  }

  lastVoiceSentText = text
  lastVoiceSentAt = now
  sendMessage(text, normalizedText)
}

function scheduleVoiceTranscript(transcript, normalized) {
  const text = String(transcript || '').trim()
  if (!text || isVoiceInputTooShort(text)) return
  clearSpeechCommitTimer()
  speechCommitTimer = setTimeout(() => {
    commitVoiceTranscript(text, normalized || normalizeDialectTranscript(text))
  }, VOICE_INTERIM_COMMIT_MS)
}

/** 语音输入过短：允许单个汉字，过滤单字母杂音；键盘输入仍可在 sendMessage 里用 trim 判断 */
function isVoiceInputTooShort(t) {
  const s = String(t || '').trim()
  if (s.length === 0) return true
  if (s.length >= 2) return false
  return !/[\u3000-\u9fff\u3400-\u4dbf\uf900-\ufaff]/.test(s)
}

/** recognition.start() 在 stop 后过快调用会抛 InvalidStateError，做短暂重试 */
function safeRecognitionStart() {
  if (!recognition || !voicePhoneActive.value) return
  const attempt = (n) => {
    if (!recognition || !voicePhoneActive.value) return
    try {
      recognition.start()
    } catch {
      if (n < 5) {
        setTimeout(() => attempt(n + 1), 120 * n)
      } else {
        isListening.value = false
      }
    }
  }
  attempt(1)
}

function pickZhVoiceFallback() {
  const voices = window.speechSynthesis.getVoices()
  return (
    voices.find((v) => v.lang && v.lang.toLowerCase().includes('zh')) ||
    voices.find((v) => v.name && /chinese|中文|mandarin/i.test(v.name)) ||
    voices[0] ||
    null
  )
}

/** 去掉旁白括号，避免朗读与展示动作说明 */
function stripParentheticals(raw) {
  if (!raw) return ''
  let s = String(raw)
  for (let n = 0; n < 6; n++) {
    const next = s
      .replace(/（[^）]*）/g, ' ')
      .replace(/\([^)]*\)/g, ' ')
      .replace(/【[^】]*】/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
    if (next === s) break
    s = next
  }
  return s
}

/** 首条 AI 欢迎语（strip 后），用于预取 TTS 与整段播放，避免拆句多请求 */
function getWelcomeSpeakText() {
  const m = messages.value[0]
  if (!m || m.type !== 'ai' || !m.text) return ''
  return stripParentheticals(String(m.text)).trim()
}

/** 进入板块一时后台预取欢迎语音频，首次点击/触摸时多半已就绪，减少「等半天才出声」 */
let welcomeTtsPrefetchedBlob = null
let welcomeTtsPrefetchPromise = null

function prefetchWelcomeTts() {
  if (!voiceOutputEnabled.value) return
  const text = getWelcomeSpeakText()
  if (!text) return
  welcomeTtsPrefetchPromise = fetch(`${API_URL}/api/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, dialect: dialectMode.value })
  })
    .then((res) => {
      if (!res.ok) throw new Error('tts http')
      return res.blob()
    })
    .then((blob) => {
      if (blob && blob.size >= 16) welcomeTtsPrefetchedBlob = blob
    })
    .catch(() => {
      welcomeTtsPrefetchedBlob = null
    })
}

function cancelSpeech() {
  ttsPlaySession++
  window.speechSynthesis.cancel()
  ttsPending = 0
  ttsChain = Promise.resolve()
  if (currentAudio) {
    currentAudio.pause()
    currentAudio.src = ''
    currentAudio = null
  }
  if (finishCurrentAudioPlayback) {
    const done = finishCurrentAudioPlayback
    finishCurrentAudioPlayback = null
    done()
  }
  suppressRecognitionRestart = false
  if (voicePhoneActive.value && recognition) {
    setTimeout(() => resumeRecognitionAfterTts(), 120)
  }
}

function playBrowserTts(text) {
  return new Promise((resolve) => {
    const u = new SpeechSynthesisUtterance(text.trim())
    u.lang = 'zh-CN'
    u.rate = TTS_CONVERSATION_RATE
    u.pitch = 1.02
    const v = pickZhVoiceFallback()
    if (v) u.voice = v
    u.onend = () => resolve()
    u.onerror = () => resolve()
    window.speechSynthesis.speak(u)
  })
}

/**
 * 优先播放后端神经网络 TTS（Edge/CosyVoice，较自然）。
 * 仅在接口失败或空音频时再走浏览器 speech（较机械），避免两种声音叠播。
 */
async function prepareEdgeTtsBlob(text, sessionAtSchedule) {
  const t = (text || '').trim()
  if (!t) return null

  let blob = null
  const welcomeSpeak = getWelcomeSpeakText()
  if (welcomeSpeak && t === welcomeSpeak) {
    if (welcomeTtsPrefetchedBlob) {
      blob = welcomeTtsPrefetchedBlob
      welcomeTtsPrefetchedBlob = null
    } else if (welcomeTtsPrefetchPromise) {
      try {
        await welcomeTtsPrefetchPromise
        if (sessionAtSchedule !== ttsPlaySession) return null
        if (welcomeTtsPrefetchedBlob) {
          blob = welcomeTtsPrefetchedBlob
          welcomeTtsPrefetchedBlob = null
        }
      } catch {
        /* 走下方请求 */
      }
    }
  }

  if (!blob) {
    const res = await fetch(`${API_URL}/api/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: t, dialect: dialectMode.value })
    })
    if (!res.ok) throw new Error('tts http')
    if (sessionAtSchedule !== ttsPlaySession) return null

    blob = await res.blob()
    if (!blob || blob.size < 16) throw new Error('tts empty')
    if (sessionAtSchedule !== ttsPlaySession) return null
  }

  return blob
}

async function playPreparedTtsBlob(blob, sessionAtSchedule) {
  if (!blob || sessionAtSchedule !== ttsPlaySession) return
  const url = URL.createObjectURL(blob)
  const a = new Audio(url)
  a.playbackRate = TTS_CONVERSATION_RATE
  currentAudio = a

  try {
    await new Promise((resolve, reject) => {
      let settled = false
      const finish = () => {
        if (settled) return
        settled = true
        finishCurrentAudioPlayback = null
        URL.revokeObjectURL(url)
        if (currentAudio === a) currentAudio = null
        resolve()
      }
      finishCurrentAudioPlayback = finish

      a.onended = finish
      a.onerror = () => {
        finishCurrentAudioPlayback = null
        URL.revokeObjectURL(url)
        if (currentAudio === a) currentAudio = null
        if (!settled) {
          settled = true
          reject(new Error('audio'))
        }
      }

      const p = a.play()
      if (p !== undefined) {
        p.catch((err) => {
          a.pause()
          a.src = ''
          URL.revokeObjectURL(url)
          if (currentAudio === a) currentAudio = null
          finishCurrentAudioPlayback = null
          if (!settled) {
            settled = true
            reject(err)
          }
        })
      }
    })
  } catch (e) {
    finishCurrentAudioPlayback = null
    throw e
  }
}

async function playEdgeTts(text, sessionAtSchedule) {
  const blob = await prepareEdgeTtsBlob(text, sessionAtSchedule)
  await playPreparedTtsBlob(blob, sessionAtSchedule)
}

function speakLine(text) {
  const line = localizeAiReply(stripParentheticals(text))
  if (!voiceOutputEnabled.value || !line.trim()) return

  const sessionAtSchedule = ttsPlaySession
  ttsPending++
  pauseRecognitionForTts()
  const preparedAudio = prepareEdgeTtsBlob(line.trim(), sessionAtSchedule)
  preparedAudio.catch(() => {})

  ttsChain = ttsChain.then(async () => {
    if (sessionAtSchedule !== ttsPlaySession) {
      ttsPending = Math.max(0, ttsPending - 1)
      if (ttsPending === 0) resumeRecognitionAfterTts()
      return
    }

    let usedBrowser = false
    try {
      await playPreparedTtsBlob(await preparedAudio, sessionAtSchedule)
    } catch (e) {
      if (sessionAtSchedule !== ttsPlaySession) {
        ttsPending = Math.max(0, ttsPending - 1)
        if (ttsPending === 0) resumeRecognitionAfterTts()
        return
      }
      // 接口失败或音频无法播放时再用浏览器兜底；先确保神经网络侧已静音，避免叠音
      window.speechSynthesis.cancel()
      await playBrowserTts(line.trim())
      usedBrowser = true
    }

    if (sessionAtSchedule !== ttsPlaySession) {
      if (usedBrowser) window.speechSynthesis.cancel()
      ttsPending = Math.max(0, ttsPending - 1)
      if (ttsPending === 0) resumeRecognitionAfterTts()
      return
    }

    ttsPending = Math.max(0, ttsPending - 1)
    if (ttsPending === 0) resumeRecognitionAfterTts()
  })
}

function pauseRecognitionForTts() {
  if (!recognition || !voicePhoneActive.value) return
  // 电话模式保持常开麦：用户可以直接插话，识别到人声后会打断当前播报。
  suppressRecognitionRestart = false
  isListening.value = true
}

function resumeRecognitionAfterTts() {
  // 不在此处判断 isTyping：AI 生成期间也应保持麦克风就绪，是否发送由 onresult 里统一拦截
  if (!recognition || !voicePhoneActive.value) return
  suppressRecognitionRestart = false
  setTimeout(() => {
    if (!recognition || !voicePhoneActive.value) return
    safeRecognitionStart()
  }, 320)
}

function resetStreamReplySpeech() {
  streamReplyTtsBuffer = ''
}

function queueStreamReplySpeech(chunk, force = false) {
  if (!voiceOutputEnabled.value) return
  streamReplyTtsBuffer += chunk || ''

  while (streamReplyTtsBuffer.trim()) {
    const trimmedStart = streamReplyTtsBuffer.search(/\S/)
    if (trimmedStart > 0) streamReplyTtsBuffer = streamReplyTtsBuffer.slice(trimmedStart)

    const sentenceMatch = streamReplyTtsBuffer.match(
      new RegExp(`^[\\s\\S]{${STREAM_TTS_MIN_SENTENCE_CHARS},${STREAM_TTS_MAX_SENTENCE_CHARS}}?[。！？.!?\\n]`)
    )
    if (sentenceMatch) {
      const part = sentenceMatch[0]
      streamReplyTtsBuffer = streamReplyTtsBuffer.slice(part.length)
      speakLine(part)
      continue
    }

    if (force) {
      const tail = localizeAiReply(streamReplyTtsBuffer.trim())
      streamReplyTtsBuffer = ''
      if (tail) speakLine(tail)
    }
    break
  }
}

/** DeepSeek 完整回复到达后再分段朗读（不在流式过程中抢先念） */
function speakFullReply(fullText) {
  if (!voiceOutputEnabled.value) return
  ttsBuffer = stripParentheticals(fullText || '').trim()
  if (!ttsBuffer) return

  // 仅首条欢迎语：整段一次合成/播放，与 prefetch 一致，且少一次网络往返
  if (messages.value.length === 1 && ttsBuffer === getWelcomeSpeakText()) {
    speakLine(ttsBuffer)
    ttsBuffer = ''
    return
  }

  // 中等长度以内整段一次 TTS，减少句间等待（长文仍按句切，避免单次合成过久）
  if (ttsBuffer.length <= 800) {
    speakLine(ttsBuffer)
    ttsBuffer = ''
    return
  }

  while (ttsBuffer.length > 0) {
    const m = ttsBuffer.match(/^[\s\S]{1,200}?[。！？.!?\n]/)
    if (m) {
      speakLine(m[0])
      ttsBuffer = ttsBuffer.slice(m[0].length)
      continue
    }
    if (ttsBuffer.length >= 72) {
      const part = ttsBuffer.slice(0, 48)
      ttsBuffer = ttsBuffer.slice(48)
      speakLine(part + '…')
      continue
    }
    break
  }
  if (ttsBuffer.trim()) {
    speakLine(ttsBuffer.trim())
    ttsBuffer = ''
  }
}

function toggleVoiceOutput() {
  const wasOff = !voiceOutputEnabled.value
  voiceOutputEnabled.value = !voiceOutputEnabled.value
  if (!voiceOutputEnabled.value) {
    cancelSpeech()
    ttsBuffer = ''
    resetStreamReplySpeech()
    return
  }
  // 从关→开：补预取欢迎语（若进页时未预取）
  if (wasOff) prefetchWelcomeTts()
  // 从关→开：用户点击即算手势，浏览器才允许出声；立刻朗读当前最后一条小孙的话
  if (wasOff) {
    ttsBuffer = ''
    const lastAi = [...messages.value]
      .reverse()
      .find((m) => m.type === 'ai' && m.text && String(m.text).trim())
    if (lastAi) speakFullReply(lastAi.text)
  }
}

/**
 * 欢迎语是否已触发（避免与首屏点击重复播）。
 * 从首页进入时由 tryWelcomeOnEnter 尽快播放；若浏览器仍拦截有声播放，可依赖首次点空白区兜底。
 */
let didUnlockWelcome = false

/** 供 App 在「进入板块一」后立即调用：利用刚发生的点击手势，尽量无需再点一下就能播欢迎语 */
function tryWelcomeOnEnter() {
  if (didUnlockWelcome) return
  if (!voiceOutputEnabled.value) return
  if (messages.value.length !== 1) return
  const msg = messages.value[0].text
  if (!msg || !String(msg).trim()) return
  didUnlockWelcome = true
  ttsBuffer = ''
  resetStreamReplySpeech()
  speakFullReply(msg)
}

defineExpose({ tryWelcomeOnEnter })

function onChatFirstInteract(ev) {
  const t = ev.target
  if (t && t.closest && t.closest('button')) return
  if (didUnlockWelcome) return
  // 已在播欢迎或队列中：记为已处理，避免叠播
  if (ttsPending > 0 || currentAudio || window.speechSynthesis.speaking) {
    didUnlockWelcome = true
    return
  }
  if (messages.value.length !== 1) return
  didUnlockWelcome = true
  if (!voiceOutputEnabled.value) return
  const msg = messages.value[0].text
  if (msg && String(msg).trim()) {
    ttsBuffer = ''
    resetStreamReplySpeech()
    speakFullReply(msg)
  }
}

function setupRecognition() {
  const SR = getSpeechRecognition()
  if (!SR) {
    sttUnsupported.value = true
    return
  }
  sttUnsupported.value = false
  recognition = new SR()
  recognition.lang = 'zh-CN'
  recognition.continuous = false
  recognition.maxAlternatives = dialectMode.value === 'mandarin' ? 1 : 5
  // 开启 interim 有利于中文在部分浏览器中更快产出 isFinal 结果
  recognition.interimResults = true

  recognition.onstart = () => {
    isListening.value = true
    sttWarnText.value = ''
    sttNetworkWarn.value = false
  }

  recognition.onresult = (ev) => {
    const finalPicked = pickBestFinalTranscript(ev.results, ev.resultIndex, true)
    const finalText = finalPicked.transcript.trim()
    if (finalText && !isVoiceInputTooShort(finalText)) {
      commitVoiceTranscript(finalText, finalPicked.normalized)
      return
    }

    const interimPicked = pickBestFinalTranscript(ev.results, ev.resultIndex, false)
    const interimText = interimPicked.transcript.trim()
    if (interimText && !isVoiceInputTooShort(interimText)) {
      scheduleVoiceTranscript(interimText, interimPicked.normalized)
    }
  }

  recognition.onerror = (ev) => {
    if (ev.error === 'aborted') return
    if (ev.error === 'no-speech') {
      sttWarnText.value = '还没听清您说的话，请靠近麦克风再说一遍。'
      return
    }
    if (ev.error === 'not-allowed') {
      sttUnsupported.value = true
      sttWarnText.value = '麦克风权限被拒绝了，请在浏览器地址栏允许麦克风后再打开语音电话。'
    }
    if (ev.error === 'network') {
      sttNetworkWarn.value = true
      sttWarnText.value = '语音识别服务暂时连不上，请检查网络，或先改用文字输入。'
    }
    if (ev.error === 'audio-capture') {
      sttWarnText.value = '没有检测到可用麦克风，请检查麦克风设备。'
    }
    isListening.value = false
  }

  recognition.onend = () => {
    if (!voicePhoneActive.value) {
      isListening.value = false
      return
    }
    if (suppressRecognitionRestart) {
      isListening.value = false
      return
    }
    setTimeout(() => {
      if (!voicePhoneActive.value || !recognition) return
      safeRecognitionStart()
    }, 240)
  }
}

async function requestMicrophoneAccess() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    return true
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    stream.getTracks().forEach((track) => track.stop())
    sttWarnText.value = ''
    return true
  } catch (e) {
    const name = e && e.name
    if (name === 'NotAllowedError' || name === 'SecurityError') {
      sttWarnText.value = '麦克风权限被拒绝了，请在浏览器地址栏允许麦克风后再打开语音电话。'
    } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
      sttWarnText.value = '没有检测到可用麦克风，请检查麦克风设备。'
    } else {
      sttWarnText.value = '麦克风启动失败，请检查浏览器权限和设备后重试。'
    }
    return false
  }
}

async function togglePhoneMode() {
  if (!getSpeechRecognition()) {
    sttUnsupported.value = true
    sttWarnText.value = '当前浏览器不支持语音输入，请使用 Edge 或 Chrome，或改用文字输入。'
    return
  }

  const nextActive = !voicePhoneActive.value
  voicePhoneActive.value = nextActive
  if (nextActive) {
    clearSpeechCommitTimer()
    suppressRecognitionRestart = false
    sttNetworkWarn.value = false
    sttWarnText.value = ''
    const canUseMic = await requestMicrophoneAccess()
    if (!canUseMic) {
      voicePhoneActive.value = false
      isListening.value = false
      return
    }
    cancelSpeech()
    ttsBuffer = ''
    resetStreamReplySpeech()
    if (recognition) {
      try {
        recognition.stop()
      } catch {
        /* ignore */
      }
      recognition = null
    }
    setupRecognition()
    if (!recognition) {
      voicePhoneActive.value = false
      return
    }
    safeRecognitionStart()
  } else {
    clearSpeechCommitTimer()
    suppressRecognitionRestart = false
    sttNetworkWarn.value = false
    sttWarnText.value = ''
    if (recognition) {
      try {
        recognition.stop()
      } catch {
        /* ignore */
      }
      recognition = null
    }
    isListening.value = false
  }
}

function restartRecognitionForDialect() {
  cancelSpeech()
  ttsBuffer = ''
  resetStreamReplySpeech()
  welcomeTtsPrefetchedBlob = null
  welcomeTtsPrefetchPromise = null
  prefetchWelcomeTts()
  if (!voicePhoneActive.value) return
  clearSpeechCommitTimer()
  sttNetworkWarn.value = false
  sttWarnText.value = ''
  if (recognition) {
    try {
      recognition.stop()
    } catch {
      /* ignore */
    }
    recognition = null
  }
  setupRecognition()
  if (recognition) safeRecognitionStart()
}

async function sendMessage(forcedText, forcedNormalizedText) {
  return sendMessageWithDialect(forcedText, forcedNormalizedText)
}

async function sendMessageWithDialect(forcedText, forcedNormalizedText) {
  clearSpeechCommitTimer()
  const text = typeof forcedText === 'string' ? forcedText : userInput.value
  const trimmed = text.trim()
  if (!trimmed || isTyping.value) return
  if (typeof forcedText === 'string' && isVoiceInputTooShort(trimmed)) return
  const normalizedText = normalizeDialectTranscript(forcedNormalizedText || trimmed)
  const modelText = makeModelText(trimmed, normalizedText)

  if (typeof forcedText !== 'string') userInput.value = ''

  const turnSession = ++chatTurnSession
  cancelSpeech()
  ttsBuffer = ''
  resetStreamReplySpeech()

  messages.value.push({ id: nextMsgId(), type: 'user', text: trimmed, modelText })
  isTyping.value = true
  const aiMsg = { id: nextMsgId(), type: 'ai', text: '' }
  messages.value.push(aiMsg)

  if (isTeamIdentityQuestion(normalizedText)) {
    await nextTick()
    aiMsg.text = TEAM_IDENTITY_REPLY
    await nextTick()
    speakFullReply(aiMsg.text)
    isTyping.value = false
    await nextTick()
    chatBox.value?.scrollTo(0, chatBox.value.scrollHeight)
    return
  }

  const controller = new AbortController()
  activeChatAbortController = controller
  const killTimer = setTimeout(() => controller.abort(), CHAT_FETCH_MS)

  try {
    const chatHistory = messages.value
      .slice(0, -1)
      .map((m) => ({ role: m.type === 'user' ? 'user' : 'assistant', content: m.modelText || m.text }))

    const response = await fetch(`${API_URL}/chat/companion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: chatHistory, mode: 'companion' }),
      signal: controller.signal
    })

    if (turnSession !== chatTurnSession) return
    if (!response.ok || !response.body) {
      throw new Error(`http ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')

    while (true) {
      const { done, value } = await reader.read()
      if (turnSession !== chatTurnSession) return
      if (done) {
        const tail = decoder.decode(new Uint8Array(), { stream: false })
        if (tail) {
          aiMsg.text += tail
          await nextTick()
        }
        break
      }
      const chunk = decoder.decode(value, { stream: true })
      aiMsg.text += chunk
      queueStreamReplySpeech(chunk, false)
      await nextTick()
      chatBox.value?.scrollTo(0, chatBox.value.scrollHeight)
    }
    if (turnSession !== chatTurnSession) return
    await nextTick()
    aiMsg.text = localizeAiReply(stripParentheticals(aiMsg.text))
    await nextTick()
    queueStreamReplySpeech('', true)
  } catch (e) {
    if (turnSession !== chatTurnSession) return
    resetStreamReplySpeech()
    const name = e && e.name
    if (name === 'AbortError') {
      aiMsg.text =
        dialectMode.value === 'shanghai'
          ? '后台等得有点久，阿拉先伐急。侬再讲一句，我继续听侬讲。'
          : dialectMode.value === 'shandong'
            ? '后台等得有点久，咱先甭急。恁再说一句，俺继续听着。'
            : '后台等得有点久，咱们先不急。您再说一句，我继续听着。'
    } else {
      aiMsg.text = localCompanionFallbackReply()
    }
    speakFullReply(aiMsg.text)
  } finally {
    clearTimeout(killTimer)
    if (activeChatAbortController === controller) activeChatAbortController = null
    if (turnSession === chatTurnSession) isTyping.value = false
    await nextTick()
    chatBox.value?.scrollTo(0, chatBox.value.scrollHeight)
  }
}

onMounted(() => {
  window.speechSynthesis.getVoices()
  prefetchWelcomeTts()
  // 非经首页按钮进入（如日后深链）时仍尝试自动欢迎；若与 App.goChat 重复，didUnlockWelcome 会挡掉第二次
  nextTick(() => tryWelcomeOnEnter())
})

onUnmounted(() => {
  welcomeTtsPrefetchedBlob = null
  welcomeTtsPrefetchPromise = null
  clearSpeechCommitTimer()
  resetStreamReplySpeech()
  cancelSpeech()
  if (recognition) {
    try {
      recognition.stop()
    } catch {
      /* ignore */
    }
  }
})
</script>

<style scoped>
/* 参考稿：白卡片 + 浅灰消息区 + 浅蓝 AI 气泡 + 蓝发送 + 绿在线 + 红底结束报告 */
.chat-card {
  width: 100%;
  max-width: min(780px, 100%);
  margin: 0 auto;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(15, 23, 42, 0.08), 0 2px 8px rgba(15, 23, 42, 0.04);
  border: none;
  padding: clamp(16px, 2.6vw, 24px);
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
}

.chat-card__head {
  flex-shrink: 0;
  margin-bottom: 12px;
}

.chat-card__title {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: clamp(26px, 3.2vw, 34px);
  font-weight: 700;
  color: #1e293b;
  letter-spacing: 0.06em;
  margin: 0 0 10px;
}

.chat-card__status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: clamp(20px, 2.2vw, 23px);
  padding: 0 2px;
}

.chat-card__online {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #16a34a;
  font-weight: 600;
}

.chat-card__online-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.25);
}

.chat-card__mode {
  color: #94a3b8;
  font-weight: 500;
}

.chat-card__divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, #e2e8f0 12%, #e2e8f0 88%, transparent);
  margin-top: 12px;
}

/* 图二：浅黄底操作区（仅语音按钮与状态，无说明文案） */
.voice-panel {
  flex-shrink: 0;
  margin-bottom: 12px;
  padding: 12px;
  background: #fdf6ec;
  border: 1px solid #f5e6c8;
  border-radius: 12px;
}

.voice-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.btn-phone,
.btn-tts {
  flex: 1;
  min-width: 140px;
  min-height: 52px;
  padding: 12px 16px;
  font-size: clamp(21px, 2.2vw, 24px);
  font-weight: 600;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  cursor: pointer;
  transition: transform 0.12s, box-shadow 0.2s, background 0.2s;
  background: #fff;
  color: #334155;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.btn-phone:hover,
.btn-tts:hover {
  border-color: #94a3b8;
  background: #f8fafc;
}

.btn-phone.active {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  border-color: #60a5fa;
  color: #1e40af;
}

.btn-tts.active {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border-color: #f59e0b;
  color: #92400e;
}

.voice-panel .listening {
  margin-top: 8px;
  margin-bottom: 0;
}

.listening {
  flex-shrink: 0;
  font-size: clamp(19px, 2vw, 22px);
  color: #15803d;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  background: #22c55e;
  border-radius: 50%;
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

.voice-panel .stt-warn {
  margin-top: 8px;
  margin-bottom: 0;
}

.stt-warn {
  flex-shrink: 0;
  font-size: clamp(17px, 1.8vw, 19px);
  color: #b45309;
  padding: 10px 12px;
  background: #fff;
  border-radius: 10px;
  border: 1px solid #fde68a;
}

.chat-view {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: min(1180px, 100%);
  margin: 0 auto;
  padding: 0;
  align-items: center;
}

.chat-box {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px 16px 20px;
  box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.8);
}

.message {
  margin: 12px 0;
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.ai {
  justify-content: flex-start;
}

.bubble {
  padding: clamp(12px, 1.7vw, 16px) clamp(16px, 2vw, 20px);
  font-size: clamp(19px, 2vw, 24px);
  border-radius: 14px;
  max-width: min(85%, 680px);
  min-height: 1.2em;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
  position: relative;
  line-height: 1.6;
}

.ai-label {
  color: #1d39c4;
  font-weight: 700;
  margin-right: 2px;
}

.typing-hint {
  color: #64748b;
  font-style: italic;
}

.message.user .bubble {
  background: #fff;
  border: 1px solid #cbd5e1;
  color: #0f172a;
}

.message.user .bubble::after {
  content: '';
  position: absolute;
  right: -7px;
  top: 12px;
  width: 0;
  height: 0;
  border: 7px solid transparent;
  border-left-color: #fff;
  border-right: 0;
}

.message.ai .bubble {
  background: #e6f4ff;
  border: 1px solid #b3d8ff;
  color: #0f172a;
}

.message.ai .bubble::before {
  content: '';
  position: absolute;
  left: -7px;
  top: 12px;
  width: 0;
  height: 0;
  border: 7px solid transparent;
  border-right-color: #e6f4ff;
  border-left: 0;
}

.alert {
  flex-shrink: 0;
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
  color: #fff;
  padding: 14px;
  font-size: clamp(21px, 2.2vw, 24px);
  font-weight: 600;
  text-align: center;
  border: none;
  border-radius: 10px;
  margin: 8px 0 0;
  animation: shake 0.5s;
  box-shadow: 0 6px 24px rgba(185, 28, 28, 0.35);
}

@keyframes shake {
  0%,
  100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-8px);
  }
  75% {
    transform: translateX(8px);
  }
}

.input-area {
  flex-shrink: 0;
  display: flex;
  gap: 10px;
  margin-top: 12px;
  align-items: stretch;
}

.input-area input {
  flex: 1;
  min-height: 52px;
  padding: 14px 18px;
  font-size: clamp(21px, 2.2vw, 24px);
  border: 2px solid #cbd5e1;
  border-radius: 12px;
  background: #fff;
  color: #0f172a;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.input-area input::placeholder {
  color: #94a3b8;
}

.input-area input:focus {
  outline: none;
  border-color: #409eff;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.22);
}

.input-area__send {
  padding: 14px 24px;
  min-height: 52px;
  font-size: clamp(21px, 2.2vw, 24px);
  font-weight: 600;
  background: #409eff;
  color: #fff;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.38);
  white-space: nowrap;
}

.input-area__send:hover {
  background: #66b1ff;
}

.input-area__send:active {
  transform: scale(0.98);
}

.btn-end-chat {
  flex-shrink: 0;
  width: 100%;
  margin-top: 14px;
  padding: 16px 20px;
  min-height: 56px;
  font-size: clamp(20px, 2.15vw, 24px);
  font-weight: 700;
  letter-spacing: 0.06em;
  color: #fff;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  background: #f56c6c;
  box-shadow: 0 6px 18px rgba(245, 108, 108, 0.4);
  transition: transform 0.12s, filter 0.15s;
}

.btn-end-chat:hover {
  filter: brightness(1.05);
}

.btn-end-chat:active {
  transform: scale(0.99);
}
</style>
