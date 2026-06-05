<template>
  <div class="app">
    <header>
      <h1>📊 AI 数据分析助手</h1>
      <p>用自然语言查询数据，自动生成图表</p>
    </header>

    <div class="container">
      <!-- 侧边栏 -->
      <div class="sidebar">
        <div class="info-card">
          <h3>📈 数据概览</h3>
          <div v-if="dataInfo">
            <p>📊 总记录: {{ dataInfo.rows }} 条</p>
            <p>💰 总销售额: ¥{{ formatNumber(dataInfo.total_sales) }}</p>
            <p>📅 时间: {{ dataInfo.date_range?.start }} ~ {{ dataInfo.date_range?.end }}</p>
          </div>
          <button @click="loadDataInfo" class="refresh-btn">刷新数据</button>
        </div>
        
        <div class="info-card" v-if="hasChart">
          <h3>📊 当前图表</h3>
          <button @click="clearChart" class="clear-btn">清除图表</button>
        </div>
      </div>

      <!-- 主区域 -->
      <div class="main">
        <!-- 图表区域 -->
        <div class="chart-area" v-if="hasChart">
          <div ref="chartRef" class="chart"></div>
        </div>

        <!-- 对话区域 -->
        <div class="chat-area">
          <div class="messages" ref="messagesContainer">
            <div v-for="(msg, idx) in messages" :key="idx" class="message" :class="msg.role">
              <div class="avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
              <div class="content">
                <div class="text">{{ msg.content }}</div>
                <div class="time">{{ msg.time }}</div>
              </div>
            </div>
            <div v-if="isLoading" class="message assistant">
              <div class="avatar">🤖</div>
              <div class="content thinking">🤔 思考中...</div>
            </div>
          </div>

          <div class="input-area">
            <input 
              v-model="inputText" 
              @keydown.enter="sendMessage"
              placeholder="输入问题，如：哪个产品卖得最好？ 或：画个柱状图"
              :disabled="isLoading"
            />
            <button @click="sendMessage" :disabled="isLoading || !inputText.trim()">发送</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

const API_BASE = 'http://localhost:8001'

const messages = ref([])
const inputText = ref('')
const isLoading = ref(false)
const dataInfo = ref(null)
const hasChart = ref(false)
const chartRef = ref(null)
let chartInstance = null

const formatNumber = (num) => {
  if (!num) return '0'
  return num.toLocaleString()
}

// 加载数据概览
const loadDataInfo = async () => {
  try {
    const response = await axios.get(`${API_BASE}/info`)
    dataInfo.value = response.data
  } catch (error) {
    console.error('加载失败', error)
  }
}

// 渲染图表
const renderChart = async (chartData) => {
  if (!chartData) {
    console.error('无图表数据')
    return
  }
  
  // 先设置 hasChart 为 true，确保容器被渲染
  hasChart.value = true
  
  // 等待 DOM 更新，确保 chartRef 可用
  await nextTick()
  
  if (!chartRef.value) {
    console.error('图表容器不存在')
    return
  }
  
  if (chartInstance) {
    chartInstance.dispose()
  }
  
  chartInstance = echarts.init(chartRef.value)
  
  let option = {}
  
  if (chartData.chart_type === 'bar') {
    option = {
      title: { text: chartData.title, left: 'center' },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: { type: 'category', data: chartData.xAxis, name: '类别', axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', name: '销售额(元)' },
      series: chartData.series.map(s => ({
        type: 'bar',
        name: s.name,
        data: s.data,
        itemStyle: { borderRadius: [4, 4, 0, 0], color: '#667eea' }
      }))
    }
  } else if (chartData.chart_type === 'line') {
    option = {
      title: { text: chartData.title, left: 'center' },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: chartData.xAxis },
      yAxis: { type: 'value', name: '销售额(元)' },
      series: chartData.series.map(s => ({
        type: 'line',
        name: s.name,
        data: s.data,
        smooth: true,
        areaStyle: { opacity: 0.3 },
        lineStyle: { width: 3, color: '#667eea' }
      }))
    }
  }
  
  chartInstance.setOption(option)
  console.log('图表渲染成功', chartData)
}

