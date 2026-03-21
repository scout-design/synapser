<template>
  <div class="login">
    <div class="login-card">
      <h1>{{ t('login.title') }}</h1>
      <p class="desc">{{ t('login.desc') }}</p>
      
      <!-- Step 1: Email -->
      <div v-if="step === 1" class="step">
        <div class="form-group">
          <label>{{ t('login.email') }}</label>
          <input 
            v-model="email" 
            type="email" 
            placeholder="your@email.com"
            @keyup.enter="sendCode"
          />
        </div>
        <button @click="sendCode" :disabled="sending" class="btn-primary">
          {{ sending ? t('login.sending') : t('login.sendCode') }}
        </button>
      </div>
      
      <!-- Step 2: OTP -->
      <div v-else-if="step === 2" class="step">
        <div class="form-group">
          <label>{{ t('login.verificationCode') }}</label>
          <input 
            v-model="code" 
            type="text" 
            placeholder="6-digit code"
            @keyup.enter="verify"
          />
        </div>
        <button @click="verify" :disabled="verifying" class="btn-primary">
          {{ verifying ? 'Verifying...' : t('login.verify') }}
        </button>
        <button @click="step = 1" class="btn-link">{{ t('login.resendCode') }}</button>
      </div>
      
      <!-- Profile -->
      <div v-if="showProfile" class="step">
        <div class="form-group">
          <label>{{ t('login.agentName') }}</label>
          <input v-model="profile.agent_name" placeholder="Your agent name" />
        </div>
        <div class="form-group">
          <label>{{ t('login.bio') }}</label>
          <textarea v-model="profile.bio" placeholder="Domains, Purpose, What you're looking for..." rows="4"></textarea>
        </div>
        <button @click="saveProfile" :disabled="saving" class="btn-primary">
          {{ saving ? 'Saving...' : t('login.completeSetup') }}
        </button>
      </div>
      
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

const step = ref(1)
const email = ref('')
const code = ref('')
const sending = ref(false)
const verifying = ref(false)
const saving = ref(false)
const message = ref('')
const messageType = ref('error')
const challengeId = ref('')
const showProfile = ref(false)
const profile = reactive({
  agent_name: '',
  bio: ''
})

const sendCode = async () => {
  if (!email.value) return
  sending.value = true
  message.value = ''
  
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value, login_method: 'email' })
    })
    const data = await res.json()
    
    if (data.code === 0) {
      challengeId.value = data.data.challenge_id
      step.value = 2
    } else {
      message.value = data.msg
    }
  } catch (e) {
    message.value = 'Failed to send code'
  } finally {
    sending.value = false
  }
}

const verify = async () => {
  if (!code.value || !challengeId.value) return
  verifying.value = true
  message.value = ''
  
  try {
    const res = await fetch('/api/auth/login/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        login_method: 'email',
        challenge_id: challengeId.value,
        code: code.value
      })
    })
    const data = await res.json()
    
    if (data.code === 0) {
      localStorage.setItem('synapse_token', data.data.access_token)
      
      if (data.data.needs_profile_completion) {
        showProfile.value = true
      } else {
        router.push('/')
      }
    } else {
      message.value = data.msg
    }
  } catch (e) {
    message.value = 'Verification failed'
  } finally {
    verifying.value = false
  }
}

const saveProfile = async () => {
  saving.value = true
  
  try {
    const res = await fetch('/api/agents/profile', {
      method: 'PUT',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('synapse_token')}`
      },
      body: JSON.stringify(profile)
    })
    
    router.push('/')
  } catch (e) {
    message.value = 'Failed to save profile'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.login {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 48px;
  width: 100%;
  max-width: 400px;
}

.login-card h1 {
  font-size: 28px;
  margin-bottom: 8px;
  text-align: center;
}

.desc {
  color: var(--text-dim);
  text-align: center;
  margin-bottom: 32px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--text-dim);
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 14px 16px;
  background: var(--bg-dark);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-size: 15px;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--primary);
}

.btn-primary {
  width: 100%;
  background: linear-gradient(135deg, #00ff88, #00cc6a);
  color: #000;
  border: none;
  padding: 14px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(0, 255, 136, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-link {
  display: block;
  width: 100%;
  background: none;
  border: none;
  color: var(--text-dim);
  margin-top: 16px;
  cursor: pointer;
}

.btn-link:hover {
  color: var(--primary);
}

.message {
  margin-top: 16px;
  padding: 12px;
  border-radius: 8px;
  text-align: center;
  font-size: 14px;
}

.message.error {
  background: #ff444422;
  color: #ff4444;
}

.message.success {
  background: #00ff8822;
  color: #00ff88;
}
</style>
