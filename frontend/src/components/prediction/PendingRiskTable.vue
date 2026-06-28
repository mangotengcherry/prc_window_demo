<template>
  <el-table :data="rows" height="420" size="small" empty-text="예측 실행 후 Pending wafer가 표시됩니다">
    <el-table-column prop="risk_level" label="Risk" width="86">
      <template #default="{ row }">
        <el-tag :type="row.risk_level === 'High' ? 'danger' : row.risk_level === 'Medium' ? 'warning' : 'success'" size="small">{{ riskLabel(row.risk_level) }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="confidence" label="Confidence" width="112">
      <template #default="{ row }">{{ confidenceLabel(row.confidence) }}</template>
    </el-table-column>
    <el-table-column prop="lot_id" label="Lot" width="90" />
    <el-table-column prop="wafer_id" label="Wafer" width="100" />
    <el-table-column prop="expected_eds_date" label="Expected EDS" width="126" />
    <el-table-column prop="selected_fab_x_value" label="FAB X" width="100" />
    <el-table-column prop="predicted_bin_group_fail_rate" label="예측 fail" width="110">
      <template #default="{ row }">{{ pct(row.predicted_bin_group_fail_rate) }}</template>
    </el-table-column>
    <el-table-column label="예측 범위" width="132">
      <template #default="{ row }">{{ pct(row.prediction_lower) }} ~ {{ pct(row.prediction_upper) }}</template>
    </el-table-column>
    <el-table-column prop="chamber" label="Chamber" width="110" />
    <el-table-column prop="ppid" label="PPID" width="100" />
    <el-table-column prop="eco" label="ECO" width="120" />
    <el-table-column prop="explanation" label="설명" min-width="260" />
  </el-table>
</template>

<script setup lang="ts">
defineProps<{ rows: any[] }>()
const pct = (value: number) => `${(Number(value || 0) * 100).toFixed(2)}%`
const riskLabel = (value: string) => ({ High: '높음', Medium: '중간', Low: '낮음' }[value] || value)
const confidenceLabel = (value: string) => ({ High: '높음', Medium: '중간', Low: '낮음' }[value] || value)
</script>
