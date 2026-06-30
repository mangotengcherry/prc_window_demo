<template>
  <div class="analysis-selection-layout">
    <FilterPanel title="조건 라이브러리" subtitle="공유 조건은 읽기 전용이며, 개인 조건으로 복사한 뒤 수정합니다.">
      <el-tabs v-model="libraryScope" stretch>
        <el-tab-pane label="공유 조건" name="shared" />
        <el-tab-pane label="개인 조건" name="personal" />
      </el-tabs>
      <div class="condition-list">
        <button
          v-for="condition in visibleConditions"
          :key="condition.id"
          class="condition-item"
          :class="{ active: activeCondition?.id === condition.id }"
          type="button"
          @click="selectCondition(condition)"
        >
          <span>{{ condition.process_key }}</span>
          <strong>{{ condition.revision }}</strong>
          <small>{{ condition.name }}</small>
          <em>{{ describePeriod(condition.fab_filters) }}</em>
        </button>
      </div>
    </FilterPanel>

    <section class="selection-workflow">
      <FilterPanel title="분석물량 선정" subtitle="FAB 기준, EDS 기준, Legend 기준을 순서대로 확인한 뒤 Window Review로 넘깁니다.">
        <el-steps :active="currentStepIndex" finish-status="success" class="selection-steps">
          <el-step v-for="step in steps" :key="step.key" :title="step.title" />
        </el-steps>

        <template v-if="draft">
          <div v-show="activeStep === 'fab'" class="wizard-section">
            <div class="section-kicker">Step 1</div>
            <h3>FAB 기준 검색 조건 설정</h3>
            <p>공정 revision별로 어떤 FAB 물량을 볼지 정합니다. 기간은 고정 기간 또는 최근 N일 방식으로 설정할 수 있습니다.</p>
            <div class="form-grid">
              <el-form-item label="기간 방식">
                <el-segmented v-model="draft.fab_filters.date_mode" :options="periodOptions" />
              </el-form-item>
              <el-form-item v-if="draft.fab_filters.date_mode === 'fixed'" label="추출 대상 기간">
                <el-date-picker v-model="fixedDateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="시작일" end-placeholder="종료일" :disabled="!editable" />
              </el-form-item>
              <el-form-item v-else label="최근 N일">
                <el-input-number v-model="draft.fab_filters.recent_days" :min="7" :max="365" controls-position="right" :disabled="!editable" />
              </el-form-item>
              <el-form-item label="Product">
                <el-select v-model="draft.fab_filters.product" multiple filterable :disabled="!editable">
                  <el-option v-for="item in metadata?.products || []" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="Layer">
                <el-select v-model="draft.fab_filters.layer" multiple filterable :disabled="!editable">
                  <el-option v-for="item in metadata?.layers || []" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="Step">
                <el-select v-model="draft.fab_filters.step" multiple filterable :disabled="!editable">
                  <el-option v-for="item in metadata?.steps || []" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="FAB 관리 인자">
                <el-select v-model="draft.fab_filters.parameter" multiple filterable :disabled="!editable">
                  <el-option v-for="item in metadata?.parameters || []" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="Tool">
                <el-select v-model="draft.fab_filters.tool" multiple filterable :disabled="!editable">
                  <el-option v-for="item in metadata?.tools || []" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
              <el-form-item label="PPID / ECO">
                <el-select v-model="draft.fab_filters.ppid" multiple filterable :disabled="!editable">
                  <el-option v-for="item in metadata?.ppids || []" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
            </div>
          </div>

          <div v-show="activeStep === 'eds'" class="wizard-section">
            <div class="section-kicker">Step 2</div>
            <h3>EDS 기준 검색 조건 설정</h3>
            <p>앞으로는 EDS Data가 확보된 wafer만 분석 대상으로 사용합니다. 여기서는 Window Review의 Y축이 될 BIN Group을 선택합니다.</p>
            <el-alert title="Pending 예측은 사용하지 않습니다. EDS actual 물량만 FAB Data 추출 대상으로 고정됩니다." type="info" show-icon :closable="false" />
            <el-checkbox-group v-model="draft.selected_bin_group_ids" class="bin-choice-grid" :disabled="!editable">
              <label v-for="group in binGroups.binGroups" :key="group.id" class="bin-choice">
                <el-checkbox :label="group.id">
                  <strong>{{ group.name }}</strong>
                  <span>{{ group.failure_mode }}</span>
                  <em>{{ group.bin_ids.join(' + ') }}</em>
                </el-checkbox>
              </label>
            </el-checkbox-group>
          </div>

          <div v-show="activeStep === 'legend'" class="wizard-section">
            <div class="section-kicker">Step 3</div>
            <h3>비교 대상 Legend 설정</h3>
            <p>시계열과 Scatter 차트에서 어떤 조건을 비교할지 정합니다. 공정 revision 비교에는 부품 개조 전후, ECO, PPID, Tool/Chamber 기준이 자주 쓰입니다.</p>
            <div class="form-grid">
              <el-form-item label="Legend 기준">
                <el-select v-model="draft.legend_config.basis" :disabled="!editable">
                  <el-option v-for="basis in legendBases" :key="basis" :label="basis" :value="basis" />
                </el-select>
              </el-form-item>
              <el-form-item label="조건 Rule">
                <el-select v-model="draft.condition_rule_id" :disabled="!editable" @change="draft.legend_config.condition_rule_id = draft.condition_rule_id">
                  <el-option v-for="rule in conditionRules.conditionRules" :key="rule.id" :label="rule.name" :value="rule.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="Scatter X 인자">
                <el-select v-model="draft.legend_config.x_parameter" filterable :disabled="!editable">
                  <el-option v-for="item in metadata?.parameters || []" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
            </div>
          </div>
        </template>
      </FilterPanel>

      <div class="wizard-actions">
        <el-button :disabled="activeStep === 'fab'" @click="activeStep = previousStepKey(activeStep)">Back</el-button>
        <el-button v-if="activeStep !== 'legend'" type="primary" @click="activeStep = nextStepKey(activeStep)">Next</el-button>
        <el-button v-else type="primary" :loading="saving" @click="goWindowReview">Window Review로 이동</el-button>
      </div>
    </section>

    <FilterPanel title="현재 조건 요약" subtitle="공유 조건은 복사 후 수정할 수 있습니다.">
      <template v-if="draft">
        <div class="condition-summary">
          <span>{{ summary.scopeLabel }}</span>
          <h3>{{ summary.title }}</h3>
          <p>{{ summary.name }}</p>
        </div>
        <dl class="summary-definition">
          <div><dt>기간</dt><dd>{{ summary.period }}</dd></div>
          <div><dt>Product</dt><dd>{{ summary.product }}</dd></div>
          <div><dt>Step</dt><dd>{{ summary.step }}</dd></div>
          <div><dt>EDS 기준</dt><dd>{{ summary.edsStatus }}</dd></div>
          <div><dt>BIN Group</dt><dd>{{ summary.binGroups }}</dd></div>
          <div><dt>Legend</dt><dd>{{ summary.legendBasis }}</dd></div>
        </dl>
        <div class="side-actions">
          <el-button v-if="!editable" type="primary" plain :loading="saving" @click="copyToPersonal">개인 조건으로 복사</el-button>
          <el-button v-else type="primary" plain :loading="saving" @click="saveDraft">개인 조건 저장</el-button>
          <el-button plain disabled>공유 조건 승격 요청</el-button>
        </div>
      </template>
      <el-empty v-else description="조건을 선택하세요" />
    </FilterPanel>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import FilterPanel from '../components/common/FilterPanel.vue'
