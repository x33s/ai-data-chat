<template>
  <el-card class="chat-card" shadow="never">
    <!-- 消息区域 -->
    <div class="messages" ref="messagesContainer">
      <div v-for="(msg, idx) in messages" :key="idx" class="message" :class="msg.role">
        <el-avatar :size="36" :class="msg.role">
          {{ msg.role === 'user' ? '👤' : '🤖' }}
        </el-avatar>
        <div class="message-content">
          <div class="message-bubble">
            <div class="message-text" v-html="formatMessage(msg.content)"></div>
          </div>
          <!-- 图表按钮 -->
          <div v-if="msg.role === 'assistant' && msg.hasChart" class="chart-action">
            <el-button 
              size="small" 
              text
              @click="handleReopenChart(msg.chartMessage)"
            >
              📊 查看图表
            </el-button>
          </div>
          <div class="message-time">
            <el-text size="small" type="info">{{ msg.time }}</el-text>
          </div>
        </div>
      </div>
      
      <!-- 流式输出时的临时消息 -->
      <div v-if="isStreaming" class="message assistant streaming">
        <el-avatar :size="36" class="assistant">🤖</el-avatar>
        <div class="message-content">
          <div class="message-bubble streaming-bubble">
            <div class="message-text">
              {{ streamingContent }}
              <span class="cursor"></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="2"
        :placeholder="isStreaming ? 'AI 正在思考...' : '输入问题，如：哪个产品卖得最好？ 或：画个柱状图'"
        :disabled="isStreaming"
        resize="none"
        @keydown.enter.prevent="sendMessageStream"
      />
      <el-button 
        type="primary"
        :loading="isStreaming"
        :disabled="!inputText || !inputText.trim()"
        @click="sendMessageStream"
      >
        {{ isStreaming ? '思考中...' : '发送' }}
      </el-button>
      <el-button 
        :disabled="isStreaming"
        @click="clearChat"
      >
        清空
      </el-button>
    </div>
  </el-card>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'

const API_BASE = 'http://localhost:8001'

const emit = defineEmits(['message-sent', 'chart-needed', 'reopen-chart'])

// 响应式数据
const messages = ref([])
const inputText = ref('')
const isStreaming = ref(false)
const streamingContent = ref('')
const messagesContainer = ref(null)

// 格式化消息
const formatMessage = (content) => {
  if (!content) return ''
  return content.replace(/\n/g, '<br>')
}

// 检查是否需要图表
const shouldGenerateChart = (message) => {
  const chartKeywords = ['画', '图', '图表', '柱状', '折线', '饼图', '展示', '可视化', 'bar', 'chart']
  return chartKeywords.some(kw => message.toLowerCase().includes(kw.toLowerCase()))
}

// 重新打开图表
const handleReopenChart = (chartMessage) => {
  console.log('点击查看图表，消息:', chartMessage)
  if (chartMessage) {
    emit('reopen-chart', chartMessage)
  }
}

