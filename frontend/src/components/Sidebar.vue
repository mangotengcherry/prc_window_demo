<script setup>
// 좌측 조건 패널 (M0): Line/제품/Category/EDS_STEP/FAB_STEP/기간 + X feature/Y target 다중선택.
import { ref, computed, watch } from 'vue'

const props = defineProps({
  columns: { type: Object, default: null },        // /api/columns 응답
  xFeatureOptions: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['xopts-change', 'draw'])

const lineId = ref('')
const product = ref('')
const category = ref('')
const edsStep = ref('')
const fabStep = ref('')
const startDate = ref('')
const endDate = ref('')
const yStartDate = ref('') // y target 확보 시점(eds_tkout_time) 기준
const yEndDate = ref('')
const xFeatures = ref([])
const yTargets = ref([])
const xSearch = ref('')
const ySearch = ref('')
const xSort = ref('name') // name | score(영향도)
const matching = ref(true)        // fab_metro_prc 매칭 필터 on/off
const metroGrade = ref('')        // '' = 전체
const metroCategory = ref('')

// 컬럼 도착 시 기본값
watch(() => props.columns, (c) => {
  if (!c) return
  lineId.value = c.line_ids?.[0] || ''
  product.value = c.products?.[0] || ''
  category.value = c.categories?.[0] || ''
  edsStep.value = c.eds_steps?.[0] || ''
  fabStep.value = c.fab_steps?.[0] || ''
  startDate.value = c.date_default?.start_date || ''
  endDate.value = c.date_default?.end_date || ''
  yStartDate.value = c.target_date_default?.start_date || ''
  yEndDate.value = c.target_date_default?.end_date || ''
}, { immediate: true })

// fab_step / matching / metro 필터가 바뀌면 부모가 x-feature-options 재요청
watch([fabStep, matching, metroGrade, metroCategory], () => {
  if (fabStep.value) emit('xopts-change', {
    fabStep: fabStep.value, matching: matching.value,
    metroGrade: metroGrade.value || null, metroCategory: metroCategory.value || null,
  })
}, { immediate: true })
// fab_step 바뀌면 X feature 선택 초기화 (다른 fab의 feature는 무의미)
watch(fabStep, () => { xFeatures.value = [] })

// Y target 후보 = 선택 category 종속
const targetOptions = computed(() => props.columns?.targets_by_category?.[category.value] || [])
// category 바뀌면 유효하지 않은 yTarget 제거
watch(category, () => { yTargets.value = yTargets.value.filter((t) => targetOptions.value.includes(t)) })

// matching/필터로 인해 현재 옵션 밖에 있는 '선택된' X feature (선택 유지 + 확인용)
function keyDisplay(k) { const p = k.split('|'); return p.length >= 5 ? `${p[3]} / ${p[4]}` : k }
const selectedOutside = computed(() => {
  const inOpts = new Set(props.xFeatureOptions.map((o) => o.name))
  return xFeatures.value.filter((n) => !inOpts.has(n))
})
function removeX(k) { xFeatures.value = xFeatures.value.filter((n) => n !== k) }

const fx = computed(() => {
  const arr = props.xFeatureOptions.filter((o) =>
    (o.display_name + ' ' + o.name).toLowerCase().includes(xSearch.value.toLowerCase()))
  if (xSort.value === 'score') arr.sort((a, b) => (b.score ?? -1) - (a.score ?? -1))
  return arr
})
const fy = computed(() => targetOptions.value.filter((t) =>
  t.toLowerCase().includes(ySearch.value.toLowerCase())))

const valid = computed(() =>
  lineId.value && product.value && category.value && edsStep.value && fabStep.value &&
  startDate.value && endDate.value && yStartDate.value && yEndDate.value &&
  xFeatures.value.length && yTargets.value.length)

function allX(on) { xFeatures.value = on ? fx.value.map((o) => o.name) : [] }
function allY(on) { yTargets.value = on ? [...fy.value] : [] }

function onDraw() {
  if (!valid.value) return
  emit('draw', {
    line_id: lineId.value, product: product.value, category: category.value, eds_step: edsStep.value,
    date_range: { start_date: startDate.value, end_date: endDate.value, time_column: 'fab_track_out_time' },
    target_date_range: { start_date: yStartDate.value, end_date: yEndDate.value, time_column: 'eds_tkout_time' },
    fab_step: fabStep.value,
    x_features: [...xFeatures.value], y_targets: [...yTargets.value], bins: 10,
  })
}
</script>

<template>
  <aside class="sidebar">
    <h1 class="brand"><span class="dot"></span>Process Window</h1>

    <div class="grid2">
      <label class="fld">Line<select v-model="lineId"><option v-for="x in columns?.line_ids" :key="x">{{ x }}</option></select></label>
      <label class="fld">제품<select v-model="product"><option v-for="x in columns?.products" :key="x">{{ x }}</option></select></label>
    </div>

    <label class="fld">FAB_STEP
      <select v-model="fabStep"><option v-for="x in columns?.fab_steps" :key="x">{{ x }}</option></select>
    </label>

    <div class="grid2">
      <label class="fld">FAB 시작일<input type="date" v-model="startDate" /></label>
      <label class="fld">FAB 종료일<input type="date" v-model="endDate" /></label>
    </div>
    <p class="muted">x축·분석 기간 기준: fab_track_out_time</p>

    <section>
      <h3>Y target <small>{{ yTargets.length }}/{{ targetOptions.length }}</small></h3>
      <div class="grid2">
        <label class="fld">EDS_STEP<select v-model="edsStep"><option v-for="x in columns?.eds_steps" :key="x">{{ x }}</option></select></label>
        <label class="fld">Category<select v-model="category"><option v-for="x in columns?.categories" :key="x">{{ x }}</option></select></label>
      </div>
      <div class="grid2">
        <label class="fld">Y 시작일<input type="date" v-model="yStartDate" /></label>
        <label class="fld">Y 종료일<input type="date" v-model="yEndDate" /></label>
      </div>
      <p class="muted">y target 확보 기준: eds_tkout_time</p>
      <input class="search" v-model="ySearch" placeholder="검색" />
      <div class="bar"><a @click="allY(true)">전체 선택</a><a @click="allY(false)">해제</a></div>
      <div class="listbox sm">
        <label v-for="t in fy" :key="t" class="item" :class="{ on: yTargets.includes(t) }">
          <input type="checkbox" :value="t" v-model="yTargets" /><span>{{ t }}</span>
        </label>
        <p v-if="!fy.length" class="none">결과 없음</p>
      </div>
    </section>

    <section>
      <h3>X feature <small>{{ xFeatures.length }}/{{ xFeatureOptions.length }}</small></h3>
      <div class="matchrow">
        <label class="tog" :class="{ on: matching }" title="fab_metro_prc 매칭: 선택 FAB_STEP과 연관된 metro item만 표시">
          <input type="checkbox" v-model="matching" />Matching
        </label>
        <select v-model="metroGrade" class="mini"><option value="">Grade·전체</option><option v-for="g in columns?.metro_grades" :key="g" :value="g">{{ g }}</option></select>
        <select v-model="metroCategory" class="mini"><option value="">Cat·전체</option><option v-for="c in columns?.metro_categories" :key="c" :value="c">{{ c }}</option></select>
      </div>
      <input class="search" v-model="xSearch" placeholder="검색 (metro item / key)" />
      <div class="bar"><a @click="allX(true)">전체 선택</a><a @click="allX(false)">해제</a>
        <a class="sort" @click="xSort = xSort === 'score' ? 'name' : 'score'">{{ xSort === 'score' ? '↓ 영향도순' : '이름순' }}</a></div>
      <div class="listbox">
        <label v-for="o in fx" :key="o.name" class="item col" :class="{ on: xFeatures.includes(o.name) }" :title="o.name">
          <div class="row1"><input type="checkbox" :value="o.name" v-model="xFeatures" /><span class="dn">{{ o.display_name }}</span>
            <span v-if="o.data_type === 'category'" class="tag">cat</span></div>
          <div class="sub">FAB {{ o.name.split('|')[1] }} · {{ o.metro_step }}<span v-if="o.score != null"> · 영향도 {{ o.score }}</span></div>
        </label>
        <p v-if="!fx.length" class="none">결과 없음 (FAB_STEP/matching 확인)</p>
      </div>
      <div v-if="selectedOutside.length" class="outside">
        <span class="olbl">필터 밖 선택 {{ selectedOutside.length }}</span>
        <span v-for="k in selectedOutside" :key="k" class="ochip" :title="k">{{ keyDisplay(k) }}<a @click="removeX(k)">×</a></span>
      </div>
    </section>

    <button class="draw" :disabled="!valid || loading" @click="onDraw">
      {{ loading ? '불러오는 중…' : '차트 작성' }}
    </button>
    <p v-if="!valid" class="hint">Line·제품·Category·EDS·FAB·기간 + X/Y 1개 이상 선택</p>
  </aside>
</template>

<style scoped>
.sidebar { width: 270px; flex: 0 0 270px; background: var(--sidebar); backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%); border-right: 1px solid var(--border);
  padding: 22px 18px; display: flex; flex-direction: column; gap: 14px; overflow-y: auto; }
