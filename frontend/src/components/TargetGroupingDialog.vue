<script setup>
// Y target 합산 그룹 생성 다이얼로그. 이름 입력 + 중복 시 덮어쓰기/이름변경/취소.
import { ref, computed, watch } from 'vue'

const props = defineProps({
  sources: { type: Array, default: () => [] },       // 합산할 원본 target 이름들
  existingNames: { type: Array, default: () => [] },  // 기존 그룹 이름(중복 검사)
})
const emit = defineEmits(['create', 'close'])

const suggested = computed(() => props.sources.join('_') + '_SUM')
const name = ref(suggested.value)
watch(() => props.sources, () => { name.value = suggested.value }, { immediate: true })

const askOverwrite = ref(false)
watch(name, () => { askOverwrite.value = false })  // 이름 바꾸면 중복 경고 해제

function submit() {
  const nm = name.value.trim()
  if (!nm) return
  if (props.existingNames.includes(nm) && !askOverwrite.value) { askOverwrite.value = true; return }
  emit('create', { name: nm, sources: [...props.sources], agg: 'sum' })
}
</script>

<template>
  <div class="ov" @click.self="emit('close')">
    <div class="card">
      <h4>합산 target 만들기</h4>
      <p class="src">{{ sources.join(' + ') }} <span class="agg">합산(sum)</span></p>
      <label class="fld">새 target 이름
        <input v-model="name" @keyup.enter="submit" autofocus />
      </label>
      <p v-if="askOverwrite" class="dup">이미 같은 이름의 그룹이 있습니다.</p>
      <div class="actions">
        <template v-if="askOverwrite">
          <button class="ghost" @click="emit('close')">취소</button>
          <button class="ghost" @click="askOverwrite = false">이름 변경</button>
          <button class="primary" @click="emit('create', { name: name.trim(), sources: [...sources], agg: 'sum' })">덮어쓰기</button>
        </template>
        <template v-else>
          <button class="ghost" @click="emit('close')">취소</button>
          <button class="primary" :disabled="!name.trim()" @click="submit">만들기</button>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ov { position: fixed; inset: 0; background: rgba(17,17,26,.38); backdrop-filter: blur(2px); display: flex; align-items: center; justify-content: center; z-index: 50; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow); padding: 20px; width: 320px; display: flex; flex-direction: column; gap: 12px; }
h4 { margin: 0; font-size: 15px; font-weight: 600; }
.src { margin: 0; font-size: 12px; color: var(--text-2); background: var(--surface-2); padding: 8px 11px; border-radius: 9px; line-height: 1.5; }
.agg { font-weight: 700; color: var(--accent); }
.fld { display: flex; flex-direction: column; gap: 4px; font-size: 11px; color: var(--text-2); font-weight: 600; }
.fld input { padding: 8px 10px; font-size: 13px; border-radius: 9px; border: 1px solid var(--border); background: #fff; outline: none; }
.fld input:focus { border-color: var(--accent); box-shadow: var(--ring); }
.dup { margin: 0; font-size: 12px; color: #b45309; }
.actions { display: flex; justify-content: flex-end; gap: 8px; }
.actions button { padding: 8px 14px; font-size: 13px; font-weight: 600; border-radius: 9px; cursor: pointer; border: 1px solid var(--border); }
.ghost { background: #fff; color: var(--text-2); }
.primary { background: linear-gradient(135deg, var(--accent-2), var(--accent)); color: #fff; border: none; }
.primary:disabled { opacity: .45; cursor: not-allowed; }
</style>
