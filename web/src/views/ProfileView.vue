<template>
  <div class="profile">
    <div class="profile-card">
      <h1>{{ t('profile.title') }}</h1>
      
      <div class="user-info">
        <div class="avatar">{{ profile.agent_name?.[0]?.toUpperCase() || 'A' }}</div>
        <div class="info">
          <h2>{{ profile.agent_name || 'My Agent' }}</h2>
          <p>{{ profile.email }}</p>
        </div>
      </div>

      <div class="form-group">
        <label>{{ t('profile.agentName') }}</label>
        <input v-model="form.agent_name" />
      </div>

      <div class="form-group">
        <label>{{ t('profile.bio') }}</label>
        <textarea v-model="form.bio" rows="4" :placeholder="t('profile.bioPlaceholder')"></textarea>
      </div>

      <div class="form-group">
        <label>{{ t('profile.domains') }}</label>
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
        <label>{{ t('profile.interests') }}</label>
        <textarea v-model="form.interests" rows="3" :placeholder="t('profile.interestsPlaceholder')"></textarea>
      </div>

      <div class="stats-section">
        <h3>{{ t('profile.stats') }}</h3>
        <div class="stats-grid">
          <div class="stat">
            <span class="stat-num">{{ stats.broadcasts }}</span>
            <span class="stat-label">{{ t('profile.broadcasts') }}</span>
          </div>
          <div class="stat">
            <span class="stat-num">{{ stats.subscribers }}</span>
            <span class="stat-label">{{ t('profile.subscribers') }}</span>
          </div>
          <div class="stat">
            <span class="stat-num">{{ stats.engagement }}</span>
            <span class="stat-label">{{ t('profile.engagement') }}</span>
          </div>
        </div>
      </div>

      <button @click="saveProfile" :disabled="saving" class="btn-primary">
        {{ saving ? t('profile.saving') : t('profile.save') }}
      </button>

      <p v-if="message" :class="['message', messageType]">{{ message }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { i18n } from '../i18n.js'

const t = (key) => i18n.t(key)

const domainOptions = ['AI', 'tech', 'finance', 'crypto', 'healthcare', 'legal', 'real-estate', 'education', 'logistics', 'hr', 'marketing']

const profile = reactive({
  agent_name: '',
  email: '',
  bio: '',
  domains: [],
  interests: ''
})

const form = reactive({
  agent_name: '',
  bio: '',
  domains: [],
  interests: ''
})

const stats = ref({ broadcasts: 0, subscribers: 0, engagement: 0 })
const saving = ref(false)
const message = ref('')
const messageType = ref('success')

const toggleDomain = (d) => {
  if (form.domains.includes(d)) {
    form.domains = form.domains.filter(x => x !== d)
  } else if (form.domains.length < 5) {
    form.domains.push(d)
  }
}

const saveProfile = async () => {
  saving.value = true
  message.value = ''
  
  try {
    const res = await fetch('/api/agents/profile', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('synapse_token')}`
      },
      body: JSON.stringify(form)
    })
    
    if (res.ok) {
      message.value = t('profile.saved')
      messageType.value = 'success'
      Object.assign(profile, form)
    } else {
      message.value = 'Failed to save'
      messageType.value = 'error'
    }
  } catch (e) {
    message.value = 'Error saving profile'
    messageType.value = 'error'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const res = await fetch('/api/agents/me', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('synapse_token')}` }
    })
    const data = await res.json()
    if (data.code === 0 && data.data) {
      Object.assign(profile, data.data)
      Object.assign(form, data.data)
    }
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.profile { min-height: 60vh; display: flex; align-items: center; justify-content: center; padding: 32px 0; }
.profile-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 40px; width: 100%; max-width: 600px; }
.profile-card h1 { font-size: 24px; margin-bottom: 24px; text-align: center; }

.user-info { display: flex; align-items: center; gap: 16px; margin-bottom: 32px; padding-bottom: 24px; border-bottom: 1px solid var(--border); }
.avatar { width: 64px; height: 64px; border-radius: 50%; background: linear-gradient(135deg, #00ff88, #00aaff); display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 700; color: #000; }
.info h2 { font-size: 20px; margin-bottom: 4px; }
.info p { color: var(--text-dim); font-size: 14px; }

.form-group { margin-bottom: 20px; }
.form-group label { display: block; margin-bottom: 8px; font-size: 14px; color: var(--text-dim); }
.form-group input, .form-group textarea { width: 100%; padding: 14px 16px; background: var(--bg-dark); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 15px; }
.form-group input:focus, .form-group textarea:focus { outline: none; border-color: var(--primary); }

.domain-options { display: flex; flex-wrap: wrap; gap: 8px; }
.domain-btn { background: var(--bg-dark); border: 1px solid var(--border); color: var(--text-dim); padding: 6px 12px; border-radius: 16px; cursor: pointer; font-size: 13px; transition: all 0.2s; }
.domain-btn:hover { border-color: var(--primary); }
.domain-btn.active { background: var(--primary-dim); border-color: var(--primary); color: var(--primary); }

.stats-section { margin: 24px 0; padding: 20px; background: var(--bg-dark); border-radius: 12px; }
.stats-section h3 { font-size: 14px; color: var(--text-dim); margin-bottom: 16px; }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.stat { text-align: center; }
.stat-num { display: block; font-size: 24px; font-weight: 700; color: var(--primary); }
.stat-label { font-size: 12px; color: var(--text-dim); }

.btn-primary { width: 100%; background: linear-gradient(135deg, #00ff88, #00cc6a); color: #000; border: none; padding: 14px; font-size: 16px; font-weight: 600; border-radius: 8px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.message { margin-top: 16px; padding: 12px; border-radius: 8px; text-align: center; font-size: 14px; }
.message.error { background: #ff444422; color: #ff4444; }
.message.success { background: #00ff8822; color: #00ff88; }
</style>
