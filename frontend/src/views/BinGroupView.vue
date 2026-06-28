<template>
  <div class="page-grid two-col">
    <FilterPanel title="BIN Group 정의" subtitle="600개 EDS BIN 중 단일 BIN 또는 sum group으로 Failure Mode metric을 만듭니다.">
      <el-form label-position="top" class="dense-form">
        <div class="form-grid">
          <el-form-item label="Group 이름">
            <el-input v-model="form.name" />
          </el-form-item>
          <el-form-item label="Failure mode">
            <el-input v-model="form.failure_mode" />
          </el-form-item>
          <el-form-item label="Wafer Zone">
            <el-select v-model="form.zone" clearable placeholder="전체 zone">
              <el-option v-for="zone in metadata?.zones || []" :key="zone" :label="zone" :value="zone" />
            </el-select>
          </el-form-item>
          <el-form-item label="EDS BIN item">
            <el-select v-model="form.bin_ids" multiple filterable collapse-tags collapse-tags-tooltip>
              <el-option v-for="bin in metadata?.bin_list || []" :key="bin" :label="bin" :value="bin" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="설명">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-button :icon="Plus" type="primary" @click="createGroup">BIN Group 저장</el-button>
      </el-form>
    </FilterPanel>

    <FilterPanel title="사용 가능한 BIN Group" subtitle="기본 group은 Ch.Hole high-side / low-side trade-off를 함께 보도록 구성되어 있습니다.">
      <el-table :data="groups.binGroups" size="small" @selection-change="groups.selectedBinGroupIds = $event.map((row:any) => row.id)">
        <el-table-column type="selection" width="44" />
        <el-table-column prop="id" label="ID" width="76" />
        <el-table-column prop="name" label="이름" min-width="170" />
        <el-table-column prop="failure_mode" label="Failure mode" min-width="150" />
        <el-table-column label="BIN 구성" min-width="220">
          <template #default="{ row }">{{ row.bin_ids.join(' + ') }}</template>
        </el-table-column>
        <el-table-column prop="zone" label="Zone" width="88" />
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
import { useBinGroupStore } from '../stores/binGroupStore'

const analysis = useAnalysisSetStore()
const groups = useBinGroupStore()
const metadata = computed(() => analysis.metadata)
const form = reactive({
  name: 'Custom failure mode',
  description: 'Summed EDS BIN group for window review.',
  failure_mode: 'Custom',
  bin_ids: ['BIN_014'],
  zone: null,
})

async function createGroup() {
  const item = await groups.create({ ...form })
  ElMessage.success(`${item.name} 저장 완료`)
}
</script>
