const STORAGE_KEY = 'zhidun_home_stats'

export function loadHomeStats() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const p = JSON.parse(raw)
      return {
        totalTraining: p.totalTraining ?? 0,
        totalScoreSum: p.totalScoreSum ?? 0,
        successCount: p.successCount ?? 0,
        level: p.level ?? 1,
        exp: p.exp ?? 0
      }
    }
  } catch {
    /* ignore */
  }
  return {
    totalTraining: 0,
    totalScoreSum: 0,
    successCount: 0,
    level: 1,
    exp: 0
  }
}

export function getDisplayStats() {
  const s = loadHomeStats()
  const avgScore =
    s.totalTraining > 0 ? Math.round(s.totalScoreSum / s.totalTraining) : 0
  const successRate =
    s.totalTraining > 0
      ? Math.round((s.successCount / s.totalTraining) * 100)
      : 0
  return {
    ...s,
    avgScore,
    successRate
  }
}

export function recordTrainingComplete(score) {
  const n = typeof score === 'number' ? score : 0
  const s = loadHomeStats()
  s.totalTraining++
  s.totalScoreSum += n
  if (n >= 80) s.successCount++
  s.exp += Math.floor(n / 10)
  const expNeeded = s.level * 5
  if (s.exp >= expNeeded) {
    s.level++
    s.exp = 0
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
}

export function getLevelName(level) {
  const lv = level ?? 1
  if (lv <= 2) return '新手训练员'
  if (lv <= 5) return '初级防卫者'
  if (lv <= 10) return '中级守卫'
  if (lv <= 15) return '高级卫士'
  if (lv <= 20) return '防骗专家'
  return '反诈大师'
}
