/** 训练闯关得分与报告百分制一致，统一限制在 0–100，便于与六维满分 105 的折算对齐 */
export function clampPercentScore(value, fallback = 100) {
  const n = Number(value)
  if (!Number.isFinite(n)) return fallback
  return Math.max(0, Math.min(100, Math.round(n)))
}
