// chat.js
import request from '@/api/request'

// ========== 对话相关 ==========
export function getChat(params) {
  return request({
    url: '/chat',
    method: 'post',
    data: params
  })
}

// 流式对话（可选）
export function getChatStream(params) {
  return request({
    url: '/chat/stream',
    method: 'post',
    data: params,
    responseType: 'stream'
  })
}

// ========== 数据概览 ==========
export function getInfo() {
  return request({
    url: '/info',
    method: 'get'
  })
}

// ========== 单文件上传（兼容旧版）==========
export function upload(data, config = {}) {
  return request({
    url: '/upload',
    method: 'post',
    data: data,
    ...config
  })
}

// ========== 多文件上传（新版）==========
export function uploadMultipleFiles(formData, onProgress) {
  return request({
    url: '/datasets/upload',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        onProgress(percent)
      }
    }
  })
}

// ========== 数据集管理 ==========
// 获取所有数据集
export function getDatasets() {
  return request({
    url: '/datasets',
    method: 'get'
  })
}

// 获取当前数据集
export function getCurrentDataset() {
  return request({
    url: '/datasets/current',
    method: 'get'
  })
}

// 切换数据集
export function switchDataset(filename) {
  const formData = new FormData()
  formData.append('filename', filename)
  return request({
    url: '/datasets/switch',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 删除数据集
export function deleteDataset(filename) {
  return request({
    url: `/datasets/${filename}`,
    method: 'delete'
  })
}

// 获取数据预览
export function getDataPreview(limit = 10) {
  return request({
    url: `/datasets/preview?limit=${limit}`,
    method: 'get'
  })
}

// ========== 图表相关 ==========
export function getChart(params) {
  return request({
    url: '/chart',
    method: 'post',
    data: params
  })
}

// ========== 自然语言查询 ==========
export function naturalLanguageQuery(params) {
  return request({
    url: '/nl/query',
    method: 'post',
    data: params
  })
}

// ========== SQL 查询 ==========
export function executeSQL(params) {
  return request({
    url: '/sql/execute',
    method: 'post',
    data: params
  })
}

// ========== 健康检查 ==========
export function healthCheck() {
  return request({
    url: '/',
    method: 'get'
  })
}