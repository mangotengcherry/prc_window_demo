<script setup>
// 한 조합의 한 행. 두 가지 모드:
//  - 분리(split): (feature × target × 분할값) 단일 조합. spec은 이 조합 전용.
//  - 겹쳐보기(multi): (feature × target) 한 행에 분할값들을 추세선으로 겹쳐 비교. spec은 공유.
import { computed } from 'vue'
import WindowChart from './WindowChart.vue'
import ComboTimeSeries from './ComboTimeSeries.vue'
import { cpk, inSpecPct } from '../stats.js'

const props = defineProps({
  combo: { type: Object, required: true },        // { x_feature, x_feature_display_name, y_target, ... }
  target: { type: Object, default: null },        // split: timeseries target series
  feature: { type: Object, default: null },       // split: timeseries feature series
  stats: { type: Object, default: null },         // split: table row(μ·σ전체·σ단기)
  multi: { type: Boolean, default: false },        // 겹쳐보기 여부
  members: { type: Array, default: () => [] },     // multi: [{ cfv, combo, target, feature, stats, color }]
  estimate: { type: Object, default: null },       // 분리 모드: { points, fit_summary }
  showEstimate: { type: Boolean, default: false },
  spec: { type: Object, required: true },         // { lower, upper } (양방향 바인딩 대상, 공유)
  dcSpec: { type: Object, default: () => ({}) },  // { lower, upper } feature별 DC spec
  thin: { type: Boolean, default: false },        // 표본 부족(신뢰 낮음)
  minN: { type: Number, default: 10 },
  sampled: { type: Boolean, default: false },
})

const xName = props.combo.x_feature_display_name || props.combo.x_feature

// 분리 모드 capability — Cpk(단기 σ) / Ppk(전체 σ), DC spec / user spec 기준
const hasUser = computed(() => props.spec?.lower != null && props.spec?.upper != null)
const cap = computed(() => {
  const s = props.stats || {}
  const mu = s.x_value, so = s.x_std, sw = s.x_std_within
  const d = props.dcSpec || {}, u = props.spec || {}
  return {
    cpkDc: cpk(mu, sw, d.lower, d.upper), ppkDc: cpk(mu, so, d.lower, d.upper),
    cpkU: cpk(mu, sw, u.lower, u.upper), ppkU: cpk(mu, so, u.lower, u.upper),
    inspecU: inSpecPct(mu, so, u.lower, u.upper),
  }
})

// 겹쳐보기 모드 — 분할값별 Cpk 요약 + 차트에 넘길 groups
const memberCaps = computed(() => props.members.map((m) => {
  const s = m.stats || {}
  return {
    cfv: m.cfv, color: m.color,
    cpkDc: cpk(s.x_value, s.x_std_within, props.dcSpec?.lower, props.dcSpec?.upper),
    cpkU: cpk(s.x_value, s.x_std_within, props.spec?.lower, props.spec?.upper),
  }
}))
const windowGroups = computed(() => props.members.map((m) => ({ label: m.cfv, color: m.color, bins: m.combo.bins })))
const tsGroups = computed(() => props.members.map((m) => ({ label: m.cfv, color: m.color, target: m.target, feature: m.feature })))

const f2 = (v) => (v == null ? '-' : v.toFixed(2))
const pct = (v) => (v == null ? '-' : (v * 100).toFixed(1) + '%')
const ck = (v) => (v == null ? '' : (v < 1 ? 'bad' : (v < 1.33 ? 'warn' : 'good')))
</script>

