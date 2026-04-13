<template>
  <div class="training-view">
    <!-- 第一步：四大类（与后端 scenarios.json 分类 id 一致） -->
    <section v-if="!currentScenario && !selectedGroupId" class="category-pick">
      <div class="selector-toolbar">
        <button type="button" class="btn-back-home" @click="onBackHome">返回主页</button>
      </div>
      <h2 class="main-title category-pick-title">选择演练类型</h2>
      <p class="main-lead">请先选择诈骗大类，再进入该类下的具体剧本</p>
      <div class="category-pick-card">
        <div class="category-pick-grid">
          <button
            v-for="item in groupPickItems"
            :key="item.id"
            type="button"
            class="category-pick-btn"
            @click="selectTrainingGroup(item.id)"
          >
            <span class="category-pick-btn__name">{{ item.name }}</span>
          </button>
        </div>
      </div>
    </section>

    <!-- 第二步：该大类下的剧本列表（原交互） -->
    <div v-else-if="!currentScenario" class="scenario-selector">
      <div class="selector-toolbar selector-toolbar--split">
        <button type="button" class="btn-back-home" @click="onBackHome">返回主页</button>
        <button type="button" class="btn-back-tier" @click="backToGroupPick">返回大类</button>
      </div>
      <h2 class="main-title">请选择防骗训练剧本</h2>
      <p class="main-lead">选择下方剧本进入演练，支持语音读题</p>
      <p v-if="categoriesForSelectedGroup.length === 0" class="main-lead scenario-empty-hint">
        暂未能加载该类剧本，请检查网络后重试。
      </p>
      <div
        v-for="category in categoriesForSelectedGroup"
        :key="category.id"
        class="category-block"
      >
        <div class="category-head">
          <h3 class="category-title">{{ category.name }}</h3>
        </div>
        <div class="scenarios-grid">
          <button
            v-for="scenario in category.scenarios"
            :key="scenario.id"
            type="button"
            class="scenario-btn"
            @click="startScenario(scenario)"
          >
            <span class="scenario-btn__text">{{ scenario.title }}</span>
            <span class="scenario-btn__action">进入演练</span>
          </button>
        </div>
      </div>
    </div>

    <div v-else class="quiz-area">
      <div class="top-bar">
        <h2 class="scenario-title">{{ currentScenario.title }}</h2>
        <button type="button" class="exit-btn" @click="exitTraining">返回选剧本</button>
      </div>

      <div v-if="!hasStartedQuiz" class="start-mask">
        <button class="huge-start-btn" @click="beginFirstQuestion">点击开始本局演练</button>
      </div>

      <div v-else-if="currentQuestion" class="question-container">
        <section class="question-box question-box--stem" aria-labelledby="q-stem-label">
          <div class="question-box__head">
            <span id="q-stem-label" class="label label--stem">本题</span>
          </div>
          <p class="text text--stem">{{ currentQuestion.question_text }}</p>
        </section>

        <section class="background-box scene-card" aria-labelledby="scene-label">
          <span id="scene-label" class="label label--scene">情景背景</span>
          <p class="text text--scene">{{ currentQuestion.background_text }}</p>
        </section>

        <div class="options-box">
          <div v-if="isReading" class="reading-indicator">
            <span class="reading-main">正在语音播报，您可边听边选答案</span>
            <span class="reading-hint">无需等播报结束，点选项会自动停止朗读</span>
          </div>
          <p class="options-heading">请选择您的回答</p>
          <transition name="fade">
            <div class="options-grid" role="list">
              <button
                v-for="(opt, index) in currentQuestion.options"
                :key="index"
                type="button"
                class="option-btn"
                @click="selectOption(opt)"
              >
                <span class="option-btn__text">{{ opt.text }}</span>
              </button>
            </div>
          </transition>
        </div>
      </div>

      <div v-if="showFeedback" class="feedback-modal">
        <div class="feedback-content">
          <h3 :class="currentOption.score_change > 0 ? 'good' : 'bad'">
            {{ currentOption.score_change > 0 ? '做得很棒！' : '危险操作！' }}
          </h3>
          <p class="feedback-text">{{ currentOption.feedback }}</p>
          <button class="next-btn" @click="handleNext">
            {{ currentOption.next_q === 'end' ? '查看评估报告' : '继续下一题' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { recordTrainingComplete } from '../utils/homeStats'
import { clampPercentScore } from '../utils/trainingScore.js'
import { API_BASE } from '../apiBase.js'

const API_URL = API_BASE

// 声明向父组件发送的事件
const emit = defineEmits(['view-report', 'go-home'])

const scenariosData = ref({ categories: [] })

/** 与 backend/scenarios.json 中 categories[].id 一致，顺序即展示顺序 */
const GROUP_ORDER = ['deepfake', 'livestream', 'financial', 'insurance']
const GROUP_FALLBACK_NAME = {
  deepfake: '深度伪造诈骗',
  livestream: '网络直播诈骗',
  financial: '理财类诈骗',
  insurance: '非法代理退保'
}

/** null：显示四大类；已选 id：显示该大类下剧本 */
const selectedGroupId = ref(null)

const groupPickItems = computed(() => {
  const cats = scenariosData.value.categories || []
  return GROUP_ORDER.map((id) => {
    const c = cats.find((x) => x.id === id)
    return { id, name: c?.name || GROUP_FALLBACK_NAME[id] || id }
  })
})

const categoriesForSelectedGroup = computed(() => {
  const id = selectedGroupId.value
  if (!id) return []
  const cats = scenariosData.value.categories || []
  return cats.filter((c) => c.id === id)
})

function onBackHome() {
  selectedGroupId.value = null
  emit('go-home')
}

function selectTrainingGroup(id) {
  selectedGroupId.value = id
}

function backToGroupPick() {
  selectedGroupId.value = null
}

const currentScenario = ref(null)
const currentQuestionIndex = ref(0)
const currentQuestion = ref(null)
const hasStartedQuiz = ref(false)
const isReading = ref(false)
const showFeedback = ref(false)
const currentOption = ref(null)
const totalScore = ref(100) 

/** @type {HTMLAudioElement | null} */
let trainingAudio = null

function pickZhVoice() {
  const voices = window.speechSynthesis.getVoices()
  return (
    voices.find((v) => v.lang && v.lang.toLowerCase().includes('zh')) ||
    voices.find((v) => v.name && /chinese|中文|mandarin/i.test(v.name)) ||
    voices[0] ||
    null
  )
}

function stopTrainingAudio() {
  window.speechSynthesis.cancel()
  if (trainingAudio) {
    trainingAudio.pause()
    trainingAudio.src = ''
    trainingAudio = null
  }
}

function fallbackBrowserReadQuestion(fullText, onDone) {
  const utterance = new SpeechSynthesisUtterance(fullText)
  utterance.lang = 'zh-CN'
  utterance.rate = 1.05
  utterance.pitch = 1.02
  const v = pickZhVoice()
  if (v) utterance.voice = v
  utterance.onend = () => onDone()
  utterance.onerror = () => onDone()
  window.speechSynthesis.speak(utterance)
}

onMounted(async () => {
  window.speechSynthesis.getVoices()
  window.speechSynthesis.onvoiceschanged = () => {
    window.speechSynthesis.getVoices()
  }
  try {
    const response = await fetch(`${API_URL}/api/scenarios`)
    const data = await response.json()
    scenariosData.value = data
  } catch (error) {
    console.error('获取剧本数据失败:', error)
    alert('网络错误，无法加载防骗剧本')
  }
})

function startScenario(scenario) {
  currentScenario.value = scenario
  currentQuestionIndex.value = 0
  currentQuestion.value = scenario.questions[0]
  hasStartedQuiz.value = false
  totalScore.value = 100
}

function beginFirstQuestion() {
  hasStartedQuiz.value = true
  readCurrentQuestion()
}

async function readCurrentQuestion() {
  stopTrainingAudio()
  isReading.value = true
  showFeedback.value = false

  const bgText = currentQuestion.value.background_text
  const qText = currentQuestion.value.question_text
  const fullText = `情景背景：${bgText}。请听题：${qText}`

  const finish = () => {
    isReading.value = false
  }

  try {
    const response = await fetch(`${API_URL}/api/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: fullText })
    })
    if (!response.ok) throw new Error('tts http')
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    trainingAudio = audio
    audio.onended = () => {
      URL.revokeObjectURL(url)
      trainingAudio = null
      finish()
    }
    audio.onerror = () => {
      URL.revokeObjectURL(url)
      trainingAudio = null
      fallbackBrowserReadQuestion(fullText, finish)
    }
    const p = audio.play()
    if (p !== undefined) {
      p.catch(() => {
        URL.revokeObjectURL(url)
        trainingAudio = null
        fallbackBrowserReadQuestion(fullText, finish)
      })
    }
  } catch (e) {
    console.error('读题语音:', e)
    fallbackBrowserReadQuestion(fullText, finish)
  }
}

function selectOption(opt) {
  stopTrainingAudio()
  isReading.value = false
  currentOption.value = opt
  totalScore.value += opt.score_change
  showFeedback.value = true
}

function handleNext() {
  // 核心修改：关闭反馈弹窗
  showFeedback.value = false;

  if (currentOption.value.next_q === 'end') {
    const finalPct = clampPercentScore(totalScore.value)
    localStorage.setItem('zhidun_final_score', String(finalPct))
    recordTrainingComplete(finalPct)
    stopTrainingAudio()
    emit('view-report')
  } else {
    const nextIndex = currentScenario.value.questions.findIndex(q => q.q_id === currentOption.value.next_q)
    if (nextIndex !== -1) {
      currentQuestion.value = currentScenario.value.questions[nextIndex]
      readCurrentQuestion()
    } else {
       alert("题库发生错误，未找到下一题。")
       exitTraining()
    }
  }
}

function exitTraining() {
  stopTrainingAudio()
  currentScenario.value = null
  hasStartedQuiz.value = false
}

onUnmounted(() => {
  stopTrainingAudio()
})
</script>

<style scoped>
.training-view {
  /* 主色标题 / 琥珀按钮 / 辅色点缀；页底 --zd-plate-page-bg */
  --zd-burgundy: var(--zd-plate-ink, #5b7c99);
  --zd-burgundy-hover: var(--zd-plate-ink-hover, #6d8fb0);
  min-height: 100vh;
  min-height: 100dvh;
  width: 100%;
  background: var(--zd-plate-page-bg, #f5f7fa);
  color: var(--zd-ink, #2c2825);
  padding: clamp(14px, 2.2vw, 28px) clamp(12px, 2.2vw, 32px);
  font-family: var(--zd-font, 'Microsoft YaHei', sans-serif);
  /* 适老化：整页基准略大于 body，inherit 的控件一并略大 */
  font-size: clamp(20px, 2.45vw, 24px);
  max-width: min(1280px, 100%);
  margin: 0 auto;
  box-sizing: border-box;
}

.selector-toolbar {
  width: 100%;
  margin-bottom: 6px;
}

.selector-toolbar--split {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.btn-back-tier {
  padding: 10px 20px;
  font-size: clamp(20px, 1.95vw, 23px);
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--zd-plate-ink, #5b7c99);
  background: #fffef8;
  border: 2px solid rgba(127, 166, 194, 0.55);
  border-radius: 10px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(92, 26, 46, 0.12);
  transition: filter 0.15s, transform 0.12s;
}

.btn-back-tier:hover {
  filter: brightness(1.03);
  border-color: rgba(91, 124, 153, 0.45);
}

.btn-back-tier:active {
  transform: scale(0.98);
}

/* 四大类入口（适老化大按钮、高对比色） */
.category-pick {
  width: 100%;
}

.category-pick-title {
  margin-bottom: clamp(8px, 1.2vw, 12px);
}

.category-pick-card {
  max-width: var(--zd-content-card-max, min(1000px, 100%));
  margin: 0 auto;
  background: var(--zd-surface, #fff);
  border-radius: 16px;
  padding: clamp(16px, 2.5vw, 26px);
  border: 1px solid rgba(127, 166, 194, 0.4);
  box-shadow: 0 2px 12px rgba(91, 124, 153, 0.08);
  box-sizing: border-box;
}

.category-pick-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

@media (max-width: 520px) {
  .category-pick-grid {
    grid-template-columns: 1fr;
  }
}

.category-pick-btn {
  min-height: 92px;
  padding: 16px 14px;
  border: none;
  border-radius: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-family: inherit;
  background: var(--zd-plate-btn-bg, #7fa6c2);
  color: #fff;
  /* 顶缘高光 + 橙投影 + 轻落地影，避免「土黄一块」 */
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.28),
    0 4px 14px rgba(127, 166, 194, 0.38),
    0 2px 6px rgba(80, 52, 12, 0.1);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    background-color 0.2s ease;
}

.category-pick-btn:hover {
  background: var(--zd-plate-btn-hover, #6b93af);
  transform: translateY(-3px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.35),
    0 10px 26px rgba(127, 166, 194, 0.45),
    0 4px 12px rgba(80, 52, 12, 0.12);
}

.category-pick-btn:active {
  transform: translateY(-1px) scale(0.98);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.2),
    0 3px 10px rgba(127, 166, 194, 0.35),
    0 1px 4px rgba(80, 52, 12, 0.1);
}

.category-pick-btn__name {
  font-size: clamp(21px, 2.35vw, 27px);
  font-weight: 700;
  color: #fff;
  line-height: 1.4;
  letter-spacing: 0.04em;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.18);
}

.btn-back-home {
  padding: 10px 20px;
  font-size: clamp(20px, 1.95vw, 23px);
  font-weight: 600;
  letter-spacing: 0.06em;
  color: #fff;
  background: var(--zd-plate-btn-bg-flat, #7fa6c2);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.25),
    0 3px 12px rgba(127, 166, 194, 0.36),
    0 2px 5px rgba(80, 52, 12, 0.09);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    background-color 0.2s ease;
}

.btn-back-home:hover {
  background: var(--zd-plate-btn-hover, #6b93af);
  transform: translateY(-2px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.32),
    0 6px 18px rgba(127, 166, 194, 0.42),
    0 3px 8px rgba(80, 52, 12, 0.11);
}

.btn-back-home:active {
  transform: translateY(0) scale(0.98);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.18),
    0 2px 8px rgba(127, 166, 194, 0.32),
    0 1px 3px rgba(80, 52, 12, 0.08);
}

.scenario-empty-hint {
  color: #b45309;
}

.main-lead {
  text-align: center;
  font-size: clamp(20px, 2.05vw, 23px);
  color: var(--zd-ink-muted, #64748b);
  margin: 0 0 clamp(18px, 2.2vw, 26px);
  line-height: 1.5;
}

.main-title,
.scenario-title {
  text-align: center;
  font-size: clamp(30px, 3.8vw, 45px);
  font-weight: 700;
  color: var(--zd-burgundy, #5b7c99);
  margin-bottom: clamp(20px, 2.5vw, 30px);
  letter-spacing: 0.04em;
}

/* 选剧本页：大标题在上，说明在下，标题与说明间距收紧 */
.scenario-selector .main-title {
  margin-bottom: clamp(8px, 1.2vw, 12px);
}

/* 分类外框：单卡片、轻阴影，避免大盒套灰盒 */
.category-block {
  --cat-accent: var(--zd-plate-card, #7fa6c2);
  max-width: var(--zd-content-card-max, min(1000px, 100%));
  margin: 0 auto 16px;
  background: var(--zd-surface, #fff);
  border-radius: 16px;
  border: 1px solid rgba(127, 166, 194, 0.4);
  box-shadow: 0 2px 12px rgba(91, 124, 153, 0.08);
  overflow: hidden;
}

.category-head {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 14px 8px;
  background: transparent;
  border-bottom: none;
}

.category-title {
  font-size: clamp(21px, 2.15vw, 23px);
  font-weight: 700;
  margin: 0;
  text-align: center;
  color: var(--zd-burgundy, #5b7c99);
  letter-spacing: 0.14em;
}

.scenarios-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 12px 14px;
}

/* 剧本行：左标题 + 右主按钮，拉满宽度、减轻粗横线压迫感 */
.scenario-btn {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  width: 100%;
  margin: 0;
  padding: 14px;
  text-align: left;
  font: inherit;
  cursor: pointer;
  background: #fdfcfa;
  border: none;
  border-radius: 12px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.55);
  transition: background 0.18s, box-shadow 0.2s, transform 0.15s;
}

.scenario-btn:hover {
  background: #fff;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.85),
    0 4px 16px rgba(44, 40, 37, 0.07);
  transform: translateY(-1px);
}

.scenario-btn:active {
  transform: translateY(0);
}

.scenario-btn__text {
  flex: 1;
  min-width: 0;
  font-size: clamp(21px, 2.25vw, 24px);
  font-weight: 600;
  line-height: 1.5;
  color: var(--zd-ink, #2c2825);
  word-break: break-word;
  text-align: left;
}

.scenario-btn__action {
  flex-shrink: 0;
  font-size: clamp(20px, 2.05vw, 23px);
  font-weight: 700;
  color: #fff;
  padding: 14px 22px;
  min-height: 52px;
  min-width: 6.5em;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: var(--zd-plate-btn-bg, #7fa6c2);
  border: 1px solid rgba(160, 195, 215, 0.55);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.22),
    0 3px 12px rgba(127, 166, 194, 0.34),
    0 2px 5px rgba(80, 52, 12, 0.08);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    background-color 0.2s ease,
    border-color 0.2s ease;
}

.scenario-btn:hover .scenario-btn__action {
  background: var(--zd-plate-btn-hover, #6b93af);
  border-color: rgba(120, 165, 190, 0.55);
  transform: translateY(-2px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.3),
    0 8px 20px rgba(127, 166, 194, 0.4),
    0 4px 10px rgba(80, 52, 12, 0.1);
}

@media (max-width: 520px) {
  .scenario-btn {
    flex-direction: column;
    align-items: stretch;
    padding: 14px;
  }

  .scenario-btn__text {
    text-align: center;
  }

  .scenario-btn__action {
    width: 100%;
    min-height: 50px;
  }
}
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--zd-border, rgba(74, 60, 48, 0.14));
  padding-bottom: 10px;
  margin-bottom: 14px;
}
.exit-btn {
  background: #64748b;
  color: #f8fafc;
  font-size: clamp(20px, 2.05vw, 22px);
  font-weight: 600;
  padding: 10px 18px;
  min-height: 44px;
  border: none;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.2s;
}
.exit-btn:hover {
  background: #475569;
}
.start-mask {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 50vh;
}
.huge-start-btn {
  font-size: clamp(26px, 2.85vw, 33px);
  font-weight: 700;
  padding: 20px 36px;
  background: var(--zd-plate-btn, #7fa6c2);
  color: #fff;
  border: none;
  border-radius: 999px;
  cursor: pointer;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.24),
    0 8px 26px rgba(127, 166, 194, 0.42),
    0 4px 12px rgba(80, 52, 12, 0.1);
  transition: box-shadow 0.2s ease, background-color 0.2s ease;
  animation: pulse 2s infinite;
}

.huge-start-btn:hover {
  background: var(--zd-plate-btn-hover, #6b93af);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.32),
    0 12px 32px rgba(127, 166, 194, 0.48),
    0 6px 14px rgba(80, 52, 12, 0.12);
}
@keyframes pulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.03);
  }
  100% {
    transform: scale(1);
  }
}
/* 本题：主视觉区，与情景卡明显区分 */
.question-box--stem {
  background: #fff;
  padding: 0;
  margin-bottom: 12px;
  border-radius: 14px;
  border: 1px solid rgba(127, 166, 194, 0.45);
  box-shadow: 0 6px 24px rgba(91, 124, 153, 0.08);
  overflow: hidden;
  border-left: 5px solid var(--zd-burgundy, #5b7c99);
}

.question-box__head {
  padding: 10px 18px 8px;
  background: rgba(127, 166, 194, 0.14);
  border-bottom: 1px solid rgba(127, 166, 194, 0.35);
}

.label--stem {
  display: inline-block;
  font-size: clamp(19px, 1.95vw, 21px);
  font-weight: 800;
  letter-spacing: 0.2em;
  color: var(--zd-burgundy, #5b7c99);
  margin: 0;
}

.text--stem {
  margin: 0;
  padding: 16px 18px 18px;
  font-size: clamp(24px, 2.65vw, 30px);
  line-height: 1.55;
  font-weight: 700;
  color: var(--zd-ink, #2c2825);
}

/* 情景背景：次要信息区，纸感、字略小 */
.scene-card {
  background: #f6f3ee;
  padding: 12px 16px 14px;
  margin-bottom: 14px;
  border-radius: 12px;
  border: 1px dashed rgba(74, 60, 48, 0.22);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
}

.label--scene {
  display: block;
  font-size: clamp(19px, 1.95vw, 21px);
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--zd-ink-muted, #5e5852);
  margin: 0 0 8px;
  text-transform: none;
}

.text--scene {
  margin: 0;
  font-size: clamp(22px, 2.25vw, 25px);
  line-height: 1.65;
  font-weight: 400;
  color: var(--zd-ink, #2c2825);
}
.reading-indicator {
  text-align: center;
  font-size: clamp(20px, 2.1vw, 23px);
  color: var(--zd-burgundy, #5b7c99);
  padding: 10px 12px;
  border: 1px dashed rgba(127, 166, 194, 0.55);
  border-radius: 10px;
  margin-bottom: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: rgba(255, 249, 242, 0.85);
}
.reading-main {
  font-weight: 700;
}
.reading-hint {
  font-size: clamp(19px, 1.95vw, 22px);
  color: var(--zd-ink-muted, #5e5852);
  font-weight: normal;
}

.options-heading {
  font-size: clamp(21px, 2.15vw, 24px);
  font-weight: 700;
  color: var(--zd-burgundy, #5b7c99);
  margin: 0 0 10px;
  letter-spacing: 0.08em;
}

.options-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 0;
}

.option-btn {
  display: flex;
  align-items: center;
  width: 100%;
  text-align: left;
  margin: 0;
  padding: 16px 18px;
  min-height: 60px;
  font: inherit;
  cursor: pointer;
  color: var(--zd-ink, #2c2825);
  background: #fdfcfa;
  border: 2px solid rgba(74, 60, 48, 0.2);
  border-radius: 12px;
  box-shadow: 0 2px 0 rgba(255, 255, 255, 0.9) inset, 0 4px 14px rgba(44, 40, 37, 0.06);
  transition:
    background 0.18s,
    border-color 0.18s,
    box-shadow 0.18s,
    transform 0.12s;
}

.option-btn__text {
  flex: 1;
  min-width: 0;
  font-size: clamp(22px, 2.25vw, 25px);
  line-height: 1.55;
  font-weight: 600;
}

.option-btn:hover {
  background: #fff;
  border-color: rgba(91, 124, 153, 0.4);
  box-shadow:
    0 2px 0 rgba(255, 255, 255, 1) inset,
    0 6px 20px rgba(91, 124, 153, 0.12);
  transform: translateY(-1px);
}

.option-btn:active {
  transform: translateY(0);
}

.option-btn:focus-visible {
  outline: none;
  border-color: var(--zd-burgundy, #5b7c99);
  box-shadow: 0 0 0 3px rgba(91, 124, 153, 0.22);
}
.feedback-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(28, 25, 23, 0.72);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.feedback-content {
  background: var(--zd-surface, #fff);
  color: var(--zd-ink, #2c2825);
  padding: clamp(20px, 3vw, 28px);
  border-radius: 16px;
  max-width: min(520px, 92vw);
  text-align: center;
  border: 1px solid var(--zd-border, rgba(74, 60, 48, 0.14));
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}
.feedback-content h3 {
  font-size: clamp(32px, 3.55vw, 39px);
  margin-bottom: 12px;
}
.good {
  color: #15803d;
}
.bad {
  color: #b91c1c;
}
.feedback-text {
  font-size: clamp(23px, 2.5vw, 26px);
  line-height: 1.6;
  margin-bottom: 18px;
}
.next-btn {
  background: var(--zd-plate-btn, #7fa6c2);
  color: #fff;
  font-size: clamp(23px, 2.4vw, 26px);
  font-weight: 600;
  padding: 14px 32px;
  min-height: 52px;
  border: none;
  border-radius: 999px;
  cursor: pointer;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.22),
    0 6px 18px rgba(127, 166, 194, 0.38),
    0 3px 8px rgba(80, 52, 12, 0.09);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    background-color 0.2s ease;
}

.next-btn:hover {
  background: var(--zd-plate-btn-hover, #6b93af);
  transform: translateY(-2px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.3),
    0 10px 26px rgba(127, 166, 194, 0.44),
    0 5px 12px rgba(80, 52, 12, 0.11);
}

.next-btn:active {
  transform: translateY(0);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>