import {
  ANALYSIS_SELECTION_STEPS,
  describePeriod,
  isEditableCondition,
  nextStepKey,
  previousStepKey,
  summarizeCondition,
} from '../analysisSelection.js'
import { useAnalysisSetStore } from '../stores/analysisSetStore'
import { useBinGroupStore } from '../stores/binGroupStore'
import { useConditionRuleStore } from '../stores/conditionRuleStore'

const router = useRouter()
const analysis = useAnalysisSetStore()
const binGroups = useBinGroupStore()
const conditionRules = useConditionRuleStore()

const steps = ANALYSIS_SELECTION_STEPS
const libraryScope = ref('shared')
const activeStep = ref('fab')
const activeCondition = ref<any>(null)
const draft = ref<any>(null)
const saving = ref(false)
const periodOptions = [
  { label: '고정 기간', value: 'fixed' },
  { label: '최근 N일', value: 'recent_days' },
]
const legendBases = ['Part modification', 'ECO', 'PPID', 'Tool', 'Chamber', 'Recipe', 'PM age']

const metadata = computed(() => analysis.metadata)
const visibleConditions = computed(() => analysis.conditionLibrary[libraryScope.value] || [])
const editable = computed(() => isEditableCondition(draft.value))
const summary = computed(() => summarizeCondition(draft.value))
const currentStepIndex = computed(() => steps.findIndex((step) => step.key === activeStep.value))
const fixedDateRange = computed({
  get() {
    if (!draft.value?.fab_filters?.start_date || !draft.value?.fab_filters?.end_date) return ''
    return [draft.value.fab_filters.start_date, draft.value.fab_filters.end_date]
  },
  set(value: any) {
    if (!draft.value) return
    draft.value.fab_filters.start_date = Array.isArray(value) ? value[0] : null
    draft.value.fab_filters.end_date = Array.isArray(value) ? value[1] : null
  },
})

