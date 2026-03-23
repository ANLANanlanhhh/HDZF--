<template>
  <div class="report-view">
    <div class="controls-bar">
      <button class="back-btn" @click="goBack">⬅ 返回防骗训练</button>
      <button class="export-btn" @click="exportToPDF">📄 下载司法级PDF报告</button>
    </div>

    <div id="pdf-content" class="formal-report">
      <header class="report-header">
        <h1 class="main-title">智盾·个人认知安全评估鉴定书</h1>
        <div class="report-meta">
          <span>鉴定编号：ZD-{{ reportId }}</span>
          <span>生成时间：{{ currentDate }}</span>
        </div>
      </header>

      <div class="doc-source-banner">
        <p class="doc-source-title">依据文档：《防诈意识指标及理论支撑》(1)(1)</p>
        <p class="report-source">
          下方「一、六维鉴定明细」的<strong>维度名称、满分权重、定义与场景</strong>，以及「二、理论依据」的<strong>摘要段落</strong>，均按该 PDF
          整理写入本页；雷达图为根据训练得分折算的参考画像。
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
          <p class="score-dim-sum">六维折算合计：<strong>{{ dimSum }}</strong> / {{ TOTAL_DIM_MAX }} 分</p>
          <div class="risk-badge" :class="riskLevel.class">
            评定等级：{{ riskLevel.label }}
          </div>
        </div>
        <div class="radar-box">
          <div ref="radarChartRef" class="radar-chart"></div>
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
          与 PDF《防诈意识指标及理论支撑》各章对应；正文为便于阅读的浓缩摘要，完整论述请以原 PDF 为准。
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
            ⚠️ 警方提示：未知链接不点击，陌生来电不轻信，个人信息不透露，转账汇款多核实。如遇可疑情况，请立即拨打
            <strong>110</strong> 或全国反诈专线 <strong>96110</strong>！
          </p>
        </div>
      </section>

      <footer class="report-footer">
        <div class="stamp-box">
          <p><strong>智盾反诈研究中心</strong></p>
          <p>（由认知疫苗评估系统自动生成，仅供防范参考）</p>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import * as echarts from 'echarts'
import html2pdf from 'html2pdf.js'

const emit = defineEmits(['go-home'])
const radarChartRef = ref(null)
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

onMounted(() => {
  const savedScore = localStorage.getItem('zhidun_final_score')
  if (savedScore) {
    finalScore.value = parseInt(savedScore, 10)
  }
  dimScores.value = deriveDimScores(finalScore.value)
  initRadarChart()
})

