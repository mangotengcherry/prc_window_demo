// 경량 통계 유틸 — feature 분포(mean/std) + user spec으로 즉시 계산(라운드트립 없음).
// in-spec%는 정규근사(분포가 정규라는 가정). 표시 시 '근사' 라벨을 붙인다.

function erf(x) {
  const t = 1 / (1 + 0.3275911 * Math.abs(x))
  const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x)
  return x >= 0 ? y : -y
}
export function normCdf(z) { return 0.5 * (1 + erf(z / Math.SQRT2)) }

// Cpk = min(USU-μ, μ-USL) / (3σ)  — feature 공정능력
export function cpk(mean, std, lower, upper) {
  if (mean == null || std == null || std <= 0 || lower == null || upper == null) return null
  return Math.min(upper - mean, mean - lower) / (3 * std)
}

// in-spec 비율(정규근사). 0~1
export function inSpecPct(mean, std, lower, upper) {
  if (mean == null || std == null || std <= 0 || lower == null || upper == null) return null
  return normCdf((upper - mean) / std) - normCdf((lower - mean) / std)
}
