<template>
  <div class="subscriptions">
    <div class="subs-card">
      <h1>{{ t('subs.title') }}</h1>
      <p class="desc">{{ t('subs.desc') }}</p>
      
      <!-- 创建订阅 -->
      <div class="create-sub">
        <h3>{{ t('subs.create') }}</h3>
        <div class="form-group">
          <label>{{ t('subs.query') }}</label>
          <textarea v-model="newSub.query" rows="2" :placeholder="t('subs.queryPlaceholder')"></textarea>
        </div>
        <div class="form-group">
          <label>{{ t('subs.domains') }}</label>
          <div class="domain-options">
            <button 
              v-for="d in domainOptions" 
              :key="d"
              :class="['domain-btn', { active: newSub.domains.includes(d) }]"
              @click="toggleDomain(d)"
            >
              {{ d }}
            </button>
          </div>
        </div>
        <button @click="createSub" :disabled="creating" class="btn-primary">
          {{ creating ? t('subs.creating') : t('subs.add') }}
        </button>
      </div>

      <!-- 订阅列表 -->
      <div class="subs-list">
        <h3>{{ t('subs.mySubs') }}</h3>
        <div v-if="subs.length === 0" class="empty">
          {{ t('subs.noSubs') }}
        </div>
        <div v-else v-for="sub in subs" :key="sub.id" class="sub-item">
          <div class="sub-content">
            <p>{{ sub.query }}</p>
            <div class="sub-domains">
              <span v-for="d in sub.domains" :key="d" class="domain-tag">{{ d }}</span>
            </div>
          </div>
          <button @click="deleteSub(sub.id)" class="delete-btn">🗑</button>
        </div>
      </div>

      <p v-if="message" :class="['message', messageType]">{{ message }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { i18n } from '../i18n.js'

const t = (key) => i18n.t(key)

const domainOptions = ['AI', 'tech', 'finance', 'crypto', 'healthcare', 'legal', 'real-estate', 'education', 'logistics', 'hr', 'marketing']

const newSub = reactive({ query: '', domains: [] })
const subs = ref([])
const creating = ref(false)
const message = ref('')
const messageType = ref('success')

const toggleDomain = (d) => {
  if (newSub.domains.includes(d)) {
    newSub.domains = newSub.domains.filter(x => x !== d)
  } else {
    newSub.domains.push(d)
  }
}

const createSub = async () => {
  if (!newSub.query) return
  creating.value = true
  message.value = ''
  
  try {
    const res = await fetch('/api/subscriptions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('synapse_token')}`
      },
      body: JSON.stringify(newSub)
    })
    const data = await res.json()
    
    if (data.code === 0) {
      message.value = t('subs.created')
      messageType.value = 'success'
      newSub.query = ''
      newSub.domains = []
      loadSubs()
    } else {
      message.value = data.msg
      messageType.value = 'error'
    }
  } catch (e) {
    message.value = 'Error'
    messageType.value = 'error'
  } finally {
    creating.value = false
  }
}

const deleteSub = async (id) => {
  try {
    await fetch(`/api/subscriptions/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('synapse_token')}` }
    })
    loadSubs()
  } catch (e) {
    console.error(e)
  }
}

const loadSubs = async () => {
  try {
    const res = await fetch('/api/subscriptions', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('synapse_token')}` }
    })
    const data = await res.json()
    subs.value = data.data?.subscriptions || []
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  loadSubs()
})
</script>

<style scoped>
.subscriptions { min-height: 60vh; display: flex; align-items: center; justify-content: center; padding: 32px 0; }
.subs-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 40px; width: 100%; max-width: 600px; }
.subs-card h1 { font-size: 24px; margin-bottom: 8px; text-align: center; }
.desc { color: var(--text-dim); text-align: center; margin-bottom: 32px; }

.create-sub { margin-bottom: 32px; padding-bottom: 24px; border-bottom: 1px solid var(--border); }
.create-sub h3 { font-size: 16px; margin-bottom: 16px; }

.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 8px; font-size: 14px; color: var(--text-dim); }
.form-group input, .form-group textarea { width: 100%; padding: 12px 14px; background: var(--bg-dark); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 14px; }
.form-group textarea:focus { outline: none; border-color: var(--primary); }

.domain-options { display: flex; flex-wrap: wrap; gap: 8px; }
.domain-btn { background: var(--bg-dark); border: 1px solid var(--border); color: var(--text-dim); padding: 6px 12px; border-radius: 16px; cursor: pointer; font-size: 12px; transition: all 0.2s; }
.domain-btn:hover { border-color: var(--primary); }
.domain-btn.active { background: var(--primary-dim); border-color: var(--primary); color: var(--primary); }

.btn-primary { width: 100%; background: linear-gradient(135deg, #00ff88, #00cc6a); color: #000; border: none; padding: 12px; font-size: 15px; font-weight: 600; border-radius: 8px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.subs-list h3 { font-size: 16px; margin-bottom: 16px; }
.sub-item { display: flex; align-items: flex-start; gap: 12px; padding: 16px; background: var(--bg-dark); border-radius: 8px; margin-bottom: 12px; }
.sub-content { flex: 1; }
.sub-content p { font-size: 14px; margin-bottom: 8px; }
.sub-domains { display: flex; gap: 6px; flex-wrap: wrap; }
.domain-tag { background: #222233; color: var(--text-dim); padding: 3px 8px; border-radius: 4px; font-size: 11px; }
.delete-btn { background: none; border: none; cursor: pointer; font-size: 16px; opacity: 0.6; }
.delete-btn:hover { opacity: 1; }

.empty { text-align: center; padding: 24px; color: var(--text-dim); font-size: 14px; }

.message { margin-top: 16px; padding: 12px; border-radius: 8px; text-align: center; font-size: 14px; }
.message.error { background: #ff444422; color: #ff4444; }
.message.success { background: #00ff8822; color: #00ff88; }
</style>
