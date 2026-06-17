<script setup>
// 하단 테이블: 행 = fab_step × feature × target.
//  - user spec: 사용자가 조합별로 입력한 값
//  - DC spec: feature별 관리값(백엔드 제공)
//  - user/DC range: user spec 범위가 DC spec 범위 대비 몇 %인지
const props = defineProps({
  rows: { type: Array, default: () => [] },
  specFor: { type: Function, default: () => ({}) }, // (xFeature, yTarget) => { lower, upper }
})

function userSpec(r) { return props.specFor(r.x_feature, r.y_target) || {} }
function fmt(v) { return v == null ? '-' : v }

// user 범위 / DC 범위 비율 (%)
function rangeRatio(r) {
  const u = userSpec(r)
  if (u.lower == null || u.upper == null || r.dc_lower == null || r.dc_upper == null) return null
  const dcRange = r.dc_upper - r.dc_lower
  if (!dcRange) return null
  return ((u.upper - u.lower) / dcRange) * 100
}
function ratioText(r) {
  const v = rangeRatio(r)
  return v == null ? '-' : `${v.toFixed(1)}%`
}
</script>

<template>
  <div class="table-wrap">
    <table v-if="rows.length">
      <thead>
        <tr>
          <th>fab_step</th>
          <th>x_feature</th>
          <th>y_target</th>
          <th title="user spec lower">USL</th>
          <th title="user spec upper">USU</th>
          <th title="DC spec lower">DSL</th>
          <th title="DC spec upper">DSU</th>
          <th title="user spec 범위 / DC spec 범위">user/DC range</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(r, i) in rows" :key="i">
          <td>{{ r.fab_step }}</td>
          <td>{{ r.x_feature }}</td>
          <td>{{ r.y_target }}</td>
          <td>{{ fmt(userSpec(r).lower) }}</td>
          <td>{{ fmt(userSpec(r).upper) }}</td>
          <td>{{ fmt(r.dc_lower) }}</td>
          <td>{{ fmt(r.dc_upper) }}</td>
          <td>
            <span v-if="rangeRatio(r) != null" class="ratio"
                  :class="{ over: rangeRatio(r) > 100 }">{{ ratioText(r) }}</span>
            <span v-else>-</span>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">차트를 작성하면 요약 테이블이 표시됩니다.</p>
  </div>
</template>

<style scoped>
.table-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: auto; box-shadow: var(--shadow); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 11px 18px; text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
th {
  background: var(--surface-2); color: var(--text-2); font-weight: 600; position: sticky; top: 0;
  text-transform: uppercase; letter-spacing: 0.03em; font-size: 11px;
}
th[title] { cursor: help; text-decoration: underline dotted rgba(0, 0, 0, 0.25); text-underline-offset: 3px; }
tbody tr:last-child td { border-bottom: none; }
tbody tr { transition: background .12s; }
tbody tr:hover { background: #f5f5f7; }
.ratio { font-weight: 600; color: var(--accent); background: var(--accent-weak); padding: 2px 9px; border-radius: 999px; }
.ratio.over { color: #d70015; background: #ffe5e7; }
.empty { color: #aaa; padding: 32px; text-align: center; font-size: 14px; }
</style>
