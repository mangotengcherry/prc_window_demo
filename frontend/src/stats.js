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

// Cpk/Ppk 종합 진단 — 능력 수준 × 안정성(σ_overall/σ_within) × 중심(Cp 대비).
//  핵심: Cpk/Ppk = σ_overall/σ_within → 1보다 벌어지면 군간 변동(drift) 큼.
//        Cp(중심 무시 잠재능력)는 좋은데 Cpk 낮으면 → 치우침(재센터링).
// 반환: { cpk, ppk, cp, ratio, unstable, offcenter, state, label, msg } | null
export function capabilityDiagnosis(mean, sWithin, sOverall, lower, upper) {
  if (mean == null || sWithin == null || sOverall == null || lower == null || upper == null) return null
  if (sWithin <= 0 || sOverall <= 0 || upper <= lower) return null
  const margin = Math.min(upper - mean, mean - lower)
  const cpkV = margin / (3 * sWithin)
  const ppkV = margin / (3 * sOverall)
  const cp = (upper - lower) / (6 * sWithin)                 // 잠재능력(중심 무시)
  const half = (upper - lower) / 2
  const off = Math.abs(mean - (upper + lower) / 2) / half    // 0 중심 ~ 1 한계
  const ratio = cpkV / ppkV                                  // = σ_overall/σ_within (≥1 일반)
  const unstable = ratio >= 1.3                              // 장기 산포가 단기 대비 30%+ ↑
  const offcenter = off >= 0.25 && cp >= 1.33                // 산포는 충분한데 치우침
  const worst = Math.min(cpkV, ppkV)
  const r1 = ratio.toFixed(1), cpkS = cpkV.toFixed(2), ppkS = ppkV.toFixed(2)
  let state, label, msg
  // drift(단기 능력은 충분한데 장기 산포가 커 Ppk가 떨어짐)를 먼저 판정 — Ppk<1.0이어도 능력부족이 아니라 drift
  if (unstable && cpkV >= 1.33 && ppkV < 1.33) {
    state = 'drift'; label = 'drift 의심'
    msg = `단기 능력은 충분(Cpk ${cpkS})하나 장기 산포가 큼(σ_overall≈${r1}×σ_within, Ppk ${ppkS}) → data drift/시프트 의심. 안정화·SPC 강화.`
  } else if (worst < 1.0) {
    if (offcenter) {
      state = 'offcenter'; label = '중심 치우침'
      msg = `산포는 충분(Cp ${cp.toFixed(2)})하나 중심이 한계로 치우침 → 재센터링하면 Cpk 개선.`
    } else {
      state = 'incapable'; label = '능력 부족'
      msg = `spec 대비 능력 부족(Cpk ${cpkS}·Ppk ${ppkS})` + (unstable
        ? ` + 장기 불안정(σ_overall≈${r1}×σ_within) → 안정화 후 산포 저감/spec 재검토.`
        : ` (안정적) → spec 적정성 재검토 또는 산포 저감.`)
    }
  } else if (worst >= 2.0) {
    state = 'over'; label = '과잉(여유)'
    msg = `Cpk ${cpkS}·Ppk ${ppkS} 모두 높음 → spec 여유 큼. spec 타이트닝(조기 검출) 또는 관리 완화 검토.`
  } else if (worst < 1.33) {
    state = 'marginal'; label = '능력 경계'
    msg = `Cpk ${cpkS}·Ppk ${ppkS} 경계 → 산포/센터 개선으로 마진 확보.` + (offcenter ? ' 중심 치우침 존재.' : '')
  } else {
    state = 'ok'; label = '양호'
    msg = `안정·능력 충분(Cpk ${cpkS}·Ppk ${ppkS}).` + (unstable ? ` 단 장기 산포 다소 큼(${r1}×).` : ' 현 수준 유지.')
  }
  return { cpk: cpkV, ppk: ppkV, cp, ratio, unstable, offcenter, state, label, msg }
}
