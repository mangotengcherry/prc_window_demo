// 분석 조건 ↔ URL 직렬화 + 쿼리 식별자. 같은 링크로 같은 화면 재현(provenance·J).

// 조건(cond=차트 작성 요청 payload)을 URL-safe 문자열로. 한글 포함 → encodeURIComponent 후 btoa.
export function encodeCond(cond) {
  try {
    return btoa(encodeURIComponent(JSON.stringify(cond)))
  } catch {
    return ''
  }
}

export function decodeCond(s) {
  try {
    return JSON.parse(decodeURIComponent(atob(s)))
  } catch {
    return null
  }
}

// 결정적 짧은 쿼리 ID (FNV-1a 32bit → base36). 같은 조건 → 같은 ID.
export function queryId(cond) {
  const str = JSON.stringify(cond)
  let h = 0x811c9dc5
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i)
    h = Math.imul(h, 0x01000193)
  }
  return (h >>> 0).toString(36).padStart(7, '0').slice(0, 7)
}

// 현재 페이지 기준 공유 URL
export function shareUrl(cond) {
  const q = encodeCond(cond)
  return `${location.origin}${location.pathname}?q=${q}`
}

// 현재 URL에서 조건 복원(없으면 null)
export function condFromUrl() {
  const q = new URLSearchParams(location.search).get('q')
  return q ? decodeCond(q) : null
}
