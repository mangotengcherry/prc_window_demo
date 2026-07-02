<template>
  <div class="page-stack">
    <FilterPanel title="사용 가이드 / 시나리오 예시" subtitle="처음 사용하는 엔지니어가 어떤 메뉴부터 보면 되는지 업무 흐름 기준으로 안내합니다.">
      <div class="guide-hero">
        <div>
          <span class="guide-kicker">처음 시작할 때</span>
          <h2>먼저 “분석대상 선정 → Window Review” 순서로 보세요.</h2>
          <p>
            이 Workbench는 Spotfire를 대체하기보다, SPEC 적정성 검토에 반복되는 물량 정의,
            FAB-EDS 조인 관점, trade-off BIN Group, noise 제외, Pending 예측, 보고용 export를 한 흐름으로 묶는 용도입니다.
          </p>
        </div>
        <el-tag type="warning" effect="plain">Synthetic/mock data</el-tag>
      </div>
    </FilterPanel>

    <div class="page-grid two-col">
      <FilterPanel title="추천 사용 순서" subtitle="각 단계는 좌측 메뉴와 1:1로 대응됩니다.">
        <el-steps direction="vertical" :active="workflowSteps.length" finish-status="success" class="guide-steps">
          <el-step v-for="step in workflowSteps" :key="step.title" :title="step.title">
            <template #description>
              <strong>{{ step.menu }}</strong>
              <p>{{ step.body }}</p>
            </template>
          </el-step>
        </el-steps>
      </FilterPanel>

      <FilterPanel title="메뉴 용어 빠른 설명" subtitle="영문 도메인 용어는 유지하되, 의미를 바로 확인할 수 있게 정리했습니다.">
        <el-table :data="glossary" size="small">
          <el-table-column prop="term" label="용어" width="150" />
          <el-table-column prop="meaning" label="의미" min-width="260" />
        </el-table>
      </FilterPanel>
    </div>

    <FilterPanel title="대표 업무 시나리오" subtitle="실제 검토 Trigger별로 어느 메뉴를 어떤 순서로 보면 되는지 예시를 제공합니다.">
      <div class="scenario-grid">
        <section v-for="scenario in scenarios" :key="scenario.title" class="scenario-card">
          <div class="scenario-card__head">
            <h3>{{ scenario.title }}</h3>
            <p>{{ scenario.trigger }}</p>
          </div>
          <ol>
            <li v-for="step in scenario.path" :key="step">{{ step }}</li>
          </ol>
          <div class="scenario-outcome">
            <span>기대 결과</span>
            <p>{{ scenario.outcome }}</p>
          </div>
        </section>
      </div>
    </FilterPanel>
  </div>
</template>

<script setup lang="ts">
import FilterPanel from '../components/common/FilterPanel.vue'
import { guideGlossary, guideScenarios, guideWorkflowSteps } from '../guideContent.js'

const workflowSteps = guideWorkflowSteps
const scenarios = guideScenarios
const glossary = guideGlossary
</script>
