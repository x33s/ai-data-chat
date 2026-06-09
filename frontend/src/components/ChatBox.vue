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
          <!-- 图表按钮 - 默认样式，无背景色 -->
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
      
      <!-- 加载状态 -->
      <div v-if="isLoading" class="message assistant">
        <el-avatar :size="36" class="assistant">🤖</el-avatar>
        <div class="message-content">
          <div class="message-bubble loading-bubble">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
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
        placeholder="输入问题，如：哪个产品卖得最好？ 或：画个柱状图"
        :disabled="isLoading"
        resize="none"
        @keydown.enter.prevent="sendMessage"
      />
      <el-button 
        type="primary"
        :loading="isLoading"
        :disabled="!inputText.trim()"
        @click="sendMessage"
      >
        发送
      </el-button>
    </div>
  </el-card>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { getChat } from '@/api/chat.js'

const emit = defineEmits(['message-sent', 'chart-needed', 'reopen-chart'])

const messages = ref([])
const inputText = ref('')
const isLoading = ref(false)
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

// 检查回答中是否包含图表相关内容
const hasChartInAnswer = (answer) => {
  const chartIndicators = ['柱状图', '折线图', '饼图', '图表', '销售额对比', '业绩对比', '趋势']
  return chartIndicators.some(ind => answer.includes(ind))
}

// 重新打开图表
const handleReopenChart = (chartMessage) => {
  console.log('点击查看图表，消息:', chartMessage)
  if (chartMessage) {
    emit('reopen-chart', chartMessage)
  }
}

const sendMessage = async () => {
  if (!inputText.value.trim() || isLoading.value) return
  
  const userMessage = inputText.value.trim()
  const needChart = shouldGenerateChart(userMessage)
  
  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: userMessage,
    time: new Date().toLocaleTimeString()
  })
  
  inputText.value = ''
  isLoading.value = true
  
  await nextTick()
  scrollToBottom()
  
  emit('message-sent', userMessage)
  
  try { 
    const response = await getChat({
      message: userMessage
    })
    
    const hasChart = needChart || hasChartInAnswer(response.answer)
    
    messages.value.push({
      role: 'assistant',
      content: response.answer,
      time: new Date().toLocaleTimeString(),
      hasChart: hasChart,
      chartMessage: userMessage
    })
    
    if (needChart) {
      emit('chart-needed', userMessage)
    }
    
  } catch (error) {
    console.error('请求失败', error)
    messages.value.push({
      role: 'assistant',
      content: '抱歉，处理请求时出错了。请稍后再试。',
      time: new Date().toLocaleTimeString(),
      hasChart: false
    })
  } finally {
    isLoading.value = false
    await nextTick()
    scrollToBottom()
  }
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const clearHistory = () => {
  messages.value = []
}

defineExpose({
  clearHistory
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

/* 加载气泡 */
.loading-bubble {
  background: white;
  padding: 12px 20px;
}

/* 打字动画 */
.typing-indicator {
  display: flex;
  gap: 4px;
  align-items: center;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #adb5bd;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  30% {
    transform: translateY(-8px);
    opacity: 1;
  }
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

/* 图表按钮 - 无背景色，默认样式 */
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

.input-area .el-button {
  border-radius: 24px;
  padding: 10px 24px;
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