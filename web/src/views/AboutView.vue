<template>
  <div class="about">
    <section class="hero">
      <h1>{{ t('about.title') }}</h1>
      <p class="subtitle">{{ t('about.subtitle') }}</p>
    </section>

    <section class="features">
      <h2>{{ t('about.whatIs') }}</h2>
      <p>{{ t('about.description') }}</p>
    </section>

    <section class="features">
      <h2>{{ t('about.features') }}</h2>
      <div class="feature-grid">
        <div class="feature">
          <span class="icon">📡</span>
          <h3>{{ t('about.broadcast') }}</h3>
          <p>{{ t('about.broadcastDesc') }}</p>
        </div>
        <div class="feature">
          <span class="icon">🔔</span>
          <h3>{{ t('about.subscribe') }}</h3>
          <p>{{ t('about.subscribeDesc') }}</p>
        </div>
        <div class="feature">
          <span class="icon">🤝</span>
          <h3>{{ t('about.connect') }}</h3>
          <p>{{ t('about.connectDesc') }}</p>
        </div>
      </div>
    </section>

    <section class="features">
      <h2>{{ t('about.comingSoon') }}</h2>
      <ul>
        <li>AI-powered content matching</li>
        <li>1000+ built-in data sources</li>
        <li>Privacy-first design</li>
      </ul>
    </section>
  </div>
</template>

<script setup>
import { i18n } from '../i18n.js'

const t = (key) => i18n.t(key)
</script>

<style scoped>
.about {
  max-width: 800px;
  margin: 0 auto;
}

.hero {
  text-align: center;
  padding: 60px 0;
}

.hero h1 {
  font-size: 48px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #00ff88, #00aaff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  font-size: 20px;
  color: var(--text-dim);
}

.features {
  margin: 48px 0;
}

.features h2 {
  font-size: 24px;
  margin-bottom: 16px;
  color: var(--primary);
}

.features p {
  font-size: 16px;
  line-height: 1.8;
  color: var(--text-dim);
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
  margin-top: 24px;
}

.feature {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
}

.feature .icon {
  font-size: 32px;
  display: block;
  margin-bottom: 12px;
}

.feature h3 {
  font-size: 18px;
  margin-bottom: 8px;
}

.feature p {
  font-size: 14px;
}

.features ul {
  list-style: none;
  padding: 0;
}

.features li {
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
  color: var(--text-dim);
}

.features li::before {
  content: '→ ';
  color: var(--primary);
}
</style>
