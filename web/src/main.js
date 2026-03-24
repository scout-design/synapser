import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true
})

// 创建渲染函数
function renderMarkdown(content) {
  if (!content) return ''
  return DOMPurify.sanitize(marked(content))
}

const app = createApp(App)
app.use(router)
app.config.globalProperties.$renderMarkdown = renderMarkdown
app.mount('#app')
