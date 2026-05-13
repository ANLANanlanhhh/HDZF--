<template>
  <div
    class="app"
    :class="{
      'app--home': currentView === 'home',
      'app--chat': currentView === 'chat',
      'app--training': currentView === 'training',
      'app--plate-purple':
        currentView === 'training' || currentView === 'report'
    }"
  >
    <div v-if="showSectionChrome" class="app-section-chrome">
      <header class="header">
        <h1>银龄智盾</h1>
      </header>

      <nav class="nav nav--minimal" aria-label="主导航">
        <span class="nav-current" aria-current="page">{{ currentSectionLabel }}</span>
      </nav>
    </div>

    <main
      ref="mainScrollEl"
      :class="[
        'content',
        currentView === 'home' ? 'content-home' : 'content-page',
        currentView === 'chat' ? 'content-page--chat-fill' : ''
      ]"
    >
      <div class="view-transition-shell">
        <div class="view-transition-root">
          <HomeView
            v-if="currentView === 'home'"
            @go-chat="goChat"
            @go-training="currentView = 'training'"
            @go-report="currentView = 'report'"
          />

          <ChatView
            v-else-if="currentView === 'chat'"
            ref="chatViewRef"
            @end-chat="goHome"
          />

          <TrainingView
            v-else-if="currentView === 'training'"
            @view-report="currentView = 'report'"
            @go-home="goHome"
          />

          <ReportView v-else-if="currentView === 'report'" @go-home="goHome" />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, defineAsyncComponent } from 'vue'
import HomeView from './components/HomeView.vue'

const ChatView = defineAsyncComponent(() => import('./components/ChatView.vue'))
const TrainingView = defineAsyncComponent(() => import('./components/TrainingView.vue'))
const ReportView = defineAsyncComponent(() => import('./components/ReportView.vue'))

const currentView = ref('home')
const chatViewRef = ref(null)

/** 从首页点「找小孙聊天」进入：紧接用户点击触发欢迎语，满足浏览器有声播放策略 */
function goChat() {
  currentView.value = 'chat'
  nextTick(() => {
    chatViewRef.value?.tryWelcomeOnEnter?.()
  })
}

/** 主内容区滚动容器：切换板块时复位，避免从长页返回首页时「卡住再往上跳」 */
const mainScrollEl = ref(null)

const sectionLabels = {
  chat: '找小孙聊天',
  training: '防骗训练',
  report: '我的报告'
}

const currentSectionLabel = computed(
  () => sectionLabels[currentView.value] || ''
)

/** 非首页且非聊天时显示内页顶栏 + 导航（防骗训练/报告见 .app--plate-purple） */
const showSectionChrome = computed(
  () => currentView.value !== 'home' && currentView.value !== 'chat'
)

function resetMainScroll() {
  const el = mainScrollEl.value
  if (el) el.scrollTop = 0
  window.scrollTo(0, 0)
}

watch(currentView, (v) => {
  /* 回到首页时晚一帧再复位滚动，避免与顶栏卸除、主区域 class 切换抢同一帧布局 */
  if (v === 'home') {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => resetMainScroll())
    })
  } else {
    nextTick(() => resetMainScroll())
  }
})

function goHome() {
  currentView.value = 'home'
}
</script>

