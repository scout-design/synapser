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

// 解码 HTML 实体 (处理 &#xxx; 和 &name; 格式)
function decodeHTMLEntities(str) {
  if (!str) return ''
  
  // 使用 textarea 解码 (自动处理大多数实体)
  const txt = document.createElement('textarea')
  txt.innerHTML = str
  let decoded = txt.value
  
  // 循环解码直到没有变化（处理多重编码）
  let prev = ''
  while (decoded !== prev) {
    prev = decoded
    const div = document.createElement('div')
    div.innerHTML = decoded
    decoded = div.innerHTML
  }
  
  return decoded
}

// 创建渲染函数
function renderMarkdown(content) {
  if (!content) return ''
  
  // 先解码 HTML 实体
  let text = decodeHTMLEntities(content)
  
  // 如果已经是 HTML，移除所有 HTML 标签，只保留纯文本
  if (isHTML(text)) {
    // 创建一个临时 div 来解析 HTML
    const div = document.createElement('div')
    div.innerHTML = text
    // 获取纯文本内容（自动解码 HTML 实体）
    return div.textContent || div.innerText || text
  }
  
  // 否则作为 Markdown 解析
  return DOMPurify.sanitize(marked(text))
}

const app = createApp(App)
app.use(router)
app.config.globalProperties.$renderMarkdown = renderMarkdown
app.mount('#app')
