<template>
  <div class="chat-view" @pointerdown="onChatFirstInteract">
    <p class="intro">
      打字或开「语音电话」和小孙聊。默认会朗读小孙的回复。若听不到声，请先<strong>任意点一下空白处</strong>，或把「语音播报」先关再开（浏览器要求点一下才允许播放）。
    </p>

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

    <div class="chat-box" ref="chatBox">
      <div v-for="(msg, i) in messages" :key="msg.id" :class="['message', msg.type]">
        <div class="bubble">
          <span
            v-if="msg.type === 'ai' && !msg.text && isTyping && i === messages.length - 1"
            class="typing-hint"
            >小孙正在回复…</span>
          <span v-else>{{ msg.text }}</span>
        </div>
      </div>
    </div>

    <div v-if="showAlert" class="alert">
      ⚠️ 警告！这是诈骗测试！请勿透露个人信息！
    </div>

    <div class="input-area">
      <input
        v-model="userInput"
        @keyup.enter="sendMessage()"
        placeholder="输入您想说的话..."
      />
      <button type="button" @click="sendMessage()">发送</button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onUnmounted } from 'vue'

let msgIdSeq = 0
function nextMsgId() {
  return ++msgIdSeq
}

const messages = ref([
  { id: nextMsgId(), type: 'ai', text: '您好！我是小孙，有什么想聊的吗？' }
])
const userInput = ref('')
const showAlert = ref(false)
const API_URL = 'http://localhost:8000'
const isTyping = ref(false)
/** 聊天请求超时（毫秒），避免卡住导致 isTyping 永远为 true、语音也无法再发 */
const CHAT_FETCH_MS = 120000

const chatBox = ref(null)

const voiceOutputEnabled = ref(true)
const voicePhoneActive = ref(false)
const isListening = ref(false)
const sttUnsupported = ref(false)

let recognition = null
let ttsBuffer = ''
let ttsPending = 0
let ttsChain = Promise.resolve()
/** @type {HTMLAudioElement | null} */
let currentAudio = null

function getSpeechRecognition() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
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

function cancelSpeech() {
  window.speechSynthesis.cancel()
  ttsPending = 0
  ttsChain = Promise.resolve()
  if (currentAudio) {
    currentAudio.pause()
    currentAudio.src = ''
    currentAudio = null
  }
}

function playBrowserTts(text) {
  return new Promise((resolve) => {
    const u = new SpeechSynthesisUtterance(text.trim())
    u.lang = 'zh-CN'
    u.rate = 0.88
    u.pitch = 0.98
    const v = pickZhVoiceFallback()
    if (v) u.voice = v
    u.onend = () => resolve()
    u.onerror = () => resolve()
    window.speechSynthesis.speak(u)
  })
}

