<template>
  <div class="page-grid two-col">
    <FilterPanel title="조건 Rule 정의" subtitle="ECO, PPID, Tool/Chamber, Recipe, PM age, 부품 개조 전후 같은 legend 기준을 정의합니다.">
      <el-form label-position="top" class="dense-form">
        <div class="form-grid">
          <el-form-item label="Rule 이름">
            <el-input v-model="form.name" />
          </el-form-item>
          <el-form-item label="Legend 기준">
            <el-select v-model="form.legend_basis">
              <el-option v-for="basis in bases" :key="basis" :label="basis" :value="basis" />
            </el-select>
          </el-form-item>
          <el-form-item label="Tool">
            <el-select v-model="manual.tool_id">
              <el-option v-for="item in metadata?.tools || []" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="Chamber">
            <el-select v-model="manual.chamber_id">
              <el-option v-for="item in metadata?.chambers || []" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="적용 시작일">
            <el-date-picker v-model="manual.applied_from" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="Before / After label">
            <el-input v-model="manual.label_before" />
            <el-input v-model="manual.label_after" class="mt-8" />
          </el-form-item>
        </div>
        <el-button :icon="Plus" type="primary" @click="createRule">조건 Rule 저장</el-button>
      </el-form>
    </FilterPanel>

    <FilterPanel title="저장된 조건 Rule" subtitle="원천 데이터를 바꾸지 않고 선택된 Analysis Set에 legend rule로 적용됩니다.">
      <el-table :data="rules.conditionRules" size="small" highlight-current-row @current-change="selectRule">
        <el-table-column prop="id" label="ID" width="78" />
        <el-table-column prop="name" label="이름" min-width="200" />
        <el-table-column prop="legend_basis" label="기준" width="150" />
        <el-table-column label="Manual rule" min-width="240">
          <template #default="{ row }">{{ row.manual_rules?.map((rule:any) => `${rule.tool_id}/${rule.chamber_id} from ${rule.applied_from}`).join(', ') || '-' }}</template>
        </el-table-column>
      </el-table>
    </FilterPanel>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import FilterPanel from '../components/common/FilterPanel.vue'
import { useAnalysisSetStore } from '../stores/analysisSetStore'
import { useConditionRuleStore } from '../stores/conditionRuleStore'

const analysis = useAnalysisSetStore()
const rules = useConditionRuleStore()
const metadata = computed(() => analysis.metadata)
const bases = ['Part modification', 'ECO', 'PPID', 'Tool', 'Chamber', 'Recipe', 'PM age']
const form = reactive({ name: 'Manual part modification split', legend_basis: 'Part modification' })
const manual = reactive({
  tool_id: 'T01',
  chamber_id: 'C2',
  applied_from: '2026-03-15',
  label_before: 'Before modification',
  label_after: 'After modification',
})

function selectRule(row: any) {
  if (row?.id) rules.selectedConditionRuleId = row.id
}

async function createRule() {
  const item = await rules.create({ ...form, manual_rules: [{ ...manual }] })
  ElMessage.success(`${item.name} 저장 완료`)
}
</script>
