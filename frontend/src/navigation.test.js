import test from 'node:test'
import assert from 'node:assert/strict'
import { getWorkbenchNavItems } from './navigation.js'

test('workbench navigation consolidates setup into analysis selection and hides pending prediction', () => {
  const labels = getWorkbenchNavItems().map((item) => item.label)

  assert.deepEqual(labels, ['사용 가이드', '분석물량 선정', 'Window Review', 'Export / Report'])
  assert.equal(labels.includes('분석 물량'), false)
  assert.equal(labels.includes('BIN Group'), false)
  assert.equal(labels.includes('조건 Rule'), false)
  assert.equal(labels.includes('Pending 예측'), false)
})
