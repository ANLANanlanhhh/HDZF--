<template>
  <div class="home-landing">
    <div class="home-inner">
      <div class="home-card-toolbar">
        <button
          type="button"
          class="team-info-btn"
          aria-haspopup="dialog"
          :aria-expanded="showTeamModal"
          @click="showTeamModal = true"
        >
          关于我们
        </button>
      </div>

      <div class="logo">
        <div class="logo-title">银龄智盾</div>
        <div class="logo-subtitle">认知疫苗：陪伴 · 免疫 · 评估</div>
      </div>

      <div class="home-actions">
        <button type="button" class="main-button btn-companion" @click="$emit('go-chat')">
          <div class="button-text">
            <div class="btn-title">💬 找小孙聊天</div>
            <div class="button-subtitle">
              <span class="sub-desc">日常陪伴，随时说话</span>
            </div>
          </div>
        </button>

        <button type="button" class="main-button btn-training" @click="$emit('go-training')">
          <div class="button-text">
            <div class="btn-title">🛡️ 防骗训练</div>
            <div class="button-subtitle">
              <span class="sub-desc">主动训练，提升能力</span>
            </div>
          </div>
        </button>

        <button type="button" class="main-button btn-history" @click="$emit('go-report')">
          <div class="button-text">
            <div class="btn-title">📊 我的报告</div>
            <div class="button-subtitle">
              <span class="sub-desc">查看评估与记录</span>
            </div>
          </div>
        </button>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="showTeamModal"
        class="team-overlay"
        role="presentation"
        @click.self="closeTeamModal"
      >
        <div
          class="team-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="team-dialog-title"
        >
          <button type="button" class="team-close" aria-label="关闭" @click="closeTeamModal">
            ×
          </button>
          <h2 id="team-dialog-title" class="team-dialog-title">银龄智盾</h2>
          <p class="team-body">
            {{ teamIntro }}
          </p>
          <p class="team-contact">
            <span class="team-label">联系邮箱</span>
            <span class="team-mail">{{ TEAM_EMAIL }}</span>
          </p>
          <button type="button" class="team-ok" @click="closeTeamModal">知道了</button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

defineEmits(['go-chat', 'go-training', 'go-report'])

const TEAM_EMAIL = '19821807698@163.com'

/** 可改为更口语或更公文表述，见项目说明文档建议 */
const teamIntro = '本系统由“银龄智盾”团队倾情制作，\n愿为长辈多添一份安心❤'

const showTeamModal = ref(false)

function closeTeamModal() {
  showTeamModal.value = false
}

function onDocKeydown(e) {
  if (e.key === 'Escape') closeTeamModal()
}

onMounted(() => document.addEventListener('keydown', onDocKeydown))
onUnmounted(() => document.removeEventListener('keydown', onDocKeydown))
</script>

