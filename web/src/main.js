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

// 解码 HTML 实体 (处理 &lt; &gt; &amp; 等)
function decodeHTMLEntities(str) {
  if (!str) return ''
  // 使用 textarea 进行解码
  const txt = document.createElement('textarea')
  txt.innerHTML = str
  let decoded = txt.value
  
  // 额外处理常见的 HTML 实体
  const entities = {
    '&lt;': '<',
    '&gt;': '>',
    '&amp;': '&',
    '&quot;': '"',
    '&#39;': "'",
    '&nbsp;': ' '
  }
  
  for (const [entity, char] of Object.entries(entities)) {
    decoded = decoded.replace(new RegExp(entity, 'g'), char)
  }
  
  return decoded
}

// 创建渲染函数
function renderMarkdown(content) {
  if (!content) return ''
  
  // 先解码 HTML 实体
  let text = decodeHTMLEntities(content)
  
  // 如果已经是 HTML，直接清理后返回
  if (isHTML(text)) {
    return DOMPurify.sanitize(text)
  }
  
  // 否则作为 Markdown 解析
  return DOMPurify.sanitize(marked(text))
}

const app = createApp(App)
app.use(router)
app.config.globalProperties.$renderMarkdown = renderMarkdown
app.mount('#app')
