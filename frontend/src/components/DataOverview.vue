<template>
  <div class="data-overview">
    <div class="overview-header">
      <h3>📈 数据概览</h3>
      <button @click="refreshData" class="refresh-btn" :disabled="isLoading">
        {{ isLoading ? '加载中...' : '刷新' }}
      </button>
    </div>
    
    <div v-if="dataInfo && !dataInfo.error" class="overview-content">
      <!-- 基本信息 -->
      <div class="stat-item">
        <span class="stat-icon">📊</span>
        <div class="stat-info">
          <span class="stat-label">文件名</span>
          <span class="stat-value">{{ dataInfo.filename || '-' }}</span>
        </div>
      </div>
      
      <div class="stat-item">
        <span class="stat-icon">📋</span>
        <div class="stat-info">
          <span class="stat-label">数据规模</span>
          <span class="stat-value">{{ dataInfo.rows || 0 }} 行 × {{ dataInfo.columns || 0 }} 列</span>
        </div>
      </div>
      
      <!-- 总销售额（如果有） -->
      <div v-if="dataInfo.total_sales !== undefined" class="stat-item">
        <span class="stat-icon">💰</span>
        <div class="stat-info">
          <span class="stat-label">总销售额</span>
          <span class="stat-value">¥{{ formatNumber(dataInfo.total_sales) }}</span>
        </div>
      </div>
      
      <!-- 日期范围（如果有） -->
      <div v-if="dataInfo.date_range && dataInfo.date_range.start" class="stat-item">
        <span class="stat-icon">📅</span>
        <div class="stat-info">
          <span class="stat-label">时间范围</span>
          <span class="stat-value">{{ dataInfo.date_range.start }} ~ {{ dataInfo.date_range.end }}</span>
        </div>
      </div>
      
      <!-- 产品列表（如果有） -->
      <div v-if="getArrayLength(dataInfo.products) > 0" class="stat-item">
        <span class="stat-icon">📦</span>
        <div class="stat-info">
          <span class="stat-label">产品/商品</span>
          <span class="stat-value">{{ getArrayLength(dataInfo.products) }} 种</span>
          <span v-if="getArrayLength(dataInfo.products) <= 10" class="stat-detail">
            {{ getArrayPreview(dataInfo.products) }}
          </span>
        </div>
      </div>
      
      <!-- 销售员/员工（如果有） -->
      <div v-if="getArrayLength(dataInfo.salespersons) > 0" class="stat-item">
        <span class="stat-icon">👥</span>
        <div class="stat-info">
          <span class="stat-label">销售员/员工</span>
          <span class="stat-value">{{ getArrayLength(dataInfo.salespersons) }} 人</span>
          <span v-if="getArrayLength(dataInfo.salespersons) <= 10" class="stat-detail">
            {{ getArrayPreview(dataInfo.salespersons) }}
          </span>
        </div>
      </div>
      
      <!-- 品类（如果有） -->
      <div v-if="getArrayLength(dataInfo.categories) > 0" class="stat-item">
        <span class="stat-icon">🏷️</span>
        <div class="stat-info">
          <span class="stat-label">品类/分类</span>
          <span class="stat-value">{{ getArrayLength(dataInfo.categories) }} 类</span>
          <span v-if="getArrayLength(dataInfo.categories) <= 10" class="stat-detail">
            {{ getArrayPreview(dataInfo.categories) }}
          </span>
        </div>
      </div>
      
      <!-- 动态显示所有列名（可选） -->
      <details class="columns-detail">
        <summary>📋 所有列名 ({{ getArrayLength(dataInfo.column_names) }})</summary>
        <div class="column-tags">
          <span v-for="col in dataInfo.column_names" :key="col" class="column-tag">
            {{ col }}
          </span>
        </div>
      </details>
    </div>
    
    <div v-else-if="isLoading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>加载数据中...</p>
    </div>
    
    <div v-else class="error-state">
      <p>{{ dataInfo?.message || '暂无数据，请先上传文件' }}</p>
      <button @click="refreshData" class="retry-btn">重试</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getInfo } from '@/api/chat.js'

const emit = defineEmits(['data-loaded'])

const dataInfo = ref(null)
const isLoading = ref(false)

const formatNumber = (num) => {
  if (num === null || num === undefined) return '0'
  return num.toLocaleString()
}

// 安全获取数组长度
const getArrayLength = (arr) => {
  if (!arr) return 0
  return Array.isArray(arr) ? arr.length : 0
}

// 获取数组预览（前5个）
const getArrayPreview = (arr) => {
  if (!arr || !Array.isArray(arr)) return ''
  const preview = arr.slice(0, 5).join('、')
  return arr.length > 5 ? `${preview} 等` : preview
}

const loadDataInfo = async () => {
  isLoading.value = true
  try { 
    const response = await getInfo()
    console.log('数据概览:', response)
    dataInfo.value = response
    emit('data-loaded', response)
  } catch (error) {
    console.error('加载失败', error)
    dataInfo.value = { error: true, message: error.message }
  } finally {
    isLoading.value = false
  }
}

const refreshData = () => {
  loadDataInfo()
}

defineExpose({
  refreshData
})

onMounted(() => {
  loadDataInfo()
})
</script>

<style scoped>
.data-overview {
  background: #f9f9f9;
  border-radius: 8px;
  padding: 16px;
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.overview-header h3 {
  font-size: 14px;
  margin: 0;
  color: #333;
}

.refresh-btn {
  padding: 4px 12px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  transition: background 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #5a67d8;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.overview-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #eee;
}

.stat-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.stat-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 11px;
  color: #999;
}

.stat-value {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.stat-detail {
  font-size: 10px;
  color: #999;
  margin-top: 2px;
  word-break: break-all;
}

.columns-detail {
  margin-top: 8px;
  padding: 8px 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #eee;
  cursor: pointer;
}

.columns-detail summary {
  font-size: 11px;
  color: #666;
  font-weight: 500;
}

.column-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.column-tag {
  background: #e8ecff;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 10px;
  color: #667eea;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 24px 16px;
  color: #999;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 12px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-state p,
.error-state p {
  font-size: 13px;
  margin: 0 0 12px 0;
}

.retry-btn {
  padding: 6px 16px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.retry-btn:hover {
  background: #5a67d8;
}
</style>