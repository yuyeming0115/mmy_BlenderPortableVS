<template>
  <div class="grid">
    <!-- 数据卡片 -->
    <div
      v-for="item in items"
      :key="item.id"
      class="card"
      :class="{ active: item.id === activeId }"
      @click="emit('click', item)"
      @contextmenu.prevent="e => openMenu(e, item)"
    >
      <div class="icon-wrap">
        <span class="icon">{{ item.icon || item.name?.charAt(0) || '?' }}</span>
      </div>
      <div class="label">{{ item.name }}</div>
      <div v-if="item.id === activeId" class="badge">✓</div>
    </div>

    <!-- 添加卡片 -->
    <div class="card add-card" @click="emit('add')">
      <div class="icon-wrap"><div class="icon">+</div></div>
      <div class="label">{{ t('add_new') }}</div>
    </div>
  </div>

  <!-- 右键菜单 -->
  <n-dropdown
    trigger="manual"
    :x="menuX"
    :y="menuY"
    :show="menuVisible"
    :options="menuOptions"
    @clickoutside="menuVisible = false"
    @select="onMenuSelect"
  />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { CardItem } from '../stores/app'

const { t } = useI18n()

// TODO: 根据你的数据类型修改 CardItem
interface CardItem {
  id: string
  name: string
  icon?: string
}

const props = defineProps<{
  items: CardItem[]
  activeId?: string
}>()

const emit = defineEmits<{
  click: [item: CardItem]
  edit: [item: CardItem]
  delete: [item: CardItem]
  add: []
}>()

const menuVisible = ref(false)
const menuX = ref(0)
const menuY = ref(0)
const menuTarget = ref<CardItem | null>(null)

const menuOptions = [
  { label: () => t('edit'), key: 'edit' },
  { label: () => t('delete'), key: 'delete', props: { style: 'color:#d03050' } },
]

function openMenu(e: MouseEvent, item: CardItem) {
  menuTarget.value = item
  menuX.value = e.clientX
  menuY.value = e.clientY
  menuVisible.value = true
}

function onMenuSelect(key: string) {
  menuVisible.value = false
  if (!menuTarget.value) return
  if (key === 'edit') emit('edit', menuTarget.value)
  else if (key === 'delete') emit('delete', menuTarget.value)
}
</script>

<style scoped>
.grid { display: flex; flex-wrap: wrap; gap: 14px; padding: 8px 0; }
.card {
  width: 108px;
  min-height: 100px;
  border-radius: 14px;
  border: 2px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding: 14px 8px 10px;
  cursor: pointer;
  position: relative;
  transition: border-color .2s, box-shadow .2s;
  background: #fff;
}
.card:hover {
  border-color: #18a058;
  box-shadow: 0 3px 10px rgba(24,160,88,0.16);
  transform: translateY(-1px);
}
.card.active {
  border-color: #18a058;
  background: #f0faf5;
}

/* 深色模式 */
body.dark .card { background: #2a2a2a; border-color: #444; }
body.dark .card:hover { border-color: #18a058; }
body.dark .card.active { background: #1a3a28; border-color: #18a058; }
body.dark .label { color: #ccc; }

.icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 13px;
  border: 1.5px solid #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
  background: linear-gradient(135deg, #f8f8f8, #eee);
}
body.dark .icon-wrap {
  background: linear-gradient(135deg, #333, #3a3a3a);
  border-color: #555;
}
.card:hover .icon-wrap,
.card.active .icon-wrap {
  border-color: #18a05860;
  box-shadow: 0 2px 6px rgba(24,160,88,0.15);
}
.icon {
  font-size: 18px;
  line-height: 1;
  color: #555;
  font-weight: 700;
}
body.dark .icon { color: #ccc; }

.label {
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  color: #444;
  max-width: 90px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
}

.badge {
  position: absolute;
  top: 5px;
  right: 7px;
  color: #18a058;
  font-size: 14px;
  font-weight: 700;
}

.add-card {
  border-style: dashed;
  background: #fafafa;
}
body.dark .add-card { background: #222; }
.add-card .icon { color: #bbb; font-size: 26px; }
.add-card .icon-wrap { background: none; border-style: dashed; }
</style>