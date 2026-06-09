// request.js
import axios from 'axios'

const request = axios.create({
  baseURL: 'http://localhost:8001',
  timeout: 15000,
  withCredentials: false
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    // 如果是 FormData，让浏览器自动设置 Content-Type（包含 boundary）
    // 否则使用 JSON 格式
    if (!(config.data instanceof FormData)) {
      config.headers['Content-Type'] = 'application/json'
    }
    // 如果是 FormData，删除可能存在的 Content-Type 头
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API request failed:', error.message)
    return Promise.reject(error)
  }
)

export default request