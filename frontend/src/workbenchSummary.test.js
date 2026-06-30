import assert from 'node:assert/strict'
import { test } from 'node:test'

import { summarizeWindowReview } from './workbenchSummary.js'
import { guideScenarios, guideWorkflowSteps } from './guideContent.js'

test('summarizeWindowReview keeps Korean candidate language cautious and unit-safe', () => {
  const summary = summarizeWindowReview({
    summary_metrics: {
      wafer_count: 3120,
      actual_wafer_count: 2700,
      pending_wafer_count: 420,
      correlation: 0.42,
      high_side_fail_rate: 0.0184,
      low_side_fail_rate: 0.0061,
      safe_window: { lower: 51.42, upper: 52.61 },
    },
    decision_candidates: [
      { type: 'SPEC 완화 검토 후보', basis: 'High-side fail rate rises.' },
    ],
    context: {
      x_parameter: 'metro_ch_hole_cd',
      bin_groups: [{ name: 'Hole-to-Hole' }],
    },
  })

  assert.equal(summary.waferText, '3,120매')
  assert.equal(summary.pendingText, 'Pending 420매')
  assert.equal(summary.failRateText, '1.84%')
  assert.equal(summary.safeWindowText, '51.42 ~ 52.61')
  assert.match(summary.primaryCandidate, /검토 후보/)
  assert.doesNotMatch(summary.primaryCandidate, /확정|승인/)
})

test('guide content gives first-time users scenario-oriented Korean navigation', () => {
  assert.ok(guideWorkflowSteps.length >= 6)
  assert.equal(guideWorkflowSteps[0].title, '1. 분석물량 선정')
  assert.equal(guideWorkflowSteps.some((step) => step.menu === 'Pending Prediction'), false)
  assert.ok(guideScenarios.some((scenario) => scenario.title.includes('SPEC 완화')))
  assert.ok(guideScenarios.some((scenario) => scenario.path.some((step) => step.includes('Window Review'))))
})
