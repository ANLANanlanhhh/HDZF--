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
        </div>

        <div v-if="voicePhoneActive && isListening" class="listening">
          <span class="dot" />正在听…说完一句会自动发送。
        </div>
        <div v-if="sttUnsupported" class="stt-warn">
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

function getSpeechRecognition() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
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
      isListening.value = true
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
    body: JSON.stringify({ text })
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
async function playEdgeTts(text, sessionAtSchedule) {
  const t = (text || '').trim()
  if (!t) return

  let blob = null
  const welcomeSpeak = getWelcomeSpeakText()
  if (welcomeSpeak && t === welcomeSpeak) {
    if (welcomeTtsPrefetchedBlob) {
      blob = welcomeTtsPrefetchedBlob
      welcomeTtsPrefetchedBlob = null
    } else if (welcomeTtsPrefetchPromise) {
      try {
        await welcomeTtsPrefetchPromise
        if (sessionAtSchedule !== ttsPlaySession) return
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
      body: JSON.stringify({ text: t })
    })
    if (!res.ok) throw new Error('tts http')
    if (sessionAtSchedule !== ttsPlaySession) return

    blob = await res.blob()
    if (!blob || blob.size < 16) throw new Error('tts empty')
    if (sessionAtSchedule !== ttsPlaySession) return
  }

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

function speakLine(text) {
  const line = stripParentheticals(text)
  if (!voiceOutputEnabled.value || !line.trim()) return

  const sessionAtSchedule = ttsPlaySession
  ttsPending++
  pauseRecognitionForTts()

  ttsChain = ttsChain.then(async () => {
    if (sessionAtSchedule !== ttsPlaySession) {
      ttsPending = Math.max(0, ttsPending - 1)
      if (ttsPending === 0) resumeRecognitionAfterTts()
      return
    }

    let usedBrowser = false
    try {
      await playEdgeTts(line.trim(), sessionAtSchedule)
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
  suppressRecognitionRestart = true
  try {
    recognition.stop()
  } catch {
    /* ignore */
  }
  isListening.value = false
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

/** 流式结束后一次性朗读全文，避免按句多次请求 TTS 造成句间长时间停顿 */
function speakStreamTail(strippedFinal) {
  if (!voiceOutputEnabled.value) return
  const tail = (strippedFinal || '').trim()
  if (tail) speakLine(tail)
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
  recognition.continuous = true
  recognition.maxAlternatives = 1
  // 开启 interim 有利于中文在部分浏览器中更快产出 isFinal 结果
  recognition.interimResults = true

  recognition.onstart = () => {
    sttNetworkWarn.value = false
  }

  recognition.onresult = (ev) => {
    let finalText = ''
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      const r = ev.results[i]
      if (r.isFinal) finalText += r[0].transcript
    }
    const text = finalText.trim()
    if (!text) return
    if (isVoiceInputTooShort(text)) return

    if (!isTyping.value) sendMessage(text)
  }

  recognition.onerror = (ev) => {
    if (ev.error === 'no-speech' || ev.error === 'aborted') return
    if (ev.error === 'not-allowed') {
      sttUnsupported.value = true
    }
    if (ev.error === 'network') {
      sttNetworkWarn.value = true
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

function togglePhoneMode() {
  if (!getSpeechRecognition()) {
    sttUnsupported.value = true
    return
  }

  voicePhoneActive.value = !voicePhoneActive.value
  if (voicePhoneActive.value) {
    suppressRecognitionRestart = false
    sttNetworkWarn.value = false
    cancelSpeech()
    ttsBuffer = ''
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
    suppressRecognitionRestart = false
    sttNetworkWarn.value = false
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

async function sendMessage(forcedText) {
  const text = typeof forcedText === 'string' ? forcedText : userInput.value
  const trimmed = text.trim()
  if (!trimmed || isTyping.value) return
  if (typeof forcedText === 'string' && isVoiceInputTooShort(trimmed)) return

  if (typeof forcedText !== 'string') userInput.value = ''

  cancelSpeech()
  ttsBuffer = ''

  messages.value.push({ id: nextMsgId(), type: 'user', text: trimmed })
  isTyping.value = true
  const aiMsg = { id: nextMsgId(), type: 'ai', text: '' }
  messages.value.push(aiMsg)

  if (isTeamIdentityQuestion(trimmed)) {
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
  const killTimer = setTimeout(() => controller.abort(), CHAT_FETCH_MS)

  try {
    const chatHistory = messages.value
      .slice(0, -1)
      .map((m) => ({ role: m.type === 'user' ? 'user' : 'assistant', content: m.text }))

    const response = await fetch(`${API_URL}/chat/companion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: chatHistory, mode: 'companion' }),
      signal: controller.signal
    })

    if (!response.ok || !response.body) {
      throw new Error(`http ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')

    while (true) {
      const { done, value } = await reader.read()
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
      await nextTick()
      chatBox.value?.scrollTo(0, chatBox.value.scrollHeight)
    }
    await nextTick()
    aiMsg.text = stripParentheticals(aiMsg.text)
    await nextTick()
    speakStreamTail(aiMsg.text)
  } catch (e) {
    const name = e && e.name
    if (name === 'AbortError') {
      aiMsg.text = '请求超时，请检查网络或稍后重试。'
    } else {
      aiMsg.text = '网络错误，请稍后重试'
    }
    speakFullReply(aiMsg.text)
  } finally {
    clearTimeout(killTimer)
    isTyping.value = false
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
