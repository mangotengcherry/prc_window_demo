<template>
  <el-drawer :model-value="visible" title="Wafer 상세" size="420px" @update:model-value="$emit('update:visible', $event)">
    <template v-if="point">
      <dl class="detail-grid">
        <dt>Lot / Wafer</dt><dd>{{ point.lot_id }} / {{ point.wafer_id }}</dd>
        <dt>Tool / Chamber</dt><dd>{{ point.tool_id }} / {{ point.chamber_id }}</dd>
        <dt>PPID / ECO</dt><dd>{{ point.ppid }} / {{ point.eco_number }}</dd>
        <dt>Recipe</dt><dd>{{ point.recipe_version }}</dd>
        <dt>Zone</dt><dd>{{ point.zone }}</dd>
        <dt>FAB 값</dt><dd>{{ point.x_value }}</dd>
        <dt>Target offset</dt><dd>{{ point.target_offset }}</dd>
        <dt>Spec margin</dt><dd>{{ point.spec_margin }}</dd>
        <dt>EDS yield</dt><dd>{{ pct(point.eds_yield) }}</dd>
        <dt>BIN Group fail</dt><dd>{{ pct(point.selected_bin_group_fail_rate) }}</dd>
        <dt>부품 개조</dt><dd>{{ point.part_modification_flag ? '적용' : '미적용' }}</dd>
      </dl>
      <el-input v-model="reason" type="textarea" :rows="3" placeholder="제외 사유" />
      <div class="drawer-actions">
        <el-button type="danger" plain @click="$emit('exclude', { waferIds: [point.wafer_id], reason })">Exclusion Rule 저장</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{ visible: boolean; point: any }>()
defineEmits<{ (event: 'update:visible', value: boolean): void; (event: 'exclude', value: any): void }>()
const reason = ref('다른 공정 noise 후보')
const pct = (value: number) => `${(Number(value || 0) * 100).toFixed(2)}%`

watch(() => props.point?.wafer_id, () => {
  reason.value = '다른 공정 noise 후보'
})
</script>
