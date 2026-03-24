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

// 检测是否包含 HTML 标签
function isHTML(str) {
  if (!str) return false
  return /<[a-z]+[^>]*>/i.test(str)
}

// 创建渲染函数
function renderMarkdown(content) {
  if (!content) return ''
  
  // 如果已经是 HTML，直接清理后返回
  if (isHTML(content)) {
    return DOMPurify.sanitize(content)
  }
  
  // 否则作为 Markdown 解析
  return DOMPurify.sanitize(marked(content))
}

const app = createApp(App)
app.use(router)
app.config.globalProperties.$renderMarkdown = renderMarkdown
app.mount('#app')
