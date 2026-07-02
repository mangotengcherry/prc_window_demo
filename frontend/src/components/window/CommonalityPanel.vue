<template>
  <div class="commonality-panel">
    <div class="commonality-panel__table">
      <el-table :data="rows" size="small" highlight-current-row empty-text="commonality 계산 결과가 없습니다" @current-change="select">
        <el-table-column prop="factor" label="인자" min-width="150" />
        <el-table-column prop="group_count" label="그룹 수" width="82" />
        <el-table-column label="p-value" width="130">
          <template #default="{ row }">
            {{ row.p_value == null ? '-' : row.p_value.toFixed(4) }}
            <el-tag v-if="row.p_value != null && row.p_value < 0.05" type="warning" size="small" effect="plain">유의</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="effect_size" label="효과크기(ε²)" width="110">
          <template #default="{ row }">{{ row.effect_size ?? '-' }}</template>
        </el-table-column>
        <el-table-column prop="worst_group" label="최악 그룹" width="110" />
        <el-table-column label="n" width="90">
          <template #default="{ row }">{{ totalN(row) }}</template>
        </el-table-column>
      </el-table>
      <p class="commonality-panel__caption">part_modification_flag 행은 부품 개조 전후 두 그룹을 비교하는 Before/After 검정입니다.</p>
    </div>
    <div class="commonality-panel__chart chart-panel">
      <PlotlyChart v-if="selected" :data="boxData" :layout="boxLayout" />
      <el-empty v-else description="랭킹 행을 클릭하면 그룹별 boxplot이 표시됩니다" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import PlotlyChart from '../charts/PlotlyChart.vue'
import { CATEGORICAL_PALETTE } from '../../palette.ts'

const props = defineProps<{ rows: any[] }>()
const selected = ref<any>(null)

watch(
  () => props.rows,
  (rows) => {
    if (!rows?.length) {
      selected.value = null
      return
    }
    if (!selected.value || !rows.some((row) => row.factor === selected.value.factor)) selected.value = rows[0]
  },
  { immediate: true },
)

function select(row: any) {
  if (row) selected.value = row
}

function totalN(row: any) {
  return (row.groups || []).reduce((sum: number, group: any) => sum + group.n, 0)
}

const boxData = computed(() => {
  const groups = selected.value?.groups || []
  return [
    {
      type: 'box',
      x: groups.map((group: any) => String(group.value)),
      q1: groups.map((group: any) => group.q1),
      median: groups.map((group: any) => group.median),
      q3: groups.map((group: any) => group.q3),
      lowerfence: groups.map((group: any) => group.min),
      upperfence: groups.map((group: any) => group.max),
      mean: groups.map((group: any) => group.mean),
      boxmean: true,
      marker: { color: CATEGORICAL_PALETTE[0] },
      text: groups.map((group: any) => `n=${group.n}`),
    },
  ]
})

const boxLayout = computed(() => ({
  yaxis: { title: 'Fail rate', tickformat: '.1%' },
  xaxis: { title: selected.value?.factor || '' },
  showlegend: false,
}))
</script>

<style scoped>
.commonality-panel {
  display: grid;
  grid-template-columns: minmax(360px, 0.9fr) minmax(360px, 1.1fr);
  gap: 16px;
  min-width: 0;
}

.commonality-panel__caption {
  margin: 10px 2px 0;
  color: #64748b;
  font-size: 12px;
}

.commonality-panel__chart {
  height: 520px;
}
</style>