// 清除图表
const clearChart = () => {
  hasChart.value = false
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

// 判断是否需要图表
const shouldGenerateChart = (message) => {
  const chartKeywords = ['画', '图', '图表', '柱状', '折线', '饼图', '展示', '可视化', 'bar', 'chart']
  return chartKeywords.some(kw => message.toLowerCase().includes(kw.toLowerCase()))
}

// 获取图表数据（直接调用后端 /chart 接口）
const fetchChartData = async (userMessage) => {
  try {
    console.log('正在请求图表数据...')
    // 直接调用 /chart 接口，传递用户原消息
    const response = await axios.post(`${API_BASE}/chart`, {
      message: userMessage
    })
    
    console.log('图表接口返回:', response.data)
    
    // 检查返回数据是否有效
    if (response.data && response.data.xAxis && response.data.xAxis.length > 0) {
      return response.data
    } else {
      console.warn('图表数据无效')
      return null
    }
  } catch (error) {
    console.error('获取图表数据失败:', error)
    return null
  }
}

// 发送消息
const sendMessage = async () => {
  if (!inputText.value.trim() || isLoading.value) return
  
  const userMessage = inputText.value.trim()
  const needChart = shouldGenerateChart(userMessage)
  
  console.log(`用户消息: ${userMessage}`)
  console.log(`是否需要图表: ${needChart}`)
  
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
  
  try {
    // 1. 调用对话接口
    const response = await axios.post(`${API_BASE}/chat`, {
      message: userMessage
    })
    
    console.log('对话接口返回:', response.data)
    
    // 添加 AI 回复
    messages.value.push({
      role: 'assistant',
      content: response.data.answer,
      time: new Date().toLocaleTimeString()
    })
    
    // 更新数据概览
    if (response.data.data_info) {
      dataInfo.value = response.data.data_info
    }
    
    // 2. 如果需要图表，单独请求图表数据
    if (needChart) {
      console.log('开始请求图表数据...')
      const chartData = await fetchChartData(userMessage)
      if (chartData && chartData.xAxis && chartData.xAxis.length > 0) {
        await renderChart(chartData)
      } else {
        console.log('无法生成图表，没有数据')
      }
    }
    
  } catch (error) {
    console.error('请求失败', error)
    messages.value.push({
      role: 'assistant',
      content: '抱歉，处理请求时出错了。请稍后再试。',
      time: new Date().toLocaleTimeString()
    })
  } finally {
    isLoading.value = false
    await nextTick()
    scrollToBottom()
  }
}

const scrollToBottom = () => {
  const container = document.querySelector('.messages')
  if (container) {
    container.scrollTop = container.scrollHeight
  }
}

onMounted(() => {
  loadDataInfo()
  console.log('App 已挂载，API 地址:', API_BASE)
})
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f7fa;
}

header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 16px 24px;
  text-align: center;
}

header h1 { font-size: 24px; }
header p { font-size: 14px; opacity: 0.9; margin-top: 4px; }

.container {
  flex: 1;
  display: flex;
  overflow: hidden;
  padding: 16px;
  gap: 16px;
}

.sidebar {
  width: 260px;
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-card {
  background: #f9f9f9;
  border-radius: 8px;
  padding: 12px;
}

.info-card h3 {
  font-size: 14px;
  margin-bottom: 12px;
  color: #333;
}

.info-card p {
  font-size: 12px;
  color: #666;
  margin: 6px 0;
}

.refresh-btn, .clear-btn {
  width: 100%;
  margin-top: 12px;
  padding: 6px 12px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.clear-btn { background: #ff6b6b; }
.refresh-btn:hover { background: #5a67d8; }
.clear-btn:hover { background: #ee5a5a; }

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

.chart-area {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  height: 320px;
}

.chart {
  width: 100%;
  height: 100%;
}

.chat-area {
  flex: 1;
  background: white;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.message {
  display: flex;
  margin-bottom: 16px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message.user { flex-direction: row-reverse; }

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 12px;
  flex-shrink: 0;
}

.message.user .avatar { background: #667eea; }
.message.assistant .avatar { background: #764ba2; }

.content {
  max-width: 70%;
  background: #f0f0f0;
  padding: 10px 14px;
  border-radius: 12px;
}

.message.user .content {
  background: #667eea;
  color: white;
}

.text {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14px;
  line-height: 1.5;
}

.time { font-size: 10px; opacity: 0.5; margin-top: 4px; }
.thinking { color: #999; }

.input-area {
  display: flex;
  padding: 16px;
  border-top: 1px solid #e0e0e0;
  gap: 12px;
}

.input-area input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #e0e0e0;
  border-radius: 24px;
  outline: none;
  font-size: 14px;
}

.input-area input:focus { border-color: #667eea; }

.input-area button {
  padding: 8px 24px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 24px;
  cursor: pointer;
  font-size: 14px;
}

.input-area button:hover:not(:disabled) { background: #764ba2; }
.input-area button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>