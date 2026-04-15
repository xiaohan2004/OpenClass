const API_BASE = import.meta.env.VITE_API_BASE || ''

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json'
    },
    ...options
  })

  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }

  const result = await response.json()
  if (result.code !== 0) {
    throw new Error(result.msg || '服务返回错误')
  }

  return result.data
}