<style scoped>
/* 整屏居中（类似游戏启动页）：占满主区域并在正中放置卡片 */
.home-landing {
  flex: 1;
  min-height: 0;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: clamp(10px, 2vmin, 20px);
  box-sizing: border-box;
  background: linear-gradient(145deg, var(--zd-paper, #f4f1eb) 0%, var(--zd-paper-deep, #e8e2d8) 100%);
  font-family: var(--zd-font, 'Microsoft YaHei', sans-serif);
}

/* 外层白框：略宽于内容列，两侧留白适中 */
.home-inner {
  position: relative;
  width: 100%;
  max-width: min(560px, calc(100vw - 16px));
  margin: auto;
  background: var(--zd-cream, #fff9f2);
  padding: clamp(20px, 3.2vmin, 34px) clamp(18px, 2.6vmin, 26px);
  border-radius: clamp(16px, 2vw, 22px);
  border: 1px solid var(--zd-border, rgba(74, 60, 48, 0.12));
  box-shadow: var(--zd-shadow, 0 10px 40px rgba(44, 40, 37, 0.08));
  flex-shrink: 0;
  box-sizing: border-box;
}

.home-card-toolbar {
  display: flex;
  justify-content: flex-end;
  margin: -6px 0 10px;
}

.team-info-btn {
  font-size: clamp(20px, 2.4vmin, 26px);
  padding: 10px 20px;
  border-radius: 10px;
  border: 1.5px solid #5f748a;
  background: transparent;
  color: #5f748a;
  cursor: pointer;
  font-weight: 600;
  box-shadow: none;
  transition:
    background 0.2s ease,
    color 0.2s ease,
    border-color 0.2s ease,
    transform 0.15s ease,
    box-shadow 0.2s ease;
}

.team-info-btn:hover {
  background: #5f748a;
  color: #fff;
  border-color: #5f748a;
  box-shadow: 0 4px 14px rgba(95, 116, 138, 0.28);
}

.team-info-btn:active {
  transform: scale(0.98);
}

.team-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  box-sizing: border-box;
}

.team-dialog {
  position: relative;
  width: 100%;
  max-width: min(480px, 100%);
  background: var(--zd-cream, #fff9f2);
  border: 1px solid var(--zd-border, rgba(74, 60, 48, 0.14));
  border-radius: 16px;
  padding: clamp(22px, 4vmin, 32px) clamp(20px, 3vmin, 28px) 24px;
  box-shadow: 0 20px 60px rgba(44, 40, 37, 0.18);
}

.team-close {
  position: absolute;
  top: 10px;
  right: 12px;
  width: 40px;
  height: 40px;
  border: none;
  background: transparent;
  font-size: 40px;
  line-height: 1;
  color: #666;
  cursor: pointer;
  border-radius: 8px;
}

.team-close:hover {
  background: rgba(95, 116, 138, 0.12);
  color: #5f748a;
}

.team-dialog-title {
  margin: 0 36px 14px 0;
  font-size: clamp(28px, 3.6vmin, 38px);
  color: #5f748a;
  letter-spacing: 0.12em;
  font-weight: 700;
}

.team-body {
  margin: 0 0 18px;
  font-size: clamp(22px, 2.7vmin, 27px);
  line-height: 1.65;
  color: #333;
  white-space: pre-line;
}

.team-contact {
  margin: 0 0 20px;
  padding: 14px 16px;
  background: rgba(95, 116, 138, 0.07);
  border-radius: 10px;
  border: 1px solid rgba(95, 116, 138, 0.22);
}

.team-label {
  display: block;
  font-size: 20px;
  color: #666;
  margin-bottom: 6px;
}

.team-mail {
  display: block;
  font-size: clamp(23px, 2.9vmin, 28px);
  font-weight: bold;
  color: var(--zd-ink, #2c2825);
  word-break: break-all;
}

.team-ok {
  width: 100%;
  padding: 16px;
  font-size: clamp(22px, 2.6vmin, 25px);
  font-weight: 600;
  border: 1.5px solid #5f748a;
  border-radius: 999px;
  background: transparent;
  color: #5f748a;
  cursor: pointer;
  box-shadow: none;
  transition:
    background 0.2s ease,
    color 0.2s ease,
    border-color 0.2s ease,
    transform 0.12s ease,
    box-shadow 0.2s ease;
}

.team-ok:hover {
  background: #5f748a;
  color: #fff;
  border-color: #5f748a;
  box-shadow: 0 4px 14px rgba(95, 116, 138, 0.28);
}

.team-ok:active {
  transform: scale(0.99);
}

/* 三枚主按钮纵向排列，宽度收窄、整体居中（接近移动端图二比例） */
.home-actions {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: clamp(10px, 1.6vmin, 14px);
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}

.logo {
  text-align: center;
  margin-bottom: clamp(16px, 2.6vmin, 28px);
}

.logo-title {
  font-size: clamp(40px, 6.2vmin, 72px);
  font-weight: 700;
  color: var(--zd-ink, #2c2825);
  margin-bottom: 12px;
  letter-spacing: 0.12em;
}

.logo-subtitle {
  font-size: clamp(22px, 3.2vmin, 33px);
  color: var(--zd-ink-muted, #5e5852);
  line-height: 1.5;
}

.main-button {
  width: 100%;
  border: none;
  border-radius: clamp(14px, 2vmin, 20px);
  font-weight: bold;
  color: #2c3e50;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  /* 适老化：略大内边距，便于阅读与点击 */
  padding: clamp(14px, 2.4vmin, 20px) clamp(14px, 2.6vmin, 22px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
  text-align: center;
}

.main-button:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.2);
}

.main-button:active {
  transform: translateY(-1px);
}

.btn-companion {
  background: linear-gradient(135deg, #81c784 0%, #66bb6a 100%);
}

.btn-training {
  background: linear-gradient(135deg, #64b5f6 0%, #42a5f5 100%);
}

.btn-history {
  background: linear-gradient(135deg, #ffb74d 0%, #ffa726 100%);
}

.btn-title {
  font-size: clamp(24px, 3.6vmin, 33px);
  line-height: 1.4;
}

.button-text {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
}

.button-subtitle {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  max-width: 100%;
}

.sub-desc {
  font-size: clamp(20px, 2.6vmin, 24px);
  font-weight: 500;
  line-height: 1.5;
  opacity: 0.96;
  text-align: center;
}

.sub-tag {
  font-size: clamp(21px, 2.7vmin, 26px);
  font-weight: 700;
  letter-spacing: 0.03em;
  color: #263238;
  text-align: center;
}
</style>