.brand { font-size: 18px; font-weight: 600; margin: 0 0 4px; letter-spacing: -0.02em; display: flex; align-items: center; gap: 9px; }
.dot { width: 12px; height: 12px; border-radius: 5px; background: linear-gradient(135deg, var(--accent-2), var(--accent)); box-shadow: 0 2px 6px rgba(79,70,229,.4); }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.fld { display: flex; flex-direction: column; gap: 3px; font-size: 11px; color: var(--text-2); font-weight: 600; }
select, input[type="date"] { width: 100%; padding: 7px 9px; font-size: 13px; border-radius: 9px; border: 1px solid var(--border); background: #fff; color: var(--text); outline: none; }
select:focus, input:focus { border-color: var(--accent); box-shadow: var(--ring); }
.muted { font-size: 10px; color: var(--text-2); margin: -4px 0 0; }
section { display: flex; flex-direction: column; gap: 5px; }
h3 { font-size: 12px; margin: 2px 0 0; color: var(--text-2); font-weight: 600; text-transform: uppercase; letter-spacing: .04em; display: flex; align-items: center; gap: 6px; }
h3 small { font-size: 11px; font-weight: 600; color: var(--accent); background: var(--accent-weak); border-radius: 999px; padding: 1px 7px; letter-spacing: 0; }
.search { padding: 7px 10px; font-size: 12px; border-radius: 9px; border: 1px solid var(--border); }
.bar { display: flex; gap: 10px; }
.bar a { font-size: 11px; color: var(--accent); cursor: pointer; }
.bar .sort { margin-left: auto; font-weight: 600; }
.matchrow { display: flex; gap: 6px; align-items: center; }
.tog { display: flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; color: var(--text-2); padding: 5px 9px; border: 1px solid var(--border); border-radius: 9px; background: #fff; cursor: pointer; white-space: nowrap; }
.tog.on { color: var(--accent); border-color: var(--accent); background: var(--accent-weak); }
.tog input { width: 13px; height: 13px; accent-color: var(--accent); }
.mini { flex: 1; min-width: 0; padding: 5px 6px; font-size: 11px; border-radius: 9px; border: 1px solid var(--border); background: #fff; color: var(--text); }
.outside { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; padding: 6px 2px 0; }
.olbl { font-size: 10px; font-weight: 700; color: #92400e; background: #fde68a; padding: 1px 7px; border-radius: 999px; }
.ochip { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; color: var(--text-2); background: var(--surface-2); border: 1px solid var(--border); border-radius: 999px; padding: 2px 8px; }
.ochip a { color: #d70015; cursor: pointer; font-weight: 700; }
.listbox { border: 1px solid var(--border); border-radius: 11px; background: #fff; padding: 5px; max-height: 190px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.listbox.sm { max-height: 120px; }
.item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; font-size: 13px; border-radius: 8px; cursor: pointer; }
.item:hover { background: #f5f5f7; }
.item.on { background: var(--accent-weak); }
.item.col { flex-direction: column; align-items: stretch; gap: 2px; }
.row1 { display: flex; align-items: center; gap: 7px; }
.dn { font-weight: 500; }
.sub { font-size: 10px; color: var(--text-2); padding-left: 22px; }
.tag { font-size: 9px; background: #fde68a; color: #92400e; padding: 0 5px; border-radius: 4px; margin-left: auto; }
.item input { width: 14px; height: 14px; accent-color: var(--accent); }
.none { color: #b0b0b5; font-size: 12px; text-align: center; padding: 10px; margin: 0; }
.draw { margin-top: 6px; padding: 12px; color: #fff; background: linear-gradient(135deg, var(--accent-2), var(--accent)); border: none; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; box-shadow: 0 6px 16px rgba(79,70,229,.32); }
.draw:disabled { opacity: .45; cursor: not-allowed; box-shadow: none; }
.hint { font-size: 11px; color: var(--text-2); margin: 0; text-align: center; }
</style>
