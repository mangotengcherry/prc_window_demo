<script setup>
// 좌측 탭: Y target / X feature 다중 선택(체크박스 list box, 키워드 검색) + fab_step 단일 선택.
import { ref, computed, watch } from 'vue'

const props = defineProps({
  features: { type: Array, default: () => [] },
  targets: { type: Array, default: () => [] },
  fabSteps: { type: Array, default: () => [] },
})
const emit = defineEmits(['draw'])

const xFeatures = ref([])
const yTargets = ref([])
const fabStep = ref('')
const xSearch = ref('')
const ySearch = ref('')

const filteredFeatures = computed(() =>
  props.features.filter((f) => f.toLowerCase().includes(xSearch.value.toLowerCase())))
const filteredTargets = computed(() =>
  props.targets.filter((t) => t.toLowerCase().includes(ySearch.value.toLowerCase())))

watch(() => props.features, (f) => { if (f.length && !xFeatures.value.length) xFeatures.value = [f[0]] }, { immediate: true })
watch(() => props.targets, (t) => { if (t.length && !yTargets.value.length) yTargets.value = [t[0]] }, { immediate: true })
watch(() => props.fabSteps, (s) => { if (s.length && !fabStep.value) fabStep.value = s[0] }, { immediate: true })

function onDraw() {
  if (!xFeatures.value.length || !yTargets.value.length || !fabStep.value) return
  emit('draw', { xFeatures: [...xFeatures.value], yTargets: [...yTargets.value], fabStep: fabStep.value })
}
</script>

<template>
  <aside class="sidebar">
    <h1 class="brand"><span class="dot"></span>Process Window</h1>

    <section>
      <h3>Y target <small>{{ yTargets.length }}</small></h3>
      <input class="search" v-model="ySearch" placeholder="검색" />
      <div class="listbox">
        <label v-for="t in filteredTargets" :key="t" class="item" :class="{ on: yTargets.includes(t) }">
          <input type="checkbox" :value="t" v-model="yTargets" />
          <span>{{ t }}</span>
        </label>
        <p v-if="!filteredTargets.length" class="none">결과 없음</p>
      </div>
    </section>

    <section>
      <h3>X feature <small>{{ xFeatures.length }}</small></h3>
      <input class="search" v-model="xSearch" placeholder="검색" />
      <div class="listbox">
        <label v-for="f in filteredFeatures" :key="f" class="item" :class="{ on: xFeatures.includes(f) }">
          <input type="checkbox" :value="f" v-model="xFeatures" />
          <span>{{ f }}</span>
        </label>
        <p v-if="!filteredFeatures.length" class="none">결과 없음</p>
      </div>
    </section>

    <section>
      <h3>fab_step</h3>
      <select v-model="fabStep">
        <option v-for="s in fabSteps" :key="s" :value="s">{{ s }}</option>
      </select>
    </section>

    <button class="draw" @click="onDraw">차트 작성</button>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 250px; flex: 0 0 250px;
  background: var(--sidebar);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-right: 1px solid var(--border);
  padding: 26px 20px; display: flex; flex-direction: column; gap: 22px; overflow-y: auto;
}
.brand { font-size: 19px; font-weight: 600; margin: 0 0 2px; letter-spacing: -0.02em; display: flex; align-items: center; gap: 9px; }
.dot { width: 12px; height: 12px; border-radius: 5px; background: linear-gradient(135deg, var(--accent-2), var(--accent)); box-shadow: 0 2px 6px rgba(79, 70, 229, 0.4); }
section { display: flex; flex-direction: column; gap: 8px; }
h3 {
  font-size: 12px; margin: 0; color: var(--text-2); font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.04em; display: flex; align-items: center; gap: 6px;
}
h3 small {
  font-size: 11px; font-weight: 600; color: var(--accent);
  background: var(--accent-weak); border-radius: 999px; padding: 1px 7px; letter-spacing: 0;
}
.search {
  padding: 8px 11px; font-size: 13px; border-radius: 10px;
  border: 1px solid var(--border); background: #fff; color: var(--text); outline: none;
  transition: border-color .15s, box-shadow .15s;
}
.search:focus { border-color: var(--accent); box-shadow: var(--ring); }
.search::placeholder { color: #b0b0b5; }

.listbox {
  border: 1px solid var(--border); border-radius: var(--radius-sm); background: #fff;
  padding: 5px; max-height: 150px; /* 약 4개 표시 후 스크롤 */
  overflow-y: auto; display: flex; flex-direction: column; gap: 2px;
}
.item {
  display: flex; align-items: center; gap: 9px; padding: 7px 9px;
  font-size: 14px; border-radius: 8px; cursor: pointer; transition: background .12s;
}
.item:hover { background: #f5f5f7; }
.item.on { background: var(--accent-weak); color: var(--accent); font-weight: 500; }
.item input { width: 15px; height: 15px; accent-color: var(--accent); cursor: pointer; }
.none { color: #b0b0b5; font-size: 13px; text-align: center; padding: 10px; margin: 0; }

select {
  width: 100%; padding: 9px 11px; font-size: 14px; border-radius: 10px;
  border: 1px solid var(--border); background: #fff; color: var(--text); outline: none;
}
select:focus { border-color: var(--accent); box-shadow: var(--ring); }

.draw {
  margin-top: auto; padding: 13px; color: #fff;
  background: linear-gradient(135deg, var(--accent-2), var(--accent));
  border: none; border-radius: 14px; font-size: 15px; font-weight: 600; cursor: pointer;
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.32); letter-spacing: -0.01em;
  transition: transform .08s, box-shadow .2s, filter .2s;
}
.draw:hover { filter: brightness(1.05); box-shadow: 0 8px 22px rgba(79, 70, 229, 0.4); }
.draw:active { transform: scale(0.98); }
</style>