function clone(value: any) {
  return JSON.parse(JSON.stringify(value))
}

function selectCondition(condition: any) {
  activeCondition.value = condition
  draft.value = clone(condition)
  activeStep.value = 'fab'
}

async function loadPage() {
  await Promise.all([
    analysis.loadMetadata(),
    analysis.loadAnalysisSets(),
    analysis.loadAnalysisConditions(),
    binGroups.loadBinGroups(),
    conditionRules.loadConditionRules(),
  ])
  selectCondition(analysis.conditionLibrary.shared?.[0] || analysis.conditionLibrary.personal?.[0])
}

function updatePayload() {
  return {
    name: draft.value.name,
    process_key: draft.value.process_key,
    revision: draft.value.revision,
    fab_filters: draft.value.fab_filters,
    eds_filters: {
      ...draft.value.eds_filters,
      eds_status: 'actual_only',
      selected_bin_group_ids: draft.value.selected_bin_group_ids,
    },
    selected_bin_group_ids: draft.value.selected_bin_group_ids,
    condition_rule_id: draft.value.condition_rule_id,
    legend_config: {
      ...draft.value.legend_config,
      condition_rule_id: draft.value.condition_rule_id,
    },
  }
}

async function copyToPersonal() {
  if (!draft.value) return
  saving.value = true
  try {
    const copied = await analysis.copyConditionToPersonal(draft.value.id, {
      owner: 'demo.user',
      name: `${draft.value.name} 개인 복사본`,
    })
    libraryScope.value = 'personal'
    selectCondition(copied)
    ElMessage.success('개인 조건으로 복사했습니다')
  } finally {
    saving.value = false
  }
}

async function saveDraft() {
  if (!draft.value || !editable.value) return activeCondition.value
  saving.value = true
  try {
    const updated = await analysis.updateCondition(draft.value.id, updatePayload())
    selectCondition(updated)
    ElMessage.success('개인 조건을 저장했습니다')
    return updated
  } finally {
    saving.value = false
  }
}

async function goWindowReview() {
  if (!draft.value) return
  const condition = editable.value ? await saveDraft() : activeCondition.value
  const item = await analysis.createFromCondition(condition.id)
  binGroups.selectedBinGroupIds = condition.selected_bin_group_ids?.length ? condition.selected_bin_group_ids : ['BG001']
  conditionRules.selectedConditionRuleId = condition.condition_rule_id || 'CR001'
  ElMessage.success(`${item.name} 기준으로 Window Review를 준비했습니다`)
  router.push('/window-review')
}

onMounted(loadPage)
</script>
