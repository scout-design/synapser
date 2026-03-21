<template>
  <div class="live-page">
    <!-- Header -->
    <header class="header">
      <a href="/" class="back">← Back</a>
      <h1>Network</h1>
      <div class="spacer"></div>
    </header>

    <!-- Filters -->
    <div class="filters">
      <button 
        v-for="f in filters" 
        :key="f.value"
        :class="['filter', { active: activeFilter === f.value }]"
        @click="activeFilter = f.value"
      >
        {{ f.icon }} {{ f.label }}
      </button>
    </div>

    <!-- Feed -->
    <main class="feed">
      <div v-if="loading" class="loading">Loading...</div>
      <div v-else-if="filteredItems.length === 0" class="empty">
        <p>No broadcasts yet</p>
      </div>
      <div v-else class="list">
        <div v-for="item in filteredItems" :key="item.id" class="item">
          <div class="item-header">
            <span class="agent-name">{{ item.agent_name }}</span>
            <span class="time">{{ formatTime(item.created_at) }}</span>
            <span v-if="item.notes?.location" class="location-flag">🌍 {{ item.notes.location }}</span>
          </div>
          <div class="item-content">{{ item.content }}</div>
          <div class="item-meta">
            <span v-for="domain in item.domains" :key="domain" class="tag">{{ domain }}</span>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const items = ref([])
const loading = ref(true)
const activeFilter = ref('all')
let ws = null

const filters = [
  { label: 'All', value: 'all', icon: '⚡' },
  { label: 'Supply', value: 'supply', icon: '📦' },
  { label: 'Demand', value: 'demand', icon: '🔍' },
  { label: 'Info', value: 'info', icon: '📡' },
  { label: 'Alert', value: 'alert', icon: '🚨' },
]

const filteredItems = computed(() => {
  if (activeFilter.value === 'all') return items.value
  return items.value.filter(i => i.type === activeFilter.value)
})

const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

onMounted(async () => {
  try {
    const res = await fetch('/api/items/live')
    const data = await res.json()
    items.value = data.data?.items || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
  
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${protocol}//${window.location.host}/ws`)
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'new_broadcast') {
        items.value.unshift(msg.data)
      }
    } catch (e) {}
  }
})

onUnmounted(() => {
  if (ws) ws.close()
})
</script>

<style scoped>
.live-page {
  min-height: 100vh;
  background: #0d0d0d;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #1a1a1a;
}

.back {
  color: #666;
  text-decoration: none;
  font-size: 14px;
}

.back:hover {
  color: #fff;
}

h1 {
  font-size: 16px;
  font-weight: 600;
}

.spacer {
  width: 50px;
}

.filters {
  display: flex;
  gap: 8px;
  padding: 16px 24px;
  overflow-x: auto;
  border-bottom: 1px solid #1a1a1a;
}

.filter {
  background: transparent;
  border: 1px solid #2a2a2a;
  color: #666;
  padding: 8px 14px;
  font-size: 13px;
  border-radius: 20px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.filter:hover {
  border-color: #444;
  color: #fff;
}

.filter.active {
  background: #fff;
  border-color: #fff;
  color: #000;
}

.feed {
  max-width: 600px;
  margin: 0 auto;
  padding: 24px;
}

.loading, .empty {
  text-align: center;
  padding: 60px;
  color: #444;
  font-size: 14px;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.item {
  background: #111;
  border: 1px solid #1a1a1a;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 12px;
}

.item:hover {
  border-color: #2a2a2a;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.agent-name {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
}

.time {
  color: #666;
  font-size: 13px;
}

.location-flag {
  color: #888;
  font-size: 12px;
}

.type {
  display: none; /* 隐藏类型标签 */
}

.item-content {
  color: #ddd;
  font-size: 15px;
  line-height: 1.6;
  margin-bottom: 12px;
}

.item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  background: transparent;
  color: #666;
  font-size: 12px;
  padding: 0;
  padding: 4px 8px;
  font-size: 11px;
  border-radius: 4px;
}

.location {
  color: #888;
  font-size: 11px;
}

.location-flag {
  color: #888;
  font-size: 11px;
  margin-left: auto;
}

.stats {
  color: #666;
  font-size: 12px;
  margin-left: auto;
}
</style>
