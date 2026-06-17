<script setup>
// 한 조합(feature × target)의 한 행: [spec 입력 헤더] + [Window 차트 | 매칭 시계열 차트]
// spec은 이 조합 전용. window(수직선)과 시계열(수평선)에 동시에 반영된다.
import WindowChart from './WindowChart.vue'
import ComboTimeSeries from './ComboTimeSeries.vue'

const props = defineProps({
  combo: { type: Object, required: true },        // { x_feature, y_target, bins }
  targetPoints: { type: Array, default: () => [] },
  featurePoints: { type: Array, default: () => [] },
  spec: { type: Object, required: true },         // { lower, upper } (양방향 바인딩 대상)
  dcSpec: { type: Object, default: () => ({}) },  // { lower, upper } feature별 DC spec
})
</script>

<template>
  <div class="combo-row">
    <div class="header">
      <span class="title">{{ combo.x_feature }} × {{ combo.y_target }}</span>
      <span class="spec">
        <span class="lbl">user spec</span>
        <label>lower <input type="number" v-model.number="spec.lower" /></label>
        <label>upper <input type="number" v-model.number="spec.upper" /></label>
      </span>
    </div>

    <div class="charts">
      <div class="cell">
        <div class="cap">Window</div>
        <WindowChart :bins="combo.bins" :x-feature="combo.x_feature" :y-target="combo.y_target" :spec="spec" :dc-spec="dcSpec" />
      </div>
      <div class="cell">
        <div class="cap">시계열 (trackout_time)</div>
        <ComboTimeSeries
          :target-points="targetPoints" :feature-points="featurePoints"
          :y-target="combo.y_target" :x-feature="combo.x_feature" :spec="spec"
        />
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
.header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
.title { font-size: 16px; font-weight: 600; color: var(--text); letter-spacing: -0.01em; }
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
