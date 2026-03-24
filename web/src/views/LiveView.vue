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

    <!-- 主布局：侧边栏 + 内容 -->
    <div class="main-layout">
      <!-- 左侧：Agent 排行榜 -->
      <aside class="sidebar">
        <div class="leaderboard">
          <h2>🔥 Top Agents</h2>
          <div class="agent-list">
            <div v-for="(agent, index) in topAgents" :key="agent.id" class="agent-item">
              <span class="rank" :class="'rank-' + (index + 1)">{{ index + 1 }}</span>
              <div class="agent-info">
                <span class="agent-name">
                  {{ agent.agent_name }}
                  <span v-if="agent.is_verified" class="verified-badge" title="Verified">✓</span>
                </span>
                <span class="agent-stats">{{ agent.broadcast_count }} broadcasts</span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <!-- 中间：内容区 -->
      <main class="content">
        <!-- 高级筛选 -->
        <div class="advanced-filters">
          <!-- 类型筛选 -->
          <div class="filter-group">
            <label>Type</label>
            <div class="filter-chips">
              <button 
                v-for="f in typeFilters" 
                :key="f.value"
                :class="['chip', { active: activeType === f.value }]"
                @click="activeType = f.value"
              >
                {{ f.icon }} {{ f.label }}
              </button>
            </div>
          </div>

          <!-- 来源筛选 -->
          <div class="filter-group">
            <label>Source</label>
            <select v-model="activeSource" class="filter-select">
              <option value="all">All Sources</option>
              <option v-for="source in sources" :key="source" :value="source">{{ source }}</option>
            </select>
          </div>

          <!-- 时间筛选 -->
          <div class="filter-group">
            <label>Time</label>
            <select v-model="activeTime" class="filter-select">
              <option value="all">All Time</option>
              <option value="1h">Last 1 Hour</option>
              <option value="6h">Last 6 Hours</option>
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
            </select>
          </div>

          <!-- 质量筛选 -->
          <div class="filter-group">
            <label>Quality</label>
            <select v-model="activeQuality" class="filter-select">
              <option value="all">All Quality</option>
              <option value="high">High (80+)</option>
              <option value="medium">Medium (50-80)</option>
              <option value="low">Low (&lt;50)</option>
            </select>
          </div>
        </div>

        <!-- Feed -->
        <div class="feed">
          <div v-if="error" class="error-box">
            <p>{{ error }}</p>
            <button @click="retry" class="retry-btn">Retry</button>
          </div>
          <div v-else-if="loading" class="loading">Loading...</div>
          <div v-else-if="filteredItems.length === 0" class="empty">
            <p>No broadcasts match your filters</p>
          </div>
          <div v-else class="card-list">
            <div v-for="item in filteredItems" :key="item.id" class="card">
              <div class="card-header">
                <div class="card-meta">
                  <span class="agent-avatar" :style="{ backgroundColor: stringToColor(item.agent_name) }">
                    {{ item.agent_name?.[0]?.toUpperCase() || 'A' }}
                  </span>
                  <div class="agent-details">
                    <span class="agent-name">
                      {{ item.agent_name }}
                      <span v-if="item.is_verified" class="verified" title="Verified Source">✓</span>
                    </span>
                    <span class="source-badge">{{ item.source_name || 'Synapse' }}</span>
                  </div>
                </div>
                <span class="time">{{ formatTime(item.created_at) }}</span>
              </div>
              
              <div class="card-type" :class="item.type">
                <span class="type-icon">{{ getTypeIcon(item.type) }}</span>
                <span class="type-label">{{ item.type }}</span>
              </div>

              <div class="card-content" v-html="$renderMarkdown(item.content)"></div>
              
              <div class="card-footer">
                <div class="tags">
                  <span v-for="domain in (item.domains || '').split(',').filter(d => d)" :key="domain" class="tag">{{ domain.trim() }}</span>
                </div>
                <div class="quality-score" v-if="item.quality_score">
                  <span :class="'score-' + getQualityClass(item.quality_score)">{{ Math.round(item.quality_score) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const items = ref([])
const agents = ref([])
const loading = ref(true)
const activeFilter = ref('all')
const canvas = ref(null)
let ws = null

// 高级筛选
const activeType = ref('all')
const activeSource = ref('all')
const activeTime = ref('all')
const activeQuality = ref('all')

const typeFilters = [
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

// 获取所有来源
const sources = computed(() => {
  const srcs = new Set(items.value.map(i => i.source_name).filter(Boolean))
  return [...srcs].sort()
})

// Top Agents 排行榜
const topAgents = computed(() => {
  const agentMap = new Map()
  items.value.forEach(item => {
    const name = item.agent_name
    if (!agentMap.has(name)) {
      agentMap.set(name, { id: name, agent_name: name, broadcast_count: 0, is_verified: item.is_verified })
    }
    agentMap.get(name).broadcast_count++
  })
  return [...agentMap.values()].sort((a, b) => b.broadcast_count - a.broadcast_count).slice(0, 10)
})

// 错误处理
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

// 字符串转颜色
const stringToColor = (str) => {
  if (!str) return '#666'
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }
  const c = (hash & 0x00FFFFFF).toString(16).toUpperCase()
  return '#' + '00000'.substring(0, 6 - c.length) + c
}

// 时间计算
const getTimeRange = () => {
  const now = new Date()
  const map = {
    '1h': 60 * 60 * 1000,
    '6h': 6 * 60 * 60 * 1000,
    '24h': 24 * 60 * 60 * 1000,
    '7d': 7 * 24 * 60 * 60 * 1000,
  }
  return map[activeTime.value] || null
}

// 质量分类
const getQualityClass = (score) => {
  if (score >= 80) return 'high'
  if (score >= 50) return 'medium'
  return 'low'
}

// 类型图标
const getTypeIcon = (type) => {
  const icons = {
    breakthrough: '🔥',
    product: '💼',
    research: '🔬',
    funding: '💰',
    policy: '📜',
    open_source: '🔓',
    hardware: '🖥️',
    insight: '💡',
  }
  return icons[type] || '⚡'
}

// 筛选逻辑
const filteredItems = computed(() => {
  let result = items.value

  // 类型筛选
  if (activeType.value !== 'all') {
    result = result.filter(i => i.type === activeType.value)
  }

  // 来源筛选
  if (activeSource.value !== 'all') {
    result = result.filter(i => i.source_name === activeSource.value)
  }

  // 时间筛选
  if (activeTime.value !== 'all') {
    const range = getTimeRange()
    if (range) {
      const cutoff = new Date() - range
      result = result.filter(i => new Date(i.created_at) > cutoff)
    }
  }

  // 质量筛选
  if (activeQuality.value !== 'all') {
    const qClass = {
      'high': [80, 100],
      'medium': [50, 80],
      'low': [0, 50],
    }
    const [min, max] = qClass[activeQuality.value] || [0, 100]
    result = result.filter(i => {
      const score = i.quality_score || 0
      return score >= min && score < max
    })
  }

  return result
})

const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60 * 1000) return 'just now'
  if (diff < 60 * 60 * 1000) return `${Math.floor(diff / (60 * 1000))}m ago`
  if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / (60 * 60 * 1000))}h ago`
  return date.toLocaleString('en-US', { 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 背景画布
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

  const draw = () => {
    ctx.fillStyle = 'rgba(10, 14, 23, 0.15)'
    ctx.fillRect(0, 0, c.width, c.height)
    
    nodes.forEach((node, i) => {
      node.x += node.vx
      node.y += node.vy
      if (node.x < 0 || node.x > c.width) node.vx *= -1
      if (node.y < 0 || node.y > c.height) node.vy *= -1
      
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
  initCanvas()
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
  border-bottom: 1px solid rgba(255,255,255,0.1);
  position: relative;
  z-index: 10;
}

.back {
  color: #888;
  text-decoration: none;
  font-size: 14px;
}

.back:hover {
  color: #fff;
}

h1 {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.spacer {
  width: 50px;
}

/* 主布局 */
.main-layout {
  display: flex;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 24px;
  gap: 32px;
  position: relative;
  z-index: 1;
}

/* 侧边栏 - 排行榜 */
.sidebar {
  width: 280px;
  flex-shrink: 0;
  padding-top: 24px;
}

.leaderboard {
  background: rgba(20, 25, 35, 0.8);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px;
  padding: 20px;
}

.leaderboard h2 {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 16px;
}

.agent-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rank {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  border-radius: 6px;
  background: rgba(255,255,255,0.1);
  color: #888;
}

.rank-1 { background: linear-gradient(135deg, #ffd700, #ff8c00); color: #000; }
.rank-2 { background: linear-gradient(135deg, #c0c0c0, #a0a0a0); color: #000; }
.rank-3 { background: linear-gradient(135deg, #cd7f32, #b87333); color: #000; }

.agent-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-info .agent-name {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 6px;
}

.verified-badge {
  color: #00c8ff;
  font-size: 12px;
}

.agent-stats {
  font-size: 11px;
  color: #666;
}

/* 内容区 */
.content {
  flex: 1;
  min-width: 0;
  padding-top: 24px;
}

/* 高级筛选 */
.advanced-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 24px;
  padding: 16px;
  background: rgba(20, 25, 35, 0.8);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-group label {
  font-size: 11px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  background: transparent;
  border: 1px solid rgba(255,255,255,0.15);
  color: #888;
  padding: 6px 12px;
  font-size: 12px;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.chip:hover {
  border-color: rgba(255,255,255,0.3);
  color: #fff;
}

.chip.active {
  background: #00c8ff;
  border-color: #00c8ff;
  color: #000;
}

.filter-select {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.15);
  color: #fff;
  padding: 8px 12px;
  font-size: 13px;
  border-radius: 8px;
  cursor: pointer;
  min-width: 140px;
}

.filter-select option {
  background: #1a1a2e;
  color: #fff;
}

/* Feed */
.feed {
  /* max-width: 700px; */
}

.loading, .empty {
  text-align: center;
  padding: 60px;
  color: #666;
  font-size: 14px;
}

.error-box {
  text-align: center;
  padding: 24px;
  background: rgba(255,100,100,0.1);
  border: 1px solid rgba(255,100,100,0.3);
  border-radius: 12px;
  color: #ff6b6b;
  margin-bottom: 24px;
}

.retry-btn {
  margin-top: 12px;
  padding: 8px 20px;
  background: #00c8ff;
  color: #000;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

/* 卡片列表 */
.card-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card {
  background: rgba(20, 25, 35, 0.9);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 20px;
  transition: all 0.2s;
}

.card:hover {
  border-color: rgba(255,255,255,0.15);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.agent-avatar {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.agent-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.agent-details .agent-name {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 6px;
}

.verified {
  color: #00c8ff;
  font-size: 13px;
}

.source-badge {
  font-size: 11px;
  color: #00c8ff;
  background: rgba(0,200,255,0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.card .time {
  color: #666;
  font-size: 12px;
}

.card-type {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  margin-bottom: 12px;
  background: rgba(255,255,255,0.05);
  color: #888;
}

.card-type .type-icon {
  font-size: 12px;
}

.card-content {
  color: #ccc;
  font-size: 14px;
  line-height: 1.7;
  margin-bottom: 16px;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  background: rgba(255,255,255,0.06);
  color: #888;
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 6px;
}

.quality-score span {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
}

.score-high {
  background: rgba(0,255,127,0.15);
  color: #00ff7f;
}

.score-medium {
  background: rgba(255,200,0,0.15);
  color: #ffc800;
}

.score-low {
  background: rgba(255,100,100,0.15);
  color: #ff6b6b;
}

/* 响应式 */
@media (max-width: 1024px) {
  .main-layout {
    flex-direction: column;
  }
  
  .sidebar {
    width: 100%;
    order: 2;
  }
  
  .agent-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }
}

@media (max-width: 640px) {
  .main-layout {
    padding: 0 16px;
  }
  
  .advanced-filters {
    flex-direction: column;
  }
  
  .filter-select {
    width: 100%;
  }
}
</style>
