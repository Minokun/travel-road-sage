import { create } from 'zustand'
import Taro from '@tarojs/taro'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

interface TripPlan {
  id: string
  title: string
  destination: string
  days: number
  date: string
  status: 'upcoming' | 'ongoing' | 'completed'
}

interface UserInfo {
  id: string
  nickname: string
  avatar_url: string
  gender?: number
  plan_count?: number
}

interface AppState {
  // 对话相关
  messages: Message[]
  addMessage: (message: Message) => void
  clearMessages: () => void
  
  // 行程相关
  trips: TripPlan[]
  addTrip: (trip: TripPlan) => void
  updateTrip: (id: string, updates: Partial<TripPlan>) => void
  
  // 用户相关
  isLoggedIn: boolean
  token: string | null
  userInfo: UserInfo | null
  setAuth: (token: string, user: UserInfo) => void
  logout: () => void
  loadAuth: () => void
}

export const useStore = create<AppState>((set) => ({
  // 对话
  messages: [],
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  clearMessages: () => set({ messages: [] }),
  
  // 行程
  trips: [],
  addTrip: (trip) => set((state) => ({
    trips: [...state.trips, trip]
  })),
  updateTrip: (id, updates) => set((state) => ({
    trips: state.trips.map(t => t.id === id ? { ...t, ...updates } : t)
  })),
  
  // 用户
  isLoggedIn: false,
  token: null,
  userInfo: null,
  
  setAuth: (token, user) => {
    // 保存到本地存储
    Taro.setStorageSync('token', token)
    Taro.setStorageSync('userInfo', user)
    set({
      isLoggedIn: true,
      token,
      userInfo: user
    })
  },
  
  logout: () => {
    Taro.removeStorageSync('token')
    Taro.removeStorageSync('userInfo')
    set({
      isLoggedIn: false,
      token: null,
      userInfo: null
    })
  },
  
  loadAuth: () => {
    try {
      const token = Taro.getStorageSync('token')
      const userInfo = Taro.getStorageSync('userInfo')
      if (token && userInfo) {
        set({
          isLoggedIn: true,
          token,
          userInfo
        })
      }
    } catch (e) {
      console.error('加载登录状态失败', e)
    }
  }
}))
