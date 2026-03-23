<template>
  <div class="app">
    <header class="header">
      <h1>智盾·认知疫苗</h1>
    </header>

    <nav class="nav">
      <button @click="currentView = 'chat'" :class="{ active: currentView === 'chat' }">
        找小孙聊天
      </button>
      <button @click="currentView = 'training'" :class="{ active: currentView === 'training' }">
        防骗训练
      </button>
      <button @click="currentView = 'report'" :class="{ active: currentView === 'report' }">
        我的报告
      </button>
    </nav>

    <main class="content">
      <ChatView v-if="currentView === 'chat'" />
      
      <TrainingView 
        v-if="currentView === 'training'" 
        @view-report="currentView = 'report'" 
      />
      
      <ReportView 
        v-if="currentView === 'report'" 
        @go-home="currentView = 'training'" 
      />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ChatView from './components/ChatView.vue'
import TrainingView from './components/TrainingView.vue'
import ReportView from './components/ReportView.vue'

const currentView = ref('chat')
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: "SimSun", "宋体", serif;
  background: #f5f5dc;
  color: #000;
}

.app {
  max-width: 800px;
  margin: 0 auto;
  min-height: 100vh;
}

.header {
  background: #8b0000;
  color: #ffd700;
  padding: 40px 20px;
  text-align: center;
  border-bottom: 8px solid #000;
}

.header h1 {
  font-size: 48px;
  font-weight: bold;
  letter-spacing: 8px;
}

.nav {
  display: flex;
  background: #2f4f4f;
  border-bottom: 4px solid #000;
}

.nav button {
  flex: 1;
  padding: 30px;
  font-size: 32px;
  font-weight: bold;
  background: #2f4f4f;
  color: #fff;
  border: none;
  border-right: 2px solid #000;
  cursor: pointer;
}

.nav button:last-child {
  border-right: none;
}

.nav button.active {
  background: #8b0000;
  color: #ffd700;
}

.content {
  padding: 40px 20px;
  min-height: 600px;
}
</style>