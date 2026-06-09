<template>
  <!-- 图表弹窗 -->
  <el-dialog
    v-model="dialogVisible"
    :title="chartTitle"
    width="70%"
    :close-on-click-modal="false"
    destroy-on-close
    class="chart-dialog"
  >
    <div ref="chartRef" class="chart-container"></div>
    <template #footer>
      <el-button @click="closeChart">关闭</el-button>
      <el-button type="primary" @click="exportChart">导出图片</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getChart } from '@/api/chat.js'
import { ElMessage } from 'element-plus'

const dialogVisible = ref(false)
const chartTitle = ref('数据图表')
const chartRef = ref(null)
let chartInstance = null

// 获取图表数据并打开弹窗
const fetchChartData = async (message) => {
  console.log('fetchChartData 被调用, message:', message)
  
  try {
    const response = await getChart({ message: message })
    console.log('图表接口返回:', response)
    
    if (response && response.xAxis && response.xAxis.length > 0) {
      chartTitle.value = response.title || '数据图表'
      dialogVisible.value = true
      
      // 等待弹窗 DOM 渲染完成后再渲染图表
      await nextTick()
      renderChart(response)
    } else {
      ElMessage.warning('无法生成图表，请检查数据')
    }
  } catch (error) {
    console.error('获取图表数据失败:', error)
    ElMessage.error('获取图表数据失败')
  }
}

// 渲染图表
const renderChart = (chartData) => {
  if (!chartRef.value) {
    console.error('图表容器不存在')
    return
  }
  
  if (chartInstance) {
    chartInstance.dispose()
  }
  
  chartInstance = echarts.init(chartRef.value)
  
  let option = {}
  
  if (chartData.chart_type === 'line') {
    option = {
      title: { text: chartData.title, left: 'center', top: 0 },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { top: 60, bottom: 30, left: 60, right: 40, containLabel: true },
      xAxis: { 
        type: 'category', 
        data: chartData.xAxis, 
        name: chartData.xAxis[0]?.includes('-') ? '月份' : '产品',
        axisLabel: { rotate: 30, interval: 0 }
      },
      yAxis: { type: 'value', name: '销售额(元)' },
      series: chartData.series.map(s => ({
        type: 'line',
        name: s.name,
        data: s.data,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { width: 3, color: '#667eea' },
        areaStyle: { opacity: 0.1, color: '#667eea' }
      }))
    }
  } else if (chartData.chart_type === 'bar') {
    option = {
      title: { text: chartData.title, left: 'center', top: 0 },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { top: 60, bottom: 30, left: 60, right: 40 },
      xAxis: { type: 'category', data: chartData.xAxis, name: '产品', axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', name: '销售额(元)' },
      series: chartData.series.map(s => ({
        type: 'bar',
        name: s.name,
        data: s.data,
        itemStyle: { borderRadius: [4, 4, 0, 0], color: '#667eea' }
      }))
    }
  } else if (chartData.chart_type === 'pie') {
    option = {
      title: { text: chartData.title, left: 'center', top: 0 },
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: '50%',
        data: chartData.xAxis.map((name, idx) => ({
          name: name,
          value: chartData.series[0].data[idx]
        })),
        label: { show: true, formatter: '{b}: {d}%' }
      }]
    }
  }
  
  chartInstance.setOption(option)
  console.log('图表渲染完成')
}

// 关闭弹窗
const closeChart = () => {
  dialogVisible.value = false
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

// 导出图片
const exportChart = () => {
  if (!chartInstance) {
    ElMessage.warning('没有可导出的图表')
    return
  }
  
  try {
    const url = chartInstance.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#fff'
    })
    const link = document.createElement('a')
    link.download = `${chartTitle.value}.png`
    link.href = url
    link.click()
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  }
}

// 清除图表（关闭弹窗）
const clearChart = () => {
  closeChart()
}

defineExpose({
  fetchChartData,
  clearChart
})
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 500px;
}

:deep(.chart-dialog .el-dialog__body) {
  padding: 20px;
}

:deep(.chart-dialog .el-dialog__header) {
  margin-right: 0;
  border-bottom: 1px solid #eee;
  padding-bottom: 15px;
}

:deep(.chart-dialog .el-dialog__title) {
  font-size: 16px;
  font-weight: 500;
}
</style>