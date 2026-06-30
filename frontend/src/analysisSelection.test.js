import test from 'node:test'
import assert from 'node:assert/strict'
import {
  conditionScopeLabel,
  describePeriod,
  isEditableCondition,
  nextStepKey,
  summarizeCondition,
} from './analysisSelection.js'

test('analysis selection helpers distinguish shared readonly and personal editable conditions', () => {
  const shared = {
    scope: 'shared',
    readonly: true,
    process_key: 'Ch.Hole',
    revision: 'rev1',
    fab_filters: { date_mode: 'fixed', start_date: '2026-02-01', end_date: '2026-03-31' },
    analysis_filters: { product: ['DRAM_A'], step: ['ETCH_CONTACT'], eds_status: 'actual_only' },
    selected_bin_group_ids: ['BG001', 'BG002'],
    legend_config: { basis: 'Part modification' },
  }
  const personal = { ...shared, scope: 'personal', readonly: false }

  assert.equal(conditionScopeLabel(shared), '공유 조건')
  assert.equal(conditionScopeLabel(personal), '개인 조건')
  assert.equal(isEditableCondition(shared), false)
  assert.equal(isEditableCondition(personal), true)
  assert.equal(describePeriod(shared.fab_filters), '2026-02-01 ~ 2026-03-31')
  assert.equal(summarizeCondition(shared).edsStatus, 'EDS 확보 물량만')
})

test('analysis selection helpers describe recent-day conditions and wizard step order', () => {
  const condition = {
    scope: 'personal',
    readonly: false,
    process_key: 'Ch.Hole',
    revision: 'recent-30d',
    fab_filters: { date_mode: 'recent_days', recent_days: 30 },
    analysis_filters: { product: ['DRAM_A'], step: ['ETCH_CONTACT'], eds_status: 'actual_only' },
    selected_bin_group_ids: ['BG001'],
    legend_config: { basis: 'Tool/Chamber' },
  }

  assert.equal(describePeriod(condition.fab_filters), '최근 30일')
  assert.equal(summarizeCondition(condition).title, 'Ch.Hole / recent-30d')
  assert.equal(nextStepKey('fab'), 'eds')
  assert.equal(nextStepKey('eds'), 'legend')
  assert.equal(nextStepKey('legend'), 'legend')
})
