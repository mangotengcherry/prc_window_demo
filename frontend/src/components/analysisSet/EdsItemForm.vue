<template>
  <div class="eds-item-form">
    <div class="form-grid">
      <el-form-item label="EDS_STEP">
        <el-segmented v-model="criteria.eds_step" :options="analysis.metadata?.eds_steps || ['M', 'P', 'ML', 'PL']" />
      </el-form-item>
      <el-form-item label="Category">
        <el-segmented v-model="criteria.eds_category" :options="analysis.metadata?.eds_categories || ['BIN', 'MSR']" @change="onCategoryChange" />
      </el-form-item>
    </div>

    <el-form-item label="EDS_ITEM">
      <el-select-v2
        v-model="criteria.eds_items"
        :options="itemOptions"
        multiple
        filterable
        collapse-tags
        collapse-tags-tooltip
        placeholder="아이템 검색/선택"
        style="width: 100%"
      >
        <template #default="{ item }">
          <div class="eds-item-option">
            <span :title="item.formula || ''">{{ item.label }}</span>
            <el-icon
              v-if="item.owner && item.owner === me"
              class="eds-item-option__delete"
              @click.stop="removeCustomItem(item.value)"
            ><Delete /></el-icon>
          </div>
        </template>
      </el-select-v2>
      <el-button text :icon="Plus" class="mt-8" @click="dialogVisible = true">+ 커스텀 아이템</el-button>
      <el-alert v-if="error?.stage === 'eds_items'" :title="error.message" type="error" show-icon :closable="false" class="mt-8" />
    </el-form-item>

    <div class="form-grid">
      <el-form-item label="테스트 기간">
        <el-date-picker
          v-model="dateRangeModel"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="시작일"
          end-placeholder="종료일"
        />
      </el-form-item>
      <el-form-item label="part_id">
        <el-select v-model="criteria.part_id">
          <el-option v-for="item in analysis.metadata?.part_ids || ['All', 'A', 'B', 'C']" :key="item" :label="item" :value="item" />
        </el-select>
      </el-form-item>
    </div>

    <el-form-item label="EDS 필터식 (SQL/Spotfire)">
      <ExpressionEditor v-model="criteria.filter_expression" context="eds" />
      <el-alert v-if="error?.stage === 'eds_filter'" :title="error.message" type="error" show-icon :closable="false" class="mt-8" />
    </el-form-item>

    <CustomEdsItemDialog
      v-model:visible="dialogVisible"
      :category="criteria.eds_category"
      :items="baseItems"
      :server-error="dialogServerError"
      @save="onCreateCustomItem"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Delete, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ExpressionEditor from './ExpressionEditor.vue'
import CustomEdsItemDialog from './CustomEdsItemDialog.vue'
import { useAnalysisSetStore } from '../../stores/analysisSetStore'
import { currentUser } from '../../stores/presetStore'
import { createCustomEdsItem, deleteCustomEdsItem, fetchCustomEdsItems } from '../../api/analysisApi'

const props = defineProps<{
  error?: { stage: string; message: string } | null
}>()

const criteria = defineModel<any>('criteria', { required: true })
const analysis = useAnalysisSetStore()
const me = currentUser()

const customItems = ref<any[]>([])
const dialogVisible = ref(false)
const dialogServerError = ref('')

const baseItems = computed(() => analysis.metadata?.eds_items?.[criteria.value.eds_category] || [])
const customItemsInCategory = computed(() => customItems.value.filter((item) => item.category === criteria.value.eds_category))

function formatFormula(item: any) {
  return item.terms
    .map((term: any, index: number) => (index === 0 ? term.item : `${term.sign > 0 ? '+' : '−'} ${term.item}`))
    .join(' ')
}

const itemOptions = computed(() => [
  {
    label: '커스텀',
    options: customItemsInCategory.value.map((item) => ({
      value: item.name,
      label: item.name,
      owner: item.owner,
      formula: `${item.name} = ${formatFormula(item)} (${item.owner})`,
    })),
  },
  {
    label: criteria.value.eds_category,
    options: baseItems.value.map((name: string) => ({ value: name, label: name })),
  },
])

const dateRangeModel = computed({
  get: () => (criteria.value.date_range?.start && criteria.value.date_range?.end
    ? [criteria.value.date_range.start, criteria.value.date_range.end]
    : null),
  set: (value: [string, string] | null) => {
    criteria.value.date_range = { start: value?.[0] ?? null, end: value?.[1] ?? null }
  },
})

function onCategoryChange() {
  criteria.value.eds_items = []
}

async function loadCustomItems() {
  customItems.value = await fetchCustomEdsItems()
}

async function onCreateCustomItem(payload: { name: string; category: string; terms: { item: string; sign: 1 | -1 }[] }) {
  dialogServerError.value = ''
  try {
    await createCustomEdsItem(payload)
    await loadCustomItems()
    criteria.value.eds_items = [...criteria.value.eds_items, payload.name]
    dialogVisible.value = false
    ElMessage.success(`${payload.name} 생성 완료`)
  } catch (e: any) {
    dialogServerError.value = e?.response?.data?.detail || '커스텀 아이템 생성에 실패했습니다'
  }
}

async function removeCustomItem(name: string) {
  await ElMessageBox.confirm(`${name} 커스텀 아이템을 삭제할까요?`, '삭제 확인', { type: 'warning' })
  await deleteCustomEdsItem(name)
  criteria.value.eds_items = criteria.value.eds_items.filter((item: string) => item !== name)
  await loadCustomItems()
}

onMounted(loadCustomItems)
</script>
