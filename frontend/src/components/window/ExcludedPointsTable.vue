<template>
  <el-table :data="rules" size="small" empty-text="저장된 Exclusion Rule이 없습니다">
    <el-table-column prop="id" label="Version" width="90" />
    <el-table-column label="이름" min-width="180">
      <template #default="{ row }">
        {{ row.name }}
        <el-tag v-if="row.id === activeRuleId" type="success" size="small" style="margin-left: 6px">적용 중</el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="excluded_count" label="Wafer" width="90" />
    <el-table-column prop="reason" label="제외 사유" min-width="220" />
  </el-table>
</template>

<script setup lang="ts">
defineProps<{ rules: any[]; activeRuleId?: string | null }>()
</script>