// 流式发送消息
const sendMessageStream = async () => {
  const message = inputText.value
  if (!message || !message.trim() || isStreaming.value) return
  
  const userMessage = message.trim()
  const needChart = shouldGenerateChart(userMessage)
  
  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: userMessage,
    time: new Date().toLocaleTimeString()
  })
  
  inputText.value = ''
  isStreaming.value = true
  streamingContent.value = ''
  
  await nextTick()
  scrollToBottom()
  
  emit('message-sent', userMessage)
  
  try {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userMessage })
    })
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let fullAnswer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          
          if (data === '[DONE]') {
            // 流式结束
            messages.value.push({
              role: 'assistant',
              content: fullAnswer,
              time: new Date().toLocaleTimeString(),
              hasChart: needChart,
              chartMessage: userMessage
            })
            if (needChart) {
              emit('chart-needed', userMessage)
            }
          } else if (data.startsWith('{')) {
            // JSON 格式
            try {
              const parsed = JSON.parse(data)
              if (parsed.type === 'content') {
                fullAnswer += parsed.content
                streamingContent.value = fullAnswer
                await nextTick()
                scrollToBottom()
              } else if (parsed.type === 'end') {
                messages.value.push({
                  role: 'assistant',
                  content: fullAnswer,
                  time: new Date().toLocaleTimeString(),
                  hasChart: needChart,
                  chartMessage: userMessage
                })
                if (needChart) {
                  emit('chart-needed', userMessage)
                }
              }
            } catch (e) {
              console.error('解析 JSON 失败:', e)
            }
          } else if (data && !data.startsWith('错误')) {
            // 简单格式
            fullAnswer += data
            streamingContent.value = fullAnswer
            await nextTick()
            scrollToBottom()
          }
        }
      }
    }
    
  } catch (error) {
    console.error('请求失败', error)
    ElMessage.error('请求失败，请检查后端服务')
    messages.value.push({
      role: 'assistant',
      content: '抱歉，处理请求时出错了。请稍后再试。',
      time: new Date().toLocaleTimeString(),
      hasChart: false
    })
  } finally {
    isStreaming.value = false
    streamingContent.value = ''
    await nextTick()
    scrollToBottom()
  }
}

// 清空对话
const clearChat = async () => {
  if (!confirm('确定清空所有对话吗？')) return
  
  messages.value = []
  try {
    await fetch(`${API_BASE}/clear`, { method: 'POST' })
    ElMessage.success('对话已清空')
  } catch (error) {
    console.error('清空失败', error)
  }
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 暴露方法给父组件
defineExpose({
  clearChat
})
</script>

<style scoped>
.chat-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  overflow: hidden;
}

.chat-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

/* 消息区域 */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f8f9fa;
}

/* 消息项 */
.message {
  display: flex;
  margin-bottom: 20px;
  animation: fadeIn 0.3s ease;
}

.message.user {
  flex-direction: row-reverse;
}

/* 头像 */
.el-avatar {
  flex-shrink: 0;
  font-size: 18px;
  font-weight: 500;
}

.el-avatar.user {
  background: #667eea;
  color: white;
}

.el-avatar.assistant {
  background: #e9ecef;
  color: #495057;
}

/* 消息内容容器 */
.message-content {
  max-width: 70%;
  margin: 0 12px;
}

.message.user .message-content {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

/* 消息气泡 */
.message-bubble {
  background: white;
  padding: 12px 16px;
  border-radius: 18px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.message.user .message-bubble {
  background: #667eea;
  color: white;
}

/* 流式气泡 */
.streaming-bubble {
  background: white;
  border: 1px solid #667eea;
}

/* 光标动画 */
.cursor {
  animation: blink 1s step-end infinite;
  display: inline-block;
  width: 2px;
  height: 1em;
  background-color: #667eea;
  margin-left: 2px;
  vertical-align: middle;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* 消息文本 */
.message-text {
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
  white-space: pre-wrap;
}

.message-text :deep(br) {
  display: block;
  margin: 4px 0;
}

/* 图表按钮 */
.chart-action {
  margin-top: 8px;
  text-align: left;
}

.chart-action :deep(.el-button) {
  padding: 4px 8px;
  color: #667eea;
  font-size: 12px;
}

.chart-action :deep(.el-button:hover) {
  color: #764ba2;
  background: transparent;
}

/* 消息时间 */
.message-time {
  margin-top: 4px;
  padding: 0 4px;
}

/* 输入区域 */
.input-area {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  background: white;
  border-top: 1px solid #e9ecef;
  align-items: flex-end;
}

.input-area :deep(.el-textarea__inner) {
  border-radius: 20px;
  transition: all 0.2s;
  font-size: 14px;
}

.input-area :deep(.el-textarea__inner:focus) {
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.input-area .el-button--primary {
  border-radius: 24px;
  padding: 10px 24px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border: none;
}

.input-area .el-button--primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

/* 动画 */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 滚动条 */
.messages::-webkit-scrollbar {
  width: 6px;
}

.messages::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.messages::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.messages::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>