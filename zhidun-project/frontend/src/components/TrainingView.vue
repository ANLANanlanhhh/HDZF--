<template>
  <div class="training-view">
    <div v-if="!currentScenario" class="scenario-selector">
      <h2 class="main-title">请选择防骗训练剧本</h2>
      <div v-for="category in scenariosData.categories" :key="category.id" class="category-block">
        <h3 class="category-title">{{ category.name }}</h3>
        <div class="scenarios-grid">
          <button 
            v-for="scenario in category.scenarios" 
            :key="scenario.id" 
            class="scenario-btn"
            @click="startScenario(scenario)">
            {{ scenario.title }}
          </button>
        </div>
      </div>
    </div>

    <div v-else class="quiz-area">
      <div class="top-bar">
        <h2 class="scenario-title">{{ currentScenario.title }}</h2>
        <button class="exit-btn" @click="exitTraining">退出训练</button>
      </div>

      <div v-if="!hasStartedQuiz" class="start-mask">
        <button class="huge-start-btn" @click="beginFirstQuestion">点击开始本局演练</button>
      </div>

      <div v-else-if="currentQuestion" class="question-container">
        <div class="question-box">
          <span class="label">当前问题：</span>
          <p class="text gold-text">{{ currentQuestion.question_text }}</p>
        </div>
        
        <div class="background-box">
          <span class="label">情景背景：</span>
          <p class="text">{{ currentQuestion.background_text }}</p>
        </div>

        <div class="options-box">
          <div v-if="isReading" class="reading-indicator">
            📢 正在语音播报，请认真听题...
          </div>
          <transition name="fade">
            <div v-show="!isReading" class="options-grid">
              <button 
                v-for="(opt, index) in currentQuestion.options" 
                :key="index"
                class="option-btn"
                @click="selectOption(opt)">
                {{ opt.text }}
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
import { ref, onMounted,onUnmounted } from 'vue'
// 声明向父组件发送的事件
const emit = defineEmits(['view-report'])
const scenariosData = ref({ categories: [] })
const currentScenario = ref(null)
const currentQuestionIndex = ref(0)
const currentQuestion = ref(null)
const hasStartedQuiz = ref(false)
const isReading = ref(false)
const showFeedback = ref(false)
const currentOption = ref(null)
const totalScore = ref(100) 

onMounted(async () => {
  try {
    // 假设你的后端跑在 8000 端口，和 ChatView 保持一致
    const response = await fetch('http://localhost:8000/api/scenarios') 
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

function readCurrentQuestion() {
  window.speechSynthesis.cancel()
  isReading.value = true
  showFeedback.value = false

  const bgText = currentQuestion.value.background_text
  const qText = currentQuestion.value.question_text
  const fullText = `情景背景：${bgText}。请听题：${qText}`

  const utterance = new SpeechSynthesisUtterance(fullText)
  utterance.lang = 'zh-CN'
  utterance.rate = 0.9 
  
  utterance.onend = () => {
    isReading.value = false 
  }
  
  utterance.onerror = () => {
    console.error("语音播放失败，强制显示选项")
    isReading.value = false
  }

  window.speechSynthesis.speak(utterance)
}

function selectOption(opt) {
  currentOption.value = opt
  totalScore.value += opt.score_change
  showFeedback.value = true
  window.speechSynthesis.cancel() 
}

function handleNext() {
  // 核心修改：关闭反馈弹窗
  showFeedback.value = false;

  if (currentOption.value.next_q === 'end') {
    localStorage.setItem('zhidun_final_score', totalScore.value)
    window.speechSynthesis.cancel()
    // 核心修改：通知 App.vue 切换到报告页
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
  window.speechSynthesis.cancel()
  currentScenario.value = null
  hasStartedQuiz.value = false
}

onUnmounted(() => {
  window.speechSynthesis.cancel()
})
</script>

<style scoped>
/* 保持你原有的 CSS 样式不变 */
.training-view { min-height: 100vh; background-color: #8b0000; color: #ffffff; padding: 20px; font-family: "SimSun", "STSong", serif; }
.main-title, .scenario-title { text-align: center; font-size: 36px; color: #ffd700; margin-bottom: 30px; }
.category-block { margin-bottom: 40px; background: rgba(255, 255, 255, 0.1); padding: 20px; border-radius: 10px; }
.category-title { font-size: 28px; margin-bottom: 15px; border-bottom: 2px solid #ffd700; padding-bottom: 10px; }
.scenarios-grid { display: grid; gap: 20px; }
.scenario-btn { background-color: #ffd700; color: #8b0000; font-size: 28px; font-weight: bold; padding: 20px; border: 4px solid #ffffff; border-radius: 12px; cursor: pointer; }
.scenario-btn:hover { background-color: #ffffff; }
.top-bar { display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #ffd700; padding-bottom: 10px; margin-bottom: 20px; }
.exit-btn { background: #333; color: #fff; font-size: 24px; padding: 10px 20px; border: 2px solid #fff; cursor: pointer; }
.start-mask { display: flex; justify-content: center; align-items: center; height: 60vh; }
.huge-start-btn { font-size: 40px; padding: 40px 60px; background-color: #ffd700; color: #8b0000; border: 6px solid #fff; border-radius: 20px; cursor: pointer; animation: pulse 2s infinite; }
@keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
.question-box, .background-box { background: rgba(0, 0, 0, 0.3); padding: 25px; border: 3px solid #ffd700; border-radius: 15px; margin-bottom: 20px; }
.label { font-size: 24px; color: #cccccc; display: block; margin-bottom: 10px; }
.text { font-size: 32px; line-height: 1.6; }
.gold-text { color: #ffd700; font-weight: bold; font-size: 36px; }
.reading-indicator { text-align: center; font-size: 28px; color: #ffd700; padding: 20px; border: 2px dashed #ffd700; margin-top: 20px; }
.options-grid { display: flex; flex-direction: column; gap: 20px; margin-top: 30px; }
.option-btn { background-color: #ffffff; color: #000000; font-size: 28px; padding: 25px; text-align: left; border: 4px solid #333; border-radius: 10px; cursor: pointer; }
.option-btn:hover { background-color: #ffd700; }
.feedback-modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.9); display: flex; justify-content: center; align-items: center; z-index: 1000; }
.feedback-content { background: #ffffff; color: #000; padding: 40px; border-radius: 20px; max-width: 80%; text-align: center; border: 8px solid #ffd700; }
.feedback-content h3 { font-size: 48px; margin-bottom: 20px; }
.good { color: #008000; }
.bad { color: #ff0000; }
.feedback-text { font-size: 32px; line-height: 1.5; margin-bottom: 30px; }
.next-btn { background-color: #8b0000; color: #ffd700; font-size: 36px; padding: 20px 40px; border: none; border-radius: 10px; cursor: pointer; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.5s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>