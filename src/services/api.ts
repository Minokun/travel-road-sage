import Taro from '@tarojs/taro'

const BASE_URL = 'http://localhost:8000/api'

interface ApiResponse<T = any> {
  success?: boolean
  data?: T
  reply?: string
  error?: string
}

class ApiService {
  private async request<T>(
    url: string,
    method: 'GET' | 'POST' = 'GET',
    data?: any
  ): Promise<T> {
    try {
      const res = await Taro.request({
        url: `${BASE_URL}${url}`,
        method,
        data,
        header: {
          'Content-Type': 'application/json'
        }
      })
      return res.data as T
    } catch (error) {
      console.error('API请求失败:', error)
      throw error
    }
  }

  // 对话接口
  async chat(message: string): Promise<{ reply: string }> {
    return this.request('/chat', 'POST', { message })
  }

  // 创建行程
  async createPlan(params: {
    destination: string
    days: number
    preferences?: string[]
    budget?: number
  }) {
    return this.request('/plan', 'POST', params)
  }

  // 天气查询
  async getWeather(city: string) {
    return this.request(`/map/weather?city=${encodeURIComponent(city)}`)
  }

  // POI搜索
  async searchPOI(keyword: string, city?: string) {
    let url = `/map/search?keyword=${encodeURIComponent(keyword)}`
    if (city) url += `&city=${encodeURIComponent(city)}`
    return this.request(url)
  }

  // 路径规划
  async getRoute(origin: string, destination: string, mode: string = 'walking') {
    return this.request('/map/route', 'POST', { origin, destination, mode })
  }

  // 导航链接
  async getNavigateUrl(destination: string, destinationName?: string) {
    return this.request('/plan/navigate', 'POST', {
      destination,
      destination_name: destinationName
    })
  }

  // 搜索攻略
  async searchGuides(destination: string) {
    return this.request(`/search/guides?destination=${encodeURIComponent(destination)}`)
  }
}

export const api = new ApiService()
