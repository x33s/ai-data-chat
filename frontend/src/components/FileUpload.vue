<template>
  <el-card class="file-upload-card" shadow="hover">
    <template #header>
      <div class="card-header">
        <span>📁 数据文件上传</span>
        <el-tag type="info" size="small">支持 CSV/Excel</el-tag>
      </div>
    </template>
    
    <el-upload
      class="upload-area"
      drag
      multiple
      :auto-upload="false"
      :show-file-list="false"
      :on-change="handleFileChange"
      accept=".csv,.xlsx,.xls"
      :disabled="isUploading"
    >
      <el-icon class="upload-icon"><Upload /></el-icon>
      <div class="upload-text">
        <span>点击或拖拽文件到此处</span>
        <el-text size="small" type="info">支持多选，最大 50MB</el-text>
      </div>
    </el-upload>
    
    <!-- 上传进度 -->
    <el-progress 
      v-if="isUploading" 
      :percentage="uploadProgress" 
      :status="uploadProgress === 100 ? 'success' : undefined"
      style="margin-top: 12px"
    />
    
    <!-- 上传结果 -->
    <div v-if="uploadResults.length > 0" class="upload-results">
      <el-alert
        v-for="result in uploadResults"
        :key="result.filename"
        :title="result.filename"
        :type="result.success ? 'success' : 'error'"
        :description="result.success ? `${result.rows}行 × ${result.columns}列` : result.error"
        show-icon
        :closable="false"
        style="margin-bottom: 8px"
      />
    </div>
    
    <!-- 数据集列表 -->
    <div class="dataset-list" v-if="datasets.length > 0">
      <el-divider content-position="left">
        <span>📊 已上传数据集 ({{ datasets.length }})</span>
      </el-divider>
      
      <div v-for="ds in datasets" :key="ds.name" class="dataset-item">
        <div class="dataset-info">
          <span class="dataset-name">{{ ds.name }}</span>
          <el-tag :type="ds.is_active ? 'primary' : 'info'" size="small">
            {{ ds.is_active ? '当前使用' : `${ds.rows || '-'}行 × ${ds.columns || '-'}列` }}
          </el-tag>
        </div>
        <div class="dataset-actions">
          <el-button 
            size="small" 
            :type="ds.is_active ? 'success' : 'primary'"
            :disabled="ds.is_active"
            @click="handleSwitchDataset(ds.name)"
          >
            {{ ds.is_active ? '✓ 当前' : '切换' }}
          </el-button>
          <el-button 
            size="small" 
            type="danger" 
            plain
            @click="handleDeleteDataset(ds.name)"
          >
            删除
          </el-button>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import { uploadMultipleFiles, getDatasets, switchDataset, deleteDataset } from '@/api/chat.js'

const emit = defineEmits(['upload-success', 'dataset-changed'])

const isUploading = ref(false)
const uploadProgress = ref(0)
const uploadResults = ref([])
const datasets = ref([])

const loadDatasets = async () => {
  try {
    const res = await getDatasets()
    datasets.value = res.datasets || []
  } catch (error) {
    console.error('加载失败', error)
  }
}

const handleFileChange = async (file) => {
  if (!file.raw) return
  
  isUploading.value = true
  uploadProgress.value = 0
  uploadResults.value = []
  
  const formData = new FormData()
  formData.append('files', file.raw)
  
  try {
    const result = await uploadMultipleFiles(formData, (percent) => {
      uploadProgress.value = percent
    })
    
    uploadResults.value = result.results || []
    
    if (result.success_count > 0) {
      await loadDatasets()
      emit('upload-success', result)
      ElMessage.success(`成功上传 ${result.success_count} 个文件`)
    } else {
      ElMessage.error('上传失败')
    }
  } catch (error) {
    console.error('上传失败', error)
    ElMessage.error('上传失败：' + (error.response?.data?.detail || error.message))
  } finally {
    isUploading.value = false
    setTimeout(() => {
      uploadResults.value = []
    }, 3000)
  }
}

const handleSwitchDataset = async (filename) => {
  try {
    await switchDataset(filename)
    await loadDatasets()
    emit('dataset-changed', filename)
    ElMessage.success(`已切换到: ${filename}`)
  } catch (error) {
    ElMessage.error('切换失败')
  }
}

const handleDeleteDataset = async (filename) => {
  try {
    await ElMessageBox.confirm(`确定删除 "${filename}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteDataset(filename)
    await loadDatasets()
    emit('dataset-changed')
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadDatasets()
})
</script>

<style scoped>
.file-upload-card {
  background: white;
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-area {
  width: 100%;
}

.upload-icon {
  font-size: 48px;
  color: #667eea;
  margin-bottom: 12px;
}

.upload-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.upload-results {
  margin-top: 12px;
}

.dataset-list {
  margin-top: 8px;
}

.dataset-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}

.dataset-item:last-child {
  border-bottom: none;
}

.dataset-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  overflow: hidden;
}

.dataset-name {
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dataset-actions {
  display: flex;
  gap: 8px;
}
</style>