<template>
  <div class="combo-row">
    <div class="header">
      <span class="title">{{ xName }} × {{ combo.y_target }}
        <span v-if="multi" class="cf">· 겹쳐보기 {{ members.length }}</span>
        <span v-else-if="combo.category_feature_value" class="cf">· {{ combo.category_feature_value }}</span>
        <span v-if="thin" class="thin" title="표본 부족 — 신뢰도 낮음">thin</span>
      </span>
      <span class="spec">
        <span class="lbl">user spec</span>
        <label>lower <input type="number" v-model.number="spec.lower" /></label>
        <label>upper <input type="number" v-model.number="spec.upper" /></label>
      </span>
    </div>

    <!-- 분리 모드 capability -->
    <div v-if="!multi" class="cap-strip">
      <span class="cg" title="DC spec 기준 — user 입력 없이 항상 산출. Cpk=단기 σ(MR/1.128), Ppk=전체 σ">vs DC</span>
      <span>Cpk <b :class="ck(cap.cpkDc)">{{ f2(cap.cpkDc) }}</b></span>
      <span>Ppk <b :class="ck(cap.ppkDc)">{{ f2(cap.ppkDc) }}</b></span>
      <template v-if="hasUser">
        <span class="div">|</span>
        <span class="cg" title="user spec 기준">vs user</span>
        <span>Cpk <b :class="ck(cap.cpkU)">{{ f2(cap.cpkU) }}</b></span>
        <span>Ppk <b :class="ck(cap.ppkU)">{{ f2(cap.ppkU) }}</b></span>
        <span title="in-spec 비율(정규근사)">in-spec <b>{{ pct(cap.inspecU) }}</b></span>
      </template>
      <span v-else class="hint">· user spec 입력 시 user 기준 capability 표시</span>
    </div>

    <!-- 겹쳐보기 모드: 분할값별 Cpk 비교 -->
    <div v-else class="cap-strip">
      <span class="cg" title="분할값별 Cpk(단기 σ). user spec 입력 시 user 기준 추가 표시">분할별 Cpk</span>
      <span v-for="mc in memberCaps" :key="mc.cfv" class="mcap">
        <i class="sw" :style="{ background: mc.color }"></i>{{ mc.cfv }}
        <b :class="ck(mc.cpkDc)" title="DC spec 기준">{{ f2(mc.cpkDc) }}</b>
        <b v-if="hasUser" :class="ck(mc.cpkU)" title="user spec 기준">/ {{ f2(mc.cpkU) }}</b>
      </span>
    </div>

    <div class="charts">
      <div class="cell">
        <div class="cap">Window</div>
        <WindowChart v-if="!multi" :bins="combo.bins" :recommended-window="combo.recommended_window" :x-feature="xName" :y-target="combo.y_target" :spec="spec" :dc-spec="dcSpec" :min-n="minN" />
        <WindowChart v-else :groups="windowGroups" :x-feature="xName" :y-target="combo.y_target" :spec="spec" :dc-spec="dcSpec" :min-n="minN" />
      </div>
      <div class="cell">
        <div class="cap">시계열 (trackout_time)</div>
        <ComboTimeSeries v-if="!multi"
          :target="target" :feature="feature" :estimate="estimate" :show-estimate="showEstimate"
          :y-target="combo.y_target" :x-feature="xName" :spec="spec" :dc-spec="dcSpec" :sampled="sampled" />
        <ComboTimeSeries v-else
          :groups="tsGroups"
          :y-target="combo.y_target" :x-feature="xName" :spec="spec" :dc-spec="dcSpec" :sampled="sampled" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.combo-row {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 18px 20px; box-shadow: var(--shadow-sm);
  transition: box-shadow .25s, transform .25s;
}
.combo-row:hover { box-shadow: var(--shadow); transform: translateY(-2px); }
.cap-strip { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; font-size: 12px; color: var(--text-2); margin: 0 0 12px; padding: 7px 13px; background: var(--surface-2); border-radius: 10px; }
.cap-strip b { font-weight: 700; color: var(--text); }
.cap-strip b.good { color: #166534; } .cap-strip b.warn { color: #854d0e; } .cap-strip b.bad { color: #991b1b; }
.cap-strip .cg { font-weight: 700; color: var(--text); text-transform: uppercase; font-size: 10px; letter-spacing: .04em; cursor: help; }
.cap-strip .div { color: var(--border); }
.cap-strip .hint { color: #aaa; }
.mcap { display: inline-flex; align-items: center; gap: 5px; }
.mcap .sw { width: 9px; height: 9px; border-radius: 3px; display: inline-block; }
.header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
.title { font-size: 16px; font-weight: 600; color: var(--text); letter-spacing: -0.01em; display: flex; align-items: center; gap: 8px; }
.cf { font-size: 12px; font-weight: 500; color: var(--accent); }
.thin { font-size: 10px; font-weight: 700; color: #92400e; background: #fde68a; padding: 1px 7px; border-radius: 999px; text-transform: uppercase; }
.spec { display: flex; align-items: center; gap: 12px; background: var(--surface-2); padding: 6px 12px; border-radius: 12px; }
.lbl { font-size: 12px; font-weight: 600; color: var(--text-2); text-transform: uppercase; letter-spacing: 0.03em; }
.spec label { font-size: 12px; color: var(--text-2); display: flex; align-items: center; gap: 5px; }
.spec input {
  width: 70px; padding: 5px 8px; font-size: 13px; border: 1px solid var(--border);
  border-radius: 8px; background: #fff; outline: none; transition: border-color .15s, box-shadow .15s;
}
.spec input:focus { border-color: var(--accent); box-shadow: var(--ring); }
.charts { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.cell { min-width: 0; }
.cap { font-size: 11px; color: var(--text-2); margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; }
@media (max-width: 1100px) { .charts { grid-template-columns: 1fr; } }
</style>
