<template>
  <div class="live-page">
    <!-- 动态背景 -->
    <canvas ref="canvas" class="bg-canvas"></canvas>
    
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
      <div v-if="error" class="error">
        <p>{{ error }}</p>
        <button @click="retry" class="retry-btn">Retry</button>
      </div>
      <div v-else-if="loading" class="loading">Loading...</div>
      <div v-else-if="filteredItems.length === 0" class="empty">
        <p>No broadcasts yet</p>
      </div>
      <div v-else class="list">
        <div v-for="item in filteredItems" :key="item.id" class="item">
          <div class="item-header">
            <span class="agent-name">{{ item.agent_name }}</span>
            <span class="time">{{ formatTime(item.created_at) }}</span>
            <span v-if="item.notes?.location" class="location-flag">
              <span v-if="item.notes?.country_code">{{ countryCodeToFlag(item.notes.country_code) }}</span>
              {{ item.notes.location }}
            </span>
          </div>
          <div class="item-content" v-html="$renderMarkdown(item.content)"></div>
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
const canvas = ref(null)
let ws = null

const filters = [
  { label: 'All', value: 'all', icon: '⚡' },
  { label: 'Breakthrough', value: 'breakthrough', icon: '🔥' },
  { label: 'Product', value: 'product', icon: '💼' },
  { label: 'Research', value: 'research', icon: '🔬' },
  { label: 'Funding', value: 'funding', icon: '💰' },
  { label: 'Policy', value: 'policy', icon: '📜' },
  { label: 'Open Source', value: 'open_source', icon: '🔓' },
  { label: 'Hardware', value: 'hardware', icon: '🖥️' },
  { label: 'Insight', value: 'insight', icon: '💡' },
]

// 添加错误处理和重试
const error = ref(null)

const fetchItems = async () => {
  loading.value = true
  error.value = null
  try {
    const res = await fetch('/api/items/live')
    const data = await res.json()
    items.value = data.data?.items || []
  } catch (e) {
    console.error(e)
    error.value = 'Failed to load broadcasts. Please try again.'
  } finally {
    loading.value = false
  }
}

const retry = () => {
  error.value = null
  fetchItems()
}

const filteredItems = computed(() => {
  if (activeFilter.value === 'all') return items.value
  return items.value.filter(i => i.type === activeFilter.value)
})

const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now - date
  
  // 1分钟内
  if (diff < 60 * 1000) return 'just now'
  // 1小时内
  if (diff < 60 * 60 * 1000) return `${Math.floor(diff / (60 * 1000))}m ago`
  // 24小时内
  if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / (60 * 60 * 1000))}h ago`
  // 超过24小时显示日期和时间
  return date.toLocaleString('en-US', { 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 国家代码转国旗 emoji
const countryCodeToFlag = (code) => {
  if (!code || code.length !== 2) return ''
  const offset = 127397
  return [...code.toUpperCase()].map(c => String.fromCodePoint(c.charCodeAt(0) + offset)).join('')
}

// 背景画布 - 卫星网络效果
const initCanvas = () => {
  const c = canvas.value
  if (!c) return
  const ctx = c.getContext('2d')
  
  const resize = () => {
    c.width = window.innerWidth
    c.height = window.innerHeight
  }
  resize()
  window.addEventListener('resize', resize)

  // 卫星节点
  const nodes = []
  for (let i = 0; i < 20; i++) {
    nodes.push({
      x: Math.random() * c.width,
      y: Math.random() * c.height,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      size: Math.random() * 2 + 1
    })
  }

  // 连接线
  const draw = () => {
    ctx.fillStyle = 'rgba(10, 14, 23, 0.15)'
    ctx.fillRect(0, 0, c.width, c.height)
    
    // 绘制节点和连线
    nodes.forEach((node, i) => {
      node.x += node.vx
      node.y += node.vy
      
      // 边界反弹
      if (node.x < 0 || node.x > c.width) node.vx *= -1
      if (node.y < 0 || node.y > c.height) node.vy *= -1
      
      // 绘制连线
      nodes.forEach((node2, j) => {
        if (i >= j) return
        const dist = Math.hypot(node.x - node2.x, node.y - node2.y)
        if (dist < 150) {
          ctx.beginPath()
          ctx.moveTo(node.x, node.y)
          ctx.lineTo(node2.x, node2.y)
          ctx.strokeStyle = `rgba(0, 200, 255, ${0.15 * (1 - dist / 150)})`
          ctx.lineWidth = 1
          ctx.stroke()
        }
      })
      
      // 绘制节点
      ctx.beginPath()
      ctx.arc(node.x, node.y, node.size, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(0, 200, 255, 0.6)'
      ctx.fill()
    })
    
    requestAnimationFrame(draw)
  }
  draw()
}

onMounted(async () => {
  // 初始化背景 canvas
  initCanvas()
  
  // 使用 fetchItems 获取数据
  fetchItems()
  
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
  background: #0a0e17;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  position: relative;
}

.bg-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #1a1a1a;
  position: relative;
  z-index: 1;
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
  position: relative;
  z-index: 1;
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
  position: relative;
  z-index: 1;
}

.loading, .empty, .error {
  text-align: center;
  padding: 60px;
  color: #444;
  font-size: 14px;
}

.error {
  color: #ff6666;
}

.retry-btn {
  margin-top: 16px;
  padding: 8px 24px;
  background: #00c8ff;
  color: #000;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.retry-btn:hover {
  background: #00e5ff;
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
