<template>
  <div class="publish">
    <div class="publish-card">
      <h1>{{ t('publish.title') }}</h1>
      <p class="desc">{{ t('publish.desc') }}</p>
      
      <div class="form-group">
        <label>{{ t('publish.type') }}</label>
        <div class="type-options">
          <button 
            v-for="t in types" 
            :key="t.value"
            :class="['type-btn', { active: form.type === t.value }]"
            @click="form.type = t.value"
          >
            {{ t.icon }} {{ t.label }}
          </button>
        </div>
      </div>

      <div class="form-group">
        <label>{{ t('publish.content') }}</label>
        <textarea 
          v-model="form.content" 
          :placeholder="t('publish.contentPlaceholder')"
          rows="4"
        ></textarea>
      </div>

      <div class="form-group">
        <label>{{ t('publish.summary') }}</label>
        <input v-model="form.summary" :placeholder="t('publish.summaryPlaceholder')" />
      </div>

      <div class="form-group">
        <label>{{ t('publish.domains') }}</label>
        <div class="domain-options">
          <button 
            v-for="d in domainOptions" 
            :key="d"
            :class="['domain-btn', { active: form.domains.includes(d) }]"
            @click="toggleDomain(d)"
          >
            {{ d }}
          </button>
        </div>
      </div>

      <div class="form-group">
        <label>{{ t('publish.expire') }}</label>
        <select v-model="form.expireDays">
          <option value="1">1 {{ t('publish.day') }}</option>
          <option value="3">3 {{ t('publish.days') }}</option>
          <option value="7">7 {{ t('publish.days') }}</option>
          <option value="30">30 {{ t('publish.days') }}</option>
        </select>
      </div>

      <button @click="publish" :disabled="publishing" class="btn-primary">
        {{ publishing ? t('publish.publishing') : t('publish.submit') }}
      </button>

      <p v-if="message" :class="['message', messageType]">{{ message }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { i18n } from '../i18n.js'

const router = useRouter()
const t = (key) => i18n.t(key)

const types = [
  { value: 'supply', label: 'Supply', icon: '📦' },
  { value: 'demand', label: 'Demand', icon: '🔍' },
  { value: 'info', label: 'Info', icon: '📡' },
  { value: 'alert', label: 'Alert', icon: '🚨' }
]

const domainOptions = ['AI', 'tech', 'finance', 'crypto', 'healthcare', 'legal', 'real-estate', 'education', 'logistics', 'hr', 'marketing']

const form = reactive({
  type: 'info',
  content: '',
  summary: '',
  domains: [],
  expireDays: '7'
})

const publishing = ref(false)
const message = ref('')
const messageType = ref('success')

const toggleDomain = (d) => {
  if (form.domains.includes(d)) {
    form.domains = form.domains.filter(x => x !== d)
  } else if (form.domains.length < 3) {
    form.domains.push(d)
  }
}

const publish = async () => {
  if (!form.content || !form.summary) {
    message.value = 'Please fill in content and summary'
    messageType.value = 'error'
    return
  }

  publishing.value = true
  message.value = ''

  try {
    const notes = JSON.stringify({
      type: form.type,
      domains: form.domains,
      summary: form.summary,
      expire_time: new Date(Date.now() + form.expireDays * 86400000).toISOString(),
      source_type: 'original'
    })

    const res = await fetch('/api/items/publish', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('synapse_token')}`
      },
      body: JSON.stringify({ content: form.content, notes })
    })

    const data = await res.json()
    
    if (data.code === 0) {
      message.value = 'Broadcast published!'
      messageType.value = 'success'
      setTimeout(() => router.push('/'), 1500)
    } else {
      message.value = data.msg
      messageType.value = 'error'
    }
  } catch (e) {
    message.value = 'Failed to publish'
    messageType.value = 'error'
  } finally {
    publishing.value = false
  }
}
</script>

<style scoped>
.publish { min-height: 60vh; display: flex; align-items: center; justify-content: center; padding: 32px 0; }
.publish-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 40px; width: 100%; max-width: 600px; }
.publish-card h1 { font-size: 24px; margin-bottom: 8px; text-align: center; }
.desc { color: var(--text-dim); text-align: center; margin-bottom: 32px; }

.form-group { margin-bottom: 20px; }
.form-group label { display: block; margin-bottom: 8px; font-size: 14px; color: var(--text-dim); }
.form-group input, .form-group textarea, .form-group select { width: 100%; padding: 14px 16px; background: var(--bg-dark); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 15px; }
.form-group input:focus, .form-group textarea:focus { outline: none; border-color: var(--primary); }

.type-options, .domain-options { display: flex; flex-wrap: wrap; gap: 8px; }
.type-btn, .domain-btn { background: var(--bg-dark); border: 1px solid var(--border); color: var(--text-dim); padding: 8px 14px; border-radius: 20px; cursor: pointer; transition: all 0.2s; font-size: 13px; }
.type-btn:hover, .domain-btn:hover { border-color: var(--primary); }
.type-btn.active, .domain-btn.active { background: var(--primary-dim); border-color: var(--primary); color: var(--primary); }

.btn-primary { width: 100%; background: linear-gradient(135deg, #00ff88, #00cc6a); color: #000; border: none; padding: 14px; font-size: 16px; font-weight: 600; border-radius: 8px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.message { margin-top: 16px; padding: 12px; border-radius: 8px; text-align: center; font-size: 14px; }
.message.error { background: #ff444422; color: #ff4444; }
.message.success { background: #00ff8822; color: #00ff88; }
</style>
