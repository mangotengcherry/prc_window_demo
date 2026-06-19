<script setup>
// 요약 테이블 (M0): 행 = (fab_step × x_feature × y_target). metro 메타 + n + USL/USU/DSL/DSU + user/DC range.
import { cpk as cpkFn, inSpecPct } from '../stats.js'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  specFor: { type: Function, default: () => ({}) }, // (xFeatureKey, yTarget) => { lower, upper }
})

function us(r) { return props.specFor(r.x_feature, r.y_target) || {} }
function fmt(v) { return v == null ? '-' : v }
function ratio(r) {
  const u = us(r)
  if (u.lower == null || u.upper == null || r.dc_lower == null || r.dc_upper == null) return null
  const d = r.dc_upper - r.dc_lower
  return d ? ((u.upper - u.lower) / d) * 100 : null
}
// feature 공정능력 — Cpk(단기 σ=x_std_within) / Ppk(전체 σ=x_std), user/DC spec 기준
function cpkU(r) { const u = us(r); return cpkFn(r.x_value, r.x_std_within, u.lower, u.upper) }
function ppkU(r) { const u = us(r); return cpkFn(r.x_value, r.x_std, u.lower, u.upper) }
function cpkDc(r) { return cpkFn(r.x_value, r.x_std_within, r.dc_lower, r.dc_upper) }
function ppkDc(r) { return cpkFn(r.x_value, r.x_std, r.dc_lower, r.dc_upper) }
function inspecU(r) { const u = us(r); return inSpecPct(r.x_value, r.x_std, u.lower, u.upper) }
function cpkClass(v) { return v == null ? '' : (v < 1 ? 'bad' : (v < 1.33 ? 'warn' : 'good')) }
</script>

<template>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>fab_step</th>
          <th title="metro_step · metro_item / subitem">x_feature</th>
          <th>y_target</th>
          <th title="관측 표본수">n</th>
          <th title="user spec lower">USL</th>
          <th title="user spec upper">USU</th>
          <th title="DC spec lower">DSL</th>
          <th title="DC spec upper">DSU</th>
          <th title="user spec 범위 / DC spec 범위 = (USU−USL)/(DSU−DSL)">SPEC(USER/DC)</th>
          <th title="user spec 안에 든 데이터 비율 (정규근사)">SPEC-IN(USER)*</th>
          <th title="Cpk (user spec, 단기 σ=MR/1.128)">Cpk(u)</th>
          <th title="Ppk (user spec, 전체 σ)">Ppk(u)</th>
          <th title="Cpk (DC spec, 단기 σ) — user 입력 불필요">Cpk(DC)</th>
          <th title="Ppk (DC spec, 전체 σ)">Ppk(DC)</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(r, i) in rows" :key="i">
          <td>{{ r.fab_step }}</td>
          <td :title="r.x_feature"><span class="ms">{{ r.metro_step }}</span> · {{ r.x_feature_display_name }}</td>
          <td>{{ r.y_target }}</td>
          <td>{{ fmt(r.n) }}</td>
          <td>{{ fmt(us(r).lower) }}</td>
          <td>{{ fmt(us(r).upper) }}</td>
          <td>{{ fmt(r.dc_lower) }}</td>
          <td>{{ fmt(r.dc_upper) }}</td>
          <td><span v-if="ratio(r) != null" class="ratio" :class="{ over: ratio(r) > 100 }">{{ ratio(r).toFixed(1) }}%</span><span v-else>-</span></td>
          <td>{{ inspecU(r) == null ? '-' : (inspecU(r) * 100).toFixed(1) + '%' }}</td>
          <td><span v-if="cpkU(r) != null" class="cpk" :class="cpkClass(cpkU(r))">{{ cpkU(r).toFixed(2) }}</span><span v-else>-</span></td>
          <td><span v-if="ppkU(r) != null" class="cpk" :class="cpkClass(ppkU(r))">{{ ppkU(r).toFixed(2) }}</span><span v-else>-</span></td>
          <td><span v-if="cpkDc(r) != null" class="cpk" :class="cpkClass(cpkDc(r))">{{ cpkDc(r).toFixed(2) }}</span><span v-else>-</span></td>
          <td><span v-if="ppkDc(r) != null" class="cpk" :class="cpkClass(ppkDc(r))">{{ ppkDc(r).toFixed(2) }}</span><span v-else>-</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: auto; box-shadow: var(--shadow); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
th { background: var(--surface-2); color: var(--text-2); font-weight: 600; position: sticky; top: 0; text-transform: uppercase; letter-spacing: .03em; font-size: 11px; }
th[title] { cursor: help; text-decoration: underline dotted rgba(0,0,0,.25); text-underline-offset: 3px; }
.ms { color: var(--text-2); }
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: #f5f5f7; }
.ratio { font-weight: 600; color: var(--accent); background: var(--accent-weak); padding: 2px 9px; border-radius: 999px; }
.ratio.over { color: #d70015; background: #ffe5e7; }
.cpk { font-weight: 700; padding: 2px 9px; border-radius: 999px; }
.cpk.good { color: #166534; background: #dcfce7; }
.cpk.warn { color: #854d0e; background: #fef9c3; }
.cpk.bad { color: #991b1b; background: #fee2e2; }
</style>
