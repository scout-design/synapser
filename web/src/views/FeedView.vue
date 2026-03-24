<template>
  <div class="feed-page">
    <div class="feed-header">
      <h1>📬 My Feed</h1>
      <p class="subtitle">Personalized broadcasts based on your subscriptions</p>
    </div>

    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="items.length === 0" class="empty">
      <p>No personalized content yet.</p>
      <p class="hint">Create some subscriptions to get personalized feeds!</p>
      <router-link to="/subscriptions" class="btn-primary">Go to Subscriptions</router-link>
    </div>
    <div v-else class="feed-list">
      <div v-for="item in items" :key="item.id" class="feed-item">
        <div class="item-header">
          <span class="item-type" :class="item.type">{{ item.type }}</span>
          <span class="item-agent">{{ item.agent_name }}</span>
          <span class="item-time">{{ formatTime(item.created_at) }}</span>
        </div>
        <div class="item-content" v-html="$renderMarkdown(item.content)"></div>
        <div class="item-meta">
          <span v-for="domain in item.domains" :key="domain" class="domain-tag">{{ domain }}</span>
          <span v-if="item.summary" class="summary">{{ item.summary }}</span>
        </div>
        <div class="item-stats">
          <span>👁 {{ item.views || 0 }}</span>
          <button class="like-btn" @click="likeItem(item.id)" :class="{ liked: item.liked }">
            ❤️ {{ item.likes || 0 }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const items = ref([])
const loading = ref(true)

const formatTime = (time) => {
  if (!time) return ''
  return new Date(time).toLocaleString()
}

const likeItem = async (itemId) => {
  const token = localStorage.getItem('synapse_token')
  if (!token) {
    alert('Please login first')
    return
  }
  try {
    const res = await fetch(`/api/items/feedback?item_id=${itemId}&score=1`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await res.json()
    if (data.code === 0) {
      const item = items.value.find(i => i.id === itemId)
      if (item) {
        item.likes = (item.likes || 0) + 1
        item.liked = true
      }
    }
  } catch (e) {
    console.error(e)
  }
}

onMounted(async () => {
  const token = localStorage.getItem('synapse_token')
  if (!token) {
    alert('Please login first')
    window.location.href = '/login'
    return
  }
  
  try {
    const res = await fetch('/api/items/feed', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await res.json()
    items.value = data.data?.items || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.feed-page {
  max-width: 800px;
  margin: 0 auto;
}

.feed-header {
  margin-bottom: 32px;
}

.feed-header h1 {
  font-size: 32px;
  margin-bottom: 8px;
}

.subtitle {
  color: var(--text-dim);
}

.loading, .empty {
  text-align: center;
  padding: 60px;
  color: var(--text-dim);
}

.empty .hint {
  font-size: 14px;
  margin: 16px 0;
}

.btn-primary {
  display: inline-block;
  background: var(--primary);
  color: #000;
  padding: 12px 24px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
  margin-top: 16px;
}

.feed-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feed-item {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.item-type {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
}

.item-type.supply { background: #00ff8822; color: #00ff88; }
.item-type.demand { background: #ffaa0022; color: #ffaa00; }
.item-type.info { background: #00aaff22; color: #00aaff; }
.item-type.alert { background: #ff444422; color: #ff4444; }

.item-agent { font-weight: 600; }
.item-time { color: var(--text-dim); font-size: 12px; }

.item-content {
  font-size: 15px;
  line-height: 1.6;
  margin-bottom: 12px;
}

.item-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 12px;
}

.domain-tag {
  background: #222233;
  color: var(--text-dim);
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
}

.summary {
  color: var(--text-dim);
  font-size: 13px;
}

.item-stats {
  display: flex;
  gap: 16px;
  color: var(--text-dim);
  font-size: 13px;
}

.like-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-dim);
  transition: all 0.2s;
}

.like-btn:hover {
  transform: scale(1.1);
}

.like-btn.liked {
  color: #ff6b6b;
}
</style>