function playEdgeTts(text) {
  return new Promise((resolve, reject) => {
    fetch(`${API_URL}/api/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    })
      .then((res) => {
        if (!res.ok) throw new Error('tts http')
        return res.blob()
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob)
        const a = new Audio(url)
        currentAudio = a
        a.onended = () => {
          URL.revokeObjectURL(url)
          currentAudio = null
          resolve()
        }
        a.onerror = () => {
          URL.revokeObjectURL(url)
          currentAudio = null
          reject(new Error('audio'))
        }
        const p = a.play()
        if (p !== undefined) p.catch(() => reject(new Error('play blocked')))
      })
      .catch(reject)
  })
}

function speakLine(text) {
  const line = stripParentheticals(text)
  if (!voiceOutputEnabled.value || !line.trim()) return
  ttsPending++
  pauseRecognitionForTts()
  ttsChain = ttsChain.then(async () => {
    try {
      await playEdgeTts(line.trim())
    } catch {
      await playBrowserTts(line.trim())
    } finally {
      ttsPending = Math.max(0, ttsPending - 1)
      if (ttsPending === 0) resumeRecognitionAfterTts()
    }
  })
}

function pauseRecognitionForTts() {
  // 语音电话开启时不关闭麦克风，才能像真电话一样随时打断朗读
  if (!recognition || !voicePhoneActive.value) return
}

function resumeRecognitionAfterTts() {
  if (!recognition || !voicePhoneActive.value || isTyping.value) return
  try {
    recognition.start()
    isListening.value = true
  } catch {
    /* 可能已在监听 */
  }
}

/** DeepSeek 完整回复到达后再分段朗读（不在流式过程中抢先念） */
function speakFullReply(fullText) {
  if (!voiceOutputEnabled.value) return
  ttsBuffer = stripParentheticals(fullText || '').trim()
  if (!ttsBuffer) return

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
  // 从关→开：用户点击即算手势，浏览器才允许出声；立刻朗读当前最后一条小孙的话
  if (wasOff) {
    ttsBuffer = ''
    const lastAi = [...messages.value]
      .reverse()
      .find((m) => m.type === 'ai' && m.text && String(m.text).trim())
    if (lastAi) speakFullReply(lastAi.text)
  }
}

/** 默认已开播报时，需一次点击/触摸解除浏览器静音策略，再播欢迎语（避免与按钮操作重复播） */
let didUnlockWelcome = false
function onChatFirstInteract(ev) {
  const t = ev.target
  if (t && (t.closest && (t.closest('button') || t.closest('input')))) return
  if (didUnlockWelcome) return
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
  // 仅用最终结果发送，减少回声误触与浏览器差异；打断也只在一句说完时触发
  recognition.interimResults = false

  recognition.onresult = (ev) => {
    let finalText = ''
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      const r = ev.results[i]
      if (r.isFinal) finalText += r[0].transcript
    }
    const text = finalText.trim()
    if (!text) return

    // 打电话且小孙正在朗读：先停播再发您这句（避免回声用 interim 已取消）
    if (
      voicePhoneActive.value &&
      (ttsPending > 0 || currentAudio || window.speechSynthesis.speaking)
    ) {
      cancelSpeech()
    }
    if (!isTyping.value) sendMessage(text)
  }

  recognition.onerror = (ev) => {
    // no-speech / aborted 在连续识别里较常见，不当作致命错误
    if (ev.error === 'no-speech' || ev.error === 'aborted') return
    if (ev.error === 'not-allowed') {
      sttUnsupported.value = true
    }
    isListening.value = false
  }

  recognition.onend = () => {
    if (!voicePhoneActive.value) {
      isListening.value = false
      return
    }
    // 延后重启，避免 InvalidStateError: already started
    setTimeout(() => {
      if (!voicePhoneActive.value || !recognition) return
      try {
        recognition.start()
        isListening.value = true
      } catch {
        setTimeout(() => {
          if (!voicePhoneActive.value || !recognition) return
          try {
            recognition.start()
            isListening.value = true
          } catch {
            isListening.value = false
          }
        }, 400)
      }
    }, 200)
  }
}

function togglePhoneMode() {
  if (!getSpeechRecognition()) {
    sttUnsupported.value = true
    return
  }
  if (!recognition) setupRecognition()
  if (!recognition) return

  voicePhoneActive.value = !voicePhoneActive.value
  if (voicePhoneActive.value) {
    cancelSpeech()
    ttsBuffer = ''
    try {
      recognition.start()
      isListening.value = true
    } catch {
      isListening.value = false
    }
  } else {
    try {
      recognition.stop()
    } catch {
      /* ignore */
    }
    isListening.value = false
  }
}

async function sendMessage(forcedText) {
  const text = typeof forcedText === 'string' ? forcedText : userInput.value
  const trimmed = text.trim()
  if (!trimmed || isTyping.value) return

  if (typeof forcedText !== 'string') userInput.value = ''

  cancelSpeech()
  ttsBuffer = ''

  messages.value.push({ id: nextMsgId(), type: 'user', text: trimmed })
  isTyping.value = true
  const aiMsg = { id: nextMsgId(), type: 'ai', text: '' }
  messages.value.push(aiMsg)

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
    speakFullReply(aiMsg.text)
  } catch (e) {
    const name = e && e.name
    if (name === 'AbortError') {
      aiMsg.text = '请求超时，请检查网络或稍后重试。'
    } else {
      aiMsg.text = '网络错误，请稍后重试'
    }
  } finally {
    clearTimeout(killTimer)
    isTyping.value = false
    await nextTick()
    chatBox.value?.scrollTo(0, chatBox.value.scrollHeight)
  }
}

onMounted(() => {
  window.speechSynthesis.getVoices()
})

onUnmounted(() => {
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
.intro {
  font-size: 22px;
  line-height: 1.5;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #fff8dc;
  border: 3px solid #000;
  border-radius: 8px;
}

.voice-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.btn-phone,
.btn-tts {
  flex: 1;
  min-width: 140px;
  padding: 18px 24px;
  font-size: 26px;
  font-weight: bold;
  border: 4px solid #000;
  border-radius: 8px;
  cursor: pointer;
}

.btn-phone {
  background: #2f4f4f;
  color: #fff;
}

.btn-phone.active {
  background: #1a6b3a;
  color: #fff;
}

.btn-tts {
  background: #4a4a4a;
  color: #eee;
}

.btn-tts.active {
  background: #6b4f1a;
  color: #ffd700;
}

.listening {
  font-size: 24px;
  color: #0d5c2e;
  font-weight: bold;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot {
  display: inline-block;
  width: 14px;
  height: 14px;
  background: #c00;
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

.stt-warn {
  font-size: 22px;
  color: #8b0000;
  margin-bottom: 10px;
}

.chat-view {
  display: flex;
  flex-direction: column;
  height: 600px;
}

.chat-box {
  flex: 1;
  overflow-y: auto;
  background: #f5f5dc;
  border: 4px solid #000;
  padding: 20px;
}

.message {
  margin: 20px 0;
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.ai {
  justify-content: flex-start;
}

.bubble {
  padding: 20px 30px;
  font-size: 28px;
  border-radius: 18px;
  max-width: 70%;
  min-height: 1.2em;
  box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.2);
  position: relative;
}

.typing-hint {
  color: #666;
  font-style: italic;
}

.message.user .bubble {
  background: #95ec69;
  border: 3px solid #000;
}

.message.user .bubble::after {
  content: '';
  position: absolute;
  right: -10px;
  top: 15px;
  width: 0;
  height: 0;
  border: 10px solid transparent;
  border-left-color: #95ec69;
  border-right: 0;
}

.message.ai .bubble {
  background: #fff;
  border: 3px solid #000;
}

.message.ai .bubble::before {
  content: '';
  position: absolute;
  left: -10px;
  top: 15px;
  width: 0;
  height: 0;
  border: 10px solid transparent;
  border-right-color: #fff;
  border-left: 0;
}

.alert {
  background: #ff0000;
  color: #fff;
  padding: 30px;
  font-size: 32px;
  font-weight: bold;
  text-align: center;
  border: 4px solid #000;
  margin: 20px 0;
  animation: shake 0.5s;
}

@keyframes shake {
  0%,
  100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-10px);
  }
  75% {
    transform: translateX(10px);
  }
}

.input-area {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.input-area input {
  flex: 1;
  padding: 20px;
  font-size: 28px;
  border: 4px solid #000;
  border-radius: 8px;
}

.input-area button {
  padding: 20px 40px;
  font-size: 28px;
  font-weight: bold;
  background: #8b0000;
  color: #ffd700;
  border: 4px solid #000;
  border-radius: 8px;
  cursor: pointer;
}

.input-area button:active {
  transform: scale(0.95);
}
</style>