const riskLevel = computed(() => {
  if (finalScore.value >= 80) {
    return {
      class: 'safe',
      label: '抗体已形成',
      adviceTitle: '✅ 状态优良，表现出色！',
      adviceContent:
        '您的防骗意识较强。建议继续参与社区反诈宣传，与家人保持沟通，巩固“遇事核实、转账谨慎”的习惯。'
    }
  }
  if (finalScore.value >= 60) {
    return {
      class: 'warning',
      label: '存在易感风险',
      adviceTitle: '⚠️ 易感预警，防线存在漏洞！',
      adviceContent:
        '面对“政策”“权威”“高回报”话术时易产生动摇。请多与子女或社区民警商量，避免单独做出大额或证件类决定。'
    }
  }
  return {
    class: 'danger',
    label: '高危易骗体质',
    adviceTitle: '🚨 高危干预，极易落入圈套！',
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
  const myChart = echarts.init(radarChartRef.value)
  const values = dimScores.value
  const option = {
    animation: false,
    backgroundColor: '#ffffff',
    tooltip: {},
    radar: {
      indicator: dimensionRows.map((d) => ({
        name: `${d.name}\n(满分${d.max})`,
        max: d.max
      })),
      shape: 'polygon',
      radius: '65%',
      axisName: { color: '#333', fontSize: 13, fontWeight: 'bold' },
      splitArea: { areaStyle: { color: ['#f8f9fa', '#e9ecef'] } },
      axisLine: { lineStyle: { color: '#adb5bd' } },
      splitLine: { lineStyle: { color: '#adb5bd' } }
    },
    series: [
      {
        name: '认知安全画像',
        type: 'radar',
        data: [
          {
            value: values,
            name: '本次折算结果',
            areaStyle: { color: 'rgba(139, 0, 0, 0.2)' },
            lineStyle: { color: '#8b0000', width: 3 },
            itemStyle: { color: '#8b0000' }
          }
        ]
      }
    ]
  }
  myChart.setOption(option)
}

function exportToPDF() {
  const element = document.getElementById('pdf-content')
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
</script>

<style scoped>
.report-view {
  min-height: 100vh;
  background-color: #2b2b2b;
  padding: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.controls-bar {
  width: 100%;
  max-width: 900px;
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.back-btn,
.export-btn {
  padding: 15px 30px;
  font-size: 20px;
  font-weight: bold;
  border-radius: 8px;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.back-btn {
  background: #555;
  color: #fff;
}
.back-btn:hover {
  background: #777;
}

.export-btn {
  background: #8b0000;
  color: #ffd700;
  border: 2px solid #ffd700;
}
.export-btn:hover {
  background: #a50000;
  transform: translateY(-2px);
}

.formal-report {
  background-color: #ffffff;
  color: #000000;
  width: 100%;
  max-width: 900px;
  padding: 50px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  font-family: 'SimSun', 'STSong', serif;
}

.report-header {
  text-align: center;
  border-bottom: 3px solid #8b0000;
  padding-bottom: 20px;
  margin-bottom: 20px;
}

.doc-source-banner {
  margin-bottom: 28px;
  padding: 16px 18px;
  background: linear-gradient(180deg, #fff8e8 0%, #fffef8 100%);
  border: 3px solid #8b0000;
  border-radius: 8px;
}

.doc-source-title {
  font-size: 22px;
  font-weight: bold;
  color: #8b0000;
  margin: 0 0 10px 0;
  letter-spacing: 1px;
}

.report-source {
  font-size: 16px;
  line-height: 1.65;
  color: #333;
  margin: 0;
}

.main-title {
  font-size: 42px;
  color: #8b0000;
  letter-spacing: 4px;
  margin-bottom: 15px;
}

.report-meta {
  display: flex;
  justify-content: space-between;
  color: #666;
  font-size: 18px;
}

.section-title {
  font-size: 28px;
  color: #8b0000;
  border-left: 6px solid #8b0000;
  padding-left: 15px;
  margin-bottom: 20px;
  font-weight: bold;
}

.overview-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 40px;
  gap: 20px;
}

.score-box {
  flex: 1;
  text-align: center;
}

.score-circle {
  width: 180px;
  height: 180px;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: baseline;
  margin: 20px auto;
  border: 8px solid;
}

.score-number {
  font-size: 72px;
  font-weight: bold;
  margin-top: 40px;
}
.score-label {
  font-size: 24px;
}

.score-sub {
  font-size: 18px;
  color: #555;
  margin-bottom: 6px;
}

.score-dim-sum {
  font-size: 17px;
  color: #333;
  margin-bottom: 12px;
}

.risk-badge {
  font-size: 24px;
  font-weight: bold;
  padding: 10px 20px;
  border-radius: 50px;
  display: inline-block;
  color: #fff;
}

.safe {
  border-color: #28a745;
  color: #28a745;
}
.safe.risk-badge {
  background-color: #28a745;
}

.warning {
  border-color: #ffc107;
  color: #d39e00;
}
.warning.risk-badge {
  background-color: #ffc107;
  color: #000;
}

.danger {
  border-color: #dc3545;
  color: #dc3545;
}
.danger.risk-badge {
  background-color: #dc3545;
}

.radar-box {
  flex: 1;
  height: 350px;
}
.radar-chart {
  width: 100%;
  height: 100%;
}

.detail-section {
  margin-bottom: 40px;
}

.dim-max {
  font-size: 14px;
  color: #555;
  font-weight: normal;
}

.analysis-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 17px;
  line-height: 1.5;
}

.analysis-table th,
.analysis-table td {
  border: 1px solid #000;
  padding: 12px;
  text-align: left;
  vertical-align: top;
}

.analysis-table th {
  background-color: #f8f9fa;
  font-weight: bold;
}

.theory-section {
  margin-bottom: 36px;
}

.theory-lead {
  font-size: 17px;
  color: #444;
  margin-bottom: 16px;
}

.theory-card {
  margin-bottom: 16px;
  padding: 14px 16px 16px;
  background: #fafafa;
  border: 1px solid #ccc;
  border-left: 6px solid #8b0000;
}

.theory-h3 {
  font-size: 19px;
  font-weight: bold;
  color: #8b0000;
  margin: 0 0 8px 0;
}

.theory-body {
  margin: 0;
  font-size: 16px;
  line-height: 1.65;
  color: #333;
}

.expert-section {
  margin-bottom: 50px;
}

.advice-box {
  padding: 25px;
  border: 2px solid;
  border-radius: 8px;
  font-size: 20px;
  line-height: 1.8;
  background-color: #fafafa;
}

.advice-box p {
  margin-bottom: 15px;
}
.warning-text {
  color: #8b0000;
  font-weight: bold;
}

.report-footer {
  text-align: right;
  margin-top: 50px;
  padding-top: 20px;
  border-top: 2px dashed #ccc;
}

.stamp-box p {
  font-size: 18px;
  line-height: 1.6;
  color: #555;
}
</style>
