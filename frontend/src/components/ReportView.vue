<template>
  <div class="report-view">
    <!-- 全宽一行：左「返回主页」与右全文/下载同一水平线；左右与 .report-view 对称 padding 对齐 -->
    <div class="report-top-bar">
      <button type="button" class="btn-back-home" @click="goBack">返回主页</button>
      <div class="report-doc-actions">
        <button type="button" class="theory-pdf-btn" @click="openTheoryPdf">
          查看《防诈意识指标及理论支撑》全文
        </button>
        <button type="button" class="export-btn" @click="exportToPDF">下载</button>
      </div>
    </div>

    <div id="pdf-content" class="formal-report">
      <header class="report-header">
        <h1 class="main-title">智盾·个人认知安全评估鉴定书</h1>
        <div class="report-meta">
          <span>生成时间：{{ currentDate }}</span>
        </div>
      </header>

      <div class="doc-source-banner">
        <p class="doc-source-title">依据文档：《防诈意识指标及理论支撑》</p>
        <p class="report-source">
          下方“六维认知防线鉴定明细”的<strong>维度名称、满分权重、定义与场景</strong>，以及“指标内涵与理论依据（摘要）”的<strong>摘要段落</strong>，均按《防诈意识指标及理论支撑》整理写入本页；雷达图为根据训练得分折算的参考画像。
        </p>
      </div>

      <section class="overview-section">
        <div class="score-box">
          <h2 class="section-title">综合免疫力评级</h2>
          <div class="score-circle" :class="riskLevel.class">
            <span class="score-number">{{ finalScore }}</span>
            <span class="score-label">分</span>
          </div>
          <p class="score-sub">训练闯关得分（百分制）</p>
          <p class="risk-level-plain" :class="riskLevel.class">
            评定等级：{{ riskLevel.label }}
          </p>
        </div>
        <div class="radar-box">
          <div ref="radarChartRef" class="radar-chart"></div>
          <p class="score-dim-sum">
            六维折算合计：<strong>{{ dimSum }}</strong> / {{ TOTAL_DIM_MAX }} 分
          </p>
        </div>
      </section>

      <section class="detail-section">
        <h2 class="section-title">一、六维认知防线鉴定明细</h2>
        <table class="analysis-table">
          <thead>
            <tr>
              <th width="14%">评估维度（满分）</th>
              <th width="40%">定义与核心防范场景</th>
              <th width="46%">系统鉴定结果</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in dimensionRows" :key="row.key">
              <td>
                <strong>{{ row.name }}</strong><br />
                <span class="dim-max">（满分 {{ row.max }}）</span>
              </td>
              <td>{{ row.definition }} {{ row.scenario }}</td>
              <td>{{ getComment(row.key) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="theory-section">
        <h2 class="section-title">二、指标内涵与理论依据（摘要）</h2>
        <p class="theory-lead">
          与《防诈意识指标及理论支撑》各章对应；正文为便于阅读的浓缩摘要，完整论述请以《防诈意识指标及理论支撑》为准。
        </p>
        <div v-for="block in theoryBlocks" :key="block.title" class="theory-card">
          <h3 class="theory-h3">{{ block.title }}</h3>
          <p class="theory-body">{{ block.body }}</p>
        </div>
      </section>

      <section class="expert-section">
        <h2 class="section-title">三、专家干预建议</h2>
        <div class="advice-box" :class="riskLevel.class">
          <p><strong>{{ riskLevel.adviceTitle }}</strong></p>
          <p>{{ riskLevel.adviceContent }}</p>
          <p class="warning-text">
            警方提示：未知链接不点击，陌生来电不轻信，个人信息不透露，转账汇款多核实。如遇可疑情况，请立即拨打
            <strong>110</strong> 或全国反诈专线 <strong>96110</strong>！
          </p>
        </div>
      </section>

      <footer class="report-footer">
        <div class="stamp-box">
          <p><strong>“银龄智盾”项目团队</strong></p>
          <p>（本报告由“银龄智盾”系统依据训练与演练数据自动生成，仅供个人防范参考）</p>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import { clampPercentScore } from '../utils/trainingScore.js'

const emit = defineEmits(['go-home'])
const radarChartRef = ref(null)
const radarChartInst = ref(null)
let radarResizeObserver = null
const finalScore = ref(100)

const TOTAL_DIM_MAX = 105

const reportId = ref(Math.random().toString(36).substr(2, 9).toUpperCase())
const currentDate = ref(new Date().toLocaleDateString('zh-CN'))

/** 与《防诈意识指标及理论支撑》一致的顺序与满分 */
const dimensionRows = [
  {
    key: 'info',
    name: '信息甄别能力',
    max: 25,
    definition: '对虚假信息的识别能力，涵盖逻辑漏洞、信息来源可信度及诈骗话术判断。',
    scenario:
      '核心场景：识别“区块链理财”“免费旅游”“多级分销返利”等话术；对陌生短信链接、可疑广告保持核查习惯。'
  },
  {
    key: 'greed',
    name: '贪利防御值',
    max: 20,
    definition: '对高收益诱惑的抵抗力，反映利益驱动下的风险规避倾向。',
    scenario:
      '核心场景：抵制“保本高息”“养老理财”“内部渠道”“政策扶持”等话术，了解 e 租宝、养老公寓投资等典型案例。'
  },
  {
    key: 'panic',
    name: '恐慌阈值',
    max: 15,
    definition: '面对突发诈骗威胁时的情绪稳定性；高阈值者能冷静分析，低阈值者易冲动决策。',
    scenario:
      '核心场景：遇“账户冻结需紧急转账”等恐吓时，能否先联系银行、家属或警方，而非立即转账。'
  },
  {
    key: 'authority',
    name: '权威祛魅力',
    max: 15,
    definition: '对所谓专家、公职人员等权威符号的盲目信任程度；高祛魅者能区分专业性与商业推销。',
    scenario:
      '核心场景：核查“白大褂”“警服”“领导”等身份真伪，质疑与商业利益绑定的“权威推荐”。'
  },
  {
    key: 'emotion',
    name: '情感独立性',
    max: 15,
    definition: '决策受孤独、焦虑等情感影响的程度；高独立性者能区分情感需求与事实风险。',
    scenario:
      '核心场景：防范“黄昏恋”“嘘寒问暖”“孝心工程”等情感裹挟与杀猪盘。'
  },
  {
    key: 'legal',
    name: '法治逻辑',
    max: 15,
    definition: '对法律规则与维权途径的理解，包括对诈骗罪构成、证据与《反电信网络诈骗法》等的认知。',
    scenario:
      '核心场景：知晓公检法不存在“安全账户”、不电话办案；重视电子证据与正规报案渠道。'
  }
]

const theoryBlocks = [
  {
    title: '一、信息甄别能力',
    body:
      '双加工理论：直觉系统与分析系统并存，老年人更易依赖直觉而忽略核查来源。认知负荷理论：信息嵌套过多时决策质量下降，适老化多模态呈现有助于减负。'
  },
  {
    title: '二、贪利防御值',
    body:
      '前景理论：损失厌恶使“保本高息”话术更易奏效。自我决定理论：部分老年人通过高风险投资寻求自主感，需结合认知重构与动机引导建立风险意识。'
  },
  {
    title: '三、恐慌阈值',
    body:
      '情绪调节与认知重评可降低威胁解读；压力应对模型强调问题导向应对需社会支持，家庭与社区陪伴有助于减少情绪导向的盲目转账。'
  },
  {
    title: '四、权威祛魅力',
    body:
      '米尔格拉姆实验揭示权威符号的服从效应；社会认知理论强调元认知提问，把注意力从“身份”转向“事实与利益关联”。'
  },
  {
    title: '五、情感独立性',
    body:
      '依恋理论解释情感空虚与“暖心关怀型诈骗”的匹配关系；情感智力理论提倡情绪标记与情绪日记，建立“情感需求≠事实”的惯性。'
  },
  {
    title: '六、法治逻辑',
    body:
      '法律认知理论强调把抽象条文符号化为可记忆的行为规则；规则内化理论指出体验化普法（如模拟法庭）有助于将守法转化为内在认同。'
  }
]

const dimScores = ref([0, 0, 0, 0, 0, 0])

const dimSum = computed(() => dimScores.value.reduce((a, b) => a + b, 0))

function deriveDimScores(fs) {
  const t = Math.max(0, Math.min(100, fs)) / 100
  const maxes = [25, 20, 15, 15, 15, 15]
  const seeds = [0.95, 1.02, 0.98, 1.0, 0.96, 1.04]
  return maxes.map((m, i) => Math.min(m, Math.max(0, Math.round(m * t * seeds[i]))))
}

function handleRadarResize() {
  radarChartInst.value?.resize()
}

onMounted(async () => {
  const savedScore = localStorage.getItem('zhidun_final_score')
  if (savedScore !== null && savedScore !== '') {
    finalScore.value = clampPercentScore(parseInt(savedScore, 10), 100)
  }
  dimScores.value = deriveDimScores(finalScore.value)
  await nextTick()
  initRadarChart()
  window.addEventListener('resize', handleRadarResize)
  const el = radarChartRef.value
  if (el && typeof ResizeObserver !== 'undefined') {
    radarResizeObserver = new ResizeObserver(handleRadarResize)
    radarResizeObserver.observe(el)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleRadarResize)
  radarResizeObserver?.disconnect()
  radarResizeObserver = null
  radarChartInst.value?.dispose()
  radarChartInst.value = null
})

const riskLevel = computed(() => {
  if (finalScore.value >= 80) {
    return {
      class: 'safe',
      label: '抗体已形成',
      adviceTitle: '状态优良，表现出色！',
      adviceContent:
        '您的防骗意识较强。建议继续参与社区反诈宣传，与家人保持沟通，巩固“遇事核实、转账谨慎”的习惯。'
    }
  }
  if (finalScore.value >= 60) {
    return {
      class: 'warning',
      label: '存在易感风险',
      adviceTitle: '易感预警，防线存在漏洞！',
      adviceContent:
        '面对“政策”“权威”“高回报”话术时易产生动摇。请多与子女或社区民警商量，避免单独做出大额或证件类决定。'
    }
  }
  return {
    class: 'danger',
    label: '高危易骗体质',
    adviceTitle: '高危干预，极易落入圈套！',
    adviceContent:
      '在恐慌或情感攻势下易失去冷静。请将本报告分享给家人，安装“国家反诈中心”APP，并保存社区与民警联系方式。'
  }
})

function getComment(key) {
  const score = finalScore.value
  const good = score >= 80
  const C = {
    info: {
      t: good
        ? '表现较好：能关注信息来源与典型话术，对陌生链接保持警惕。'
        : '需加强：对非官方渠道与复杂返利逻辑辨别不足，易误点可疑信息。'
    },
    greed: {
      t: good
        ? '表现较好：对“高息保本”等诱惑保持克制，能联想到常见集资风险。'
        : '需加强：易被高回报、限时优惠驱动，需警惕庞氏与养老投资骗局。'
    },
    panic: {
      t: good
        ? '表现较好：遇恐吓类话术能先冷静，倾向向家人或警方核实。'
        : '需加强：突发事件下易被操控情绪，需练习“先挂断、再核实”的步骤。'
    },
    authority: {
      t: good
        ? '表现较好：对“专家”“公职”身份会存疑并愿意核实。'
        : '需加强：易被制服、头衔误导，需养成查证资质与利益关联的习惯。'
    },
    emotion: {
      t: good
        ? '表现较好：能区分关怀与推销，对过度热情保持戒心。'
        : '需加强：情感需求易被利用，需以真实亲情与社交填补孤独感。'
    },
    legal: {
      t: good
        ? '表现较好：具备基本法治与证据意识，知晓正规维权路径。'
        : '需加强：对新型网络违法与电子证据了解不足，需补强普法与报案流程。'
    }
  }
  return C[key].t
}

function initRadarChart() {
  const el = radarChartRef.value
  if (!el) return
  radarChartInst.value?.dispose()
  radarChartInst.value = null
  const myChart = echarts.init(el)
  radarChartInst.value = myChart
  const values = dimScores.value
  const option = {
    animation: false,
    backgroundColor: '#ffffff',
    tooltip: {},
    radar: {
      // 略下移、略缩小半径，为四周轴名称（尤其正上方两行字）留出画布空间，避免裁切
      center: ['50%', '55%'],
      radius: '52%',
      nameGap: 14,
      indicator: dimensionRows.map((d) => ({
        name: `${d.name}\n(满分${d.max})`,
        max: d.max
      })),
      shape: 'polygon',
      axisName: {
        color: '#475569',
        fontSize: 15,
        fontWeight: '600',
        lineHeight: 20
      },
      splitArea: { areaStyle: { color: ['#f8fafc', '#f1f5f9'] } },
      axisLine: { lineStyle: { color: '#b8cfe0' } },
      splitLine: { lineStyle: { color: '#e2ebf2' } }
    },
    series: [
      {
        name: '认知安全画像',
        type: 'radar',
        data: [
          {
            value: values,
            name: '本次折算结果',
            areaStyle: { color: 'rgba(127, 166, 194, 0.28)' },
            lineStyle: { color: '#7fa6c2', width: 2 },
            itemStyle: { color: '#7fa6c2' }
          }
        ]
      }
    ]
  }
  myChart.setOption(option)
  requestAnimationFrame(() => myChart.resize())
}

async function exportToPDF() {
  const element = document.getElementById('pdf-content')
  if (!element) return
  const { default: html2pdf } = await import('html2pdf.js')
  const opt = {
    margin: [15, 15, 15, 15],
    filename: `智盾防骗评估报告_${reportId.value}.pdf`,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
  }
  html2pdf().set(opt).from(element).save()
}

function goBack() {
  emit('go-home')
}

/** 在新标签页打开依据文档 PDF（文件位于 public/，随前端静态资源部署） */
function openTheoryPdf() {
  const base = import.meta.env.BASE_URL || '/'
  const prefix = base.endsWith('/') ? base : `${base}/`
  window.open(`${prefix}防诈意识指标及理论支撑.pdf`, '_blank', 'noopener,noreferrer')
}
</script>

<style scoped>
/* 外层与 TrainingView .training-view 一致；白框宽度与全局 --zd-content-card-max 一致 */
.report-view {
  --zd-burgundy: var(--zd-plate-ink, #5b7c99);
  min-height: 100vh;
  min-height: 100dvh;
  width: 100%;
  max-width: min(1280px, 100%);
  margin: 0 auto;
  box-sizing: border-box;
  background: var(--zd-plate-page-bg, #f5f7fa);
  /* 与 TrainingView .training-view 同 padding，保证「返回主页」与板块二左上角对齐 */
  padding: clamp(14px, 2.2vw, 28px) clamp(12px, 2.2vw, 32px);
  font-family: var(--zd-font, 'Microsoft YaHei', sans-serif);
}

/* 全宽顶栏（与板块二 .selector-toolbar 一致），勿再 max-width 居中，否则按钮会随白卡内收 */
.report-top-bar {
  width: 100%;
  margin: 0 0 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  box-sizing: border-box;
}

.report-doc-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-back-home {
  padding: 10px 20px;
  font-size: clamp(18px, 1.8vw, 21px);
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

.export-btn,
.theory-pdf-btn {
  padding: 10px 16px;
  min-height: 52px;
  font-size: clamp(17px, 1.7vw, 20px);
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

.export-btn:hover,
.theory-pdf-btn:hover {
  background: var(--zd-plate-btn-hover, #6b93af);
  transform: translateY(-2px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.32),
    0 6px 18px rgba(127, 166, 194, 0.42),
    0 3px 8px rgba(80, 52, 12, 0.11);
}

.export-btn:active,
.theory-pdf-btn:active {
  transform: translateY(0) scale(0.98);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.18),
    0 2px 8px rgba(127, 166, 194, 0.32),
    0 1px 3px rgba(80, 52, 12, 0.08);
}

.formal-report {
  background-color: var(--zd-surface, #fff);
  color: var(--zd-ink, #2c2825);
  width: 100%;
  max-width: var(--zd-content-card-max, min(1000px, 100%));
  margin: 0 auto;
  padding: clamp(28px, 4.5vw, 42px);
  /* 描边与训练页分类卡一致；max-width 见 :root --zd-content-card-max */
  border: 1px solid rgba(127, 166, 194, 0.4);
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(91, 124, 153, 0.08);
  font-family: var(--zd-font, 'Microsoft YaHei', 'SimSun', serif);
}

.report-header {
  text-align: center;
  border-bottom: 1px solid rgba(127, 166, 194, 0.45);
  padding-bottom: 14px;
  margin-bottom: 16px;
}

.doc-source-banner {
  margin-bottom: 20px;
  padding: 14px 16px;
  background: linear-gradient(180deg, #fff9f2 0%, #fff 100%);
  border: 1px solid rgba(184, 149, 47, 0.35);
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(44, 40, 37, 0.05);
}

.doc-source-title {
  font-size: clamp(20px, 2.25vw, 23px);
  font-weight: 700;
  color: var(--zd-burgundy, #5b7c99);
  margin: 0 0 8px 0;
  letter-spacing: 0.04em;
}

.report-source {
  font-size: clamp(18px, 2vw, 20px);
  line-height: 1.65;
  color: var(--zd-ink-muted, #5e5852);
  margin: 0;
}

.main-title {
  font-size: clamp(28px, 4.4vw, 37px);
  font-weight: 700;
  color: var(--zd-burgundy, #5b7c99);
  letter-spacing: 0.08em;
  margin-bottom: 10px;
}

.report-meta {
  display: flex;
  justify-content: center;
  color: #64748b;
  font-size: clamp(18px, 1.95vw, 20px);
}

.section-title {
  font-size: clamp(23px, 2.55vw, 26px);
  font-weight: 700;
  color: var(--zd-burgundy, #5b7c99);
  border-left: 4px solid var(--zd-burgundy, #5b7c99);
  padding-left: 12px;
  margin-bottom: 14px;
}

.overview-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
  gap: 16px;
}

.score-box {
  flex: 1;
  text-align: center;
}

.score-circle {
  width: clamp(150px, 38vw, 170px);
  height: clamp(150px, 38vw, 170px);
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: baseline;
  margin: 14px auto;
  border: 6px solid;
}

.score-number {
  font-size: clamp(52px, 12.5vw, 62px);
  font-weight: bold;
  margin-top: 28px;
}
.score-label {
  font-size: clamp(21px, 2.35vw, 24px);
}

.score-sub {
  font-size: clamp(17px, 1.9vw, 19px);
  color: #555;
  margin-bottom: 4px;
}

/* 评定等级：仅文字着色，不再使用左侧实心色条（原 .risk-badge） */
.risk-level-plain {
  font-size: clamp(18px, 2vw, 21px);
  font-weight: 600;
  margin: 10px 0 0;
  line-height: 1.4;
}

.risk-level-plain.safe {
  color: #15803d;
}

.risk-level-plain.warning {
  color: #b45309;
}

.risk-level-plain.danger {
  color: #b91c1c;
}

.safe {
  border-color: #28a745;
  color: #28a745;
}

.warning {
  border-color: #ffc107;
  color: #d39e00;
}

.danger {
  border-color: #dc3545;
  color: #dc3545;
}

.radar-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
  min-height: 300px;
  /* 为雷达图顶部轴标签预留空隙，避免被父级裁切 */
  padding-top: 10px;
  box-sizing: border-box;
}

.radar-chart {
  width: 100%;
  flex: 1;
  min-height: 320px;
  /* 给 ECharts 画布足够高度，六维标签（两行）才能完整绘制 */
  min-width: 220px;
  box-sizing: border-box;
}

.score-dim-sum {
  font-size: clamp(17px, 1.9vw, 19px);
  color: #333;
  margin: 12px 0 0;
  text-align: center;
  width: 100%;
  line-height: 1.5;
}

.detail-section {
  margin-bottom: 28px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.dim-max {
  font-size: clamp(16px, 1.7vw, 18px);
  color: #555;
  font-weight: normal;
}

.analysis-table {
  width: 100%;
  border-collapse: collapse;
  font-size: clamp(17px, 1.9vw, 19px);
  line-height: 1.5;
}

.analysis-table th,
.analysis-table td {
  border: 1px solid #e2e8f0;
  padding: 10px 12px;
  text-align: left;
  vertical-align: top;
}

.analysis-table th {
  background-color: #f1f5f9;
  font-weight: 700;
  color: var(--zd-ink-muted, #5e5852);
}

.theory-section {
  margin-bottom: 36px;
}

.theory-lead {
  font-size: clamp(18px, 2vw, 20px);
  color: #444;
  margin-bottom: 12px;
}

.theory-card {
  margin-bottom: 12px;
  padding: 12px 14px;
  background: rgba(127, 166, 194, 0.08);
  border: 1px solid rgba(127, 166, 194, 0.35);
  border-left: 4px solid var(--zd-plate-card, #7fa6c2);
  border-radius: 0 8px 8px 0;
}

.theory-h3 {
  font-size: clamp(19px, 2.15vw, 22px);
  font-weight: 700;
  color: var(--zd-burgundy, #5b7c99);
  margin: 0 0 6px 0;
}

.theory-body {
  margin: 0;
  font-size: clamp(17px, 1.9vw, 19px);
  line-height: 1.65;
  color: #333;
}

.expert-section {
  margin-bottom: 36px;
}

.advice-box {
  padding: 20px;
  border: 1px solid var(--zd-border, rgba(74, 60, 48, 0.14));
  border-radius: 10px;
  font-size: clamp(18px, 2vw, 21px);
  line-height: 1.65;
  background: #fafaf9;
}

.advice-box.safe {
  border-color: rgba(22, 101, 52, 0.35);
  background: linear-gradient(180deg, #f0fdf4 0%, #fafafa 100%);
}

.advice-box.warning {
  border-color: rgba(180, 130, 0, 0.4);
  background: linear-gradient(180deg, #fffbeb 0%, #fafafa 100%);
}

.advice-box.danger {
  border-color: rgba(185, 28, 28, 0.38);
  background: linear-gradient(180deg, #fef2f2 0%, #fafafa 100%);
}

.advice-box p {
  margin-bottom: 15px;
}
.warning-text {
  color: var(--zd-burgundy, #5b7c99);
  font-weight: 700;
}

.report-footer {
  text-align: right;
  margin-top: 36px;
  padding-top: 16px;
  border-top: 1px dashed #cbd5e1;
}

.stamp-box p {
  font-size: clamp(17px, 1.9vw, 19px);
  line-height: 1.55;
  color: #555;
}
</style>