<style>
/* 银龄智盾 · 温润纸感主题（全局变量，供各页统一引用） */
:root {
  --zd-paper: #f4f1eb;
  --zd-paper-deep: #e8e2d8;
  --zd-ink: #2c2825;
  --zd-ink-muted: #5e5852;
  --zd-burgundy: #8b2942;
  --zd-burgundy-hover: #a33350;
  --zd-cream: #fff9f2;
  --zd-gold: #b8952f;
  --zd-gold-soft: #e8dcc4;
  --zd-surface: #ffffff;
  --zd-border: rgba(74, 60, 48, 0.14);
  --zd-shadow: 0 10px 40px rgba(44, 40, 37, 0.08);
  --zd-radius: 14px;
  /* 防骗训练分类卡片 / 报告正文白框共用宽度（与板块三报告卡一致） */
  --zd-content-card-max: min(1000px, 100%);
  --zd-font: 'Microsoft YaHei', 'PingFang SC', 'SimHei', system-ui, sans-serif;
  /* 内页顶栏下方导航条：与酒红主题同系，避免冷灰按钮 */
  --zd-nav-bg: linear-gradient(180deg, #5a2434 0%, #4a1d2a 100%);
  --zd-nav-pad-y: clamp(16px, 2.4vw, 20px);
  /* 内页顶栏标题区：适老化略增高 */
  --zd-nav-min-h: 58px;
  /*
   * 板块二、三：主色标题 / 辅色卡片 / 蓝按钮 / 浅灰底
   */
  --zd-plate-ink: #5b7c99;
  --zd-plate-card: #7fa6c2;
  --zd-plate-ink-mid: #7fa6c2;
  --zd-plate-ink-hover: #6d8fb0;
  --zd-plate-btn: #7fa6c2;
  --zd-plate-btn-hover: #6b93af;
  --zd-plate-header-bg: #5b7c99;
  --zd-plate-nav-bg: #4d6b82;
  --zd-plate-btn-bg: #7fa6c2;
  --zd-plate-btn-bg-flat: #7fa6c2;
  --zd-plate-page-bg: #f5f7fa;
  --zd-plate-shadow: rgba(91, 124, 153, 0.22);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body {
  min-height: 100%;
  min-height: 100dvh;
}

body {
  font-family: var(--zd-font);
  background: linear-gradient(165deg, var(--zd-paper) 0%, var(--zd-paper-deep) 100%);
  color: var(--zd-ink);
  /* 适老化：略大于浏览器默认 16px，各页显式 clamp 在此基础上再分层 */
  font-size: clamp(19px, 2.4vw, 22px);
}

/* 整站外框；relative 供内页顶栏 leave 阶段 position:absolute 定位 */
.app {
  position: relative;
  width: 100%;
  max-width: min(1440px, calc(100vw - 20px));
  margin: 10px auto;
  min-height: calc(100vh - 20px);
  min-height: calc(100dvh - 20px);
  padding: 0;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--zd-border);
  border-radius: var(--zd-radius);
  overflow: hidden;
  background: var(--zd-cream);
  box-shadow: var(--zd-shadow);
}

.header {
  flex-shrink: 0;
  background: linear-gradient(135deg, #7c2438 0%, #5c1a2e 55%, #4a1528 100%);
  color: #fdeed8;
  padding: clamp(14px, 2.4vw, 24px) clamp(12px, 2.2vw, 24px);
  text-align: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.header h1 {
  font-size: clamp(30px, 3.8vw, 48px);
  font-weight: 700;
  letter-spacing: 0.16em;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.nav {
  flex-shrink: 0;
  display: flex;
  align-items: stretch;
  min-height: var(--zd-nav-min-h);
  background: var(--zd-nav-bg);
  border-bottom: 1px solid rgba(0, 0, 0, 0.18);
}

.nav-current {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--zd-nav-pad-y) clamp(12px, 1.8vw, 20px);
  font-size: clamp(21px, 2.4vw, 27px);
  font-weight: 600;
  background: transparent;
  color: #fdeed8;
  text-align: center;
  line-height: 1.35;
  letter-spacing: 0.06em;
}

.content {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: clamp(14px, 2.2vw, 32px) clamp(6px, 1.2vw, 10px);
  width: 100%;
  /* 减轻上方顶栏消失 / 内容高度变化时浏览器滚动锚定导致的「整块往上跳」 */
  overflow-anchor: none;
}

/*
 * 勿单独改 max-width：宽屏下若首页用 100vw-20、内页用 min(1440px,…)，返回首页会整站变宽触发重排，明显「卡一下」。
 * 与 .app 同宽即可，首页要「更宽」的视觉已由 HomeView 内卡片宽度控制。
 */
.app--home {
  min-height: calc(100vh - 20px);
  min-height: calc(100dvh - 20px);
  display: flex;
  flex-direction: column;
}

/* 聊天页：去掉整站外框的描边与投影，避免多一层「最外围」线框 */
.app--chat {
  border: none;
  box-shadow: none;
}

/* 防骗训练 / 我的报告：顶栏标题与导航略放大 */
.app--plate-purple .header h1 {
  font-size: clamp(32px, 4vw, 52px);
}

.app--plate-purple .nav-current {
  font-size: clamp(23px, 2.55vw, 29px);
}

/* 板块二、三：主色顶栏 + 略深导航 */
.app--plate-purple .header {
  background: var(--zd-plate-header-bg);
  box-shadow: 0 4px 22px rgba(91, 124, 153, 0.28);
}

.app--plate-purple .nav {
  background: var(--zd-plate-nav-bg);
  border-bottom-color: rgba(40, 60, 75, 0.22);
}

.content-home {
  padding: 0;
  max-width: none;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

/* 内页：减少两侧留白，让防骗训练等模块在宽屏上更居中、更占宽 */
.content-page {
  padding: clamp(12px, 2vw, 26px) clamp(4px, 1vw, 10px);
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

/* 聊天页：主区域不整体滚动，由 ChatView 内消息区滚动，输入框常驻视口内 */
.content-page--chat-fill {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  padding: clamp(8px, 1.4vw, 18px) clamp(4px, 1vw, 10px);
}

@media (max-width: 640px) {
  .nav-current {
    font-size: clamp(19px, 4.4vw, 22px);
    padding-left: 10px;
    padding-right: 10px;
  }

  .app--plate-purple .nav-current {
    font-size: clamp(21px, 4.6vw, 24px);
  }
}

.app-section-chrome {
  flex-shrink: 0;
}

.view-transition-shell {
  position: relative;
  flex: 1;
  min-height: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  background: var(--zd-cream);
  overflow-anchor: none;
}

.view-transition-root {
  flex: 1;
  min-height: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
}
</style>
