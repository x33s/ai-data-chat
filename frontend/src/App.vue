<template>
  <el-container class="app">
    <el-header>
      <div class="header-content">
        <h1>📊 AI 数据分析助手</h1>
        <p>用自然语言查询数据，自动生成图表</p>
      </div>
    </el-header>

    <el-container class="container">
      <!-- 侧边栏 -->
      <el-aside width="320px" class="sidebar">
        <FileUpload @upload-success="handleUploadSuccess" @dataset-changed="handleDatasetChanged" />
        <DataOverview ref="dataOverviewRef" @data-loaded="handleDataLoaded" />
      </el-aside>

      <!-- 主区域 - 只有对话区域 -->
      <el-main class="main">
       <ChatBox 
        ref="chatBoxRef"
        @message-sent="handleMessageSent"
        @chart-needed="handleChartNeeded"
        @reopen-chart="handleReopenChart"
      />
      </el-main>
    </el-container>
    
    <!-- 图表弹窗组件 -->
    <ChartDisplay ref="chartDisplayRef" />
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import FileUpload from './components/FileUpload.vue'
import DataOverview from './components/DataOverview.vue'
import ChatBox from './components/ChatBox.vue'
import ChartDisplay from './components/ChartDisplay.vue'

const dataOverviewRef = ref(null)
const chartDisplayRef = ref(null)
const chatBoxRef = ref(null)

const handleUploadSuccess = (data) => {
  console.log('文件上传成功:', data)
  if (dataOverviewRef.value) {
    dataOverviewRef.value.refreshData()
  }
}

const handleDatasetChanged = (filename) => {
  console.log('数据集已切换:', filename)
  if (dataOverviewRef.value) {
    dataOverviewRef.value.refreshData()
  }
  if (chartDisplayRef.value) {
    chartDisplayRef.value.clearChart()
  }
}

const handleDataLoaded = (data) => {
  console.log('数据已加载:', data)
}

const handleMessageSent = (message) => {
  console.log('消息已发送:', message)
}

const handleChartNeeded = async (message) => {
  console.log('需要生成图表:', message)
  if (chartDisplayRef.value) {
    await chartDisplayRef.value.fetchChartData(message)
  }
}
// 重新打开图表
const handleReopenChart = async (message) => {
  console.log('App.vue 接收到重新打开图表事件:', message)
  if (chartDisplayRef.value) {
    await chartDisplayRef.value.fetchChartData(message)
  }
}

</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.app {
  height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.el-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 0;
  height: auto !important;
}

.header-content {
  padding: 16px 24px;
  color: white;
  text-align: center;
}

.header-content h1 {
  font-size: 24px;
  margin: 0;
}

.header-content p {
  font-size: 14px;
  opacity: 0.9;
  margin-top: 4px;
}

.container {
  height: calc(100vh - 80px);
  padding: 16px;
  gap: 16px;
  background: #f5f7fa;
}

.sidebar {
  background: transparent;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.main {
  background: transparent;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow-y: auto;
}

/* 自定义滚动条 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>