import { useState, useEffect, useCallback } from 'react'
import { View, Text, ScrollView, Image } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useStore } from '@/store'
import { API_BASE } from '@/config'
import './index.scss'

interface TripItem {
  id: string
  destination: string
  days: number
  start_date?: string
  end_date?: string
  content: string
  cover_url?: string
  plan_data?: {
    route_map_url?: string
  }
  share_code?: string
  is_public: boolean
  created_at: string
}

// 格式化日期显示
const formatDateRange = (start?: string, end?: string): string => {
  if (!start || !end) return ''
  const startDate = new Date(start)
  const endDate = new Date(end)
  const startMonth = startDate.getMonth() + 1
  const startDay = startDate.getDate()
  const endMonth = endDate.getMonth() + 1
  const endDay = endDate.getDate()
  
  if (startMonth === endMonth) {
    return `${startMonth}月${startDay}日 - ${endDay}日`
  }
  return `${startMonth}月${startDay}日 - ${endMonth}月${endDay}日`
}

// 判断行程状态
const getTripStatus = (start?: string, end?: string): 'upcoming' | 'ongoing' | 'completed' => {
  if (!start || !end) return 'upcoming'
  const now = new Date()
  const startDate = new Date(start)
  const endDate = new Date(end)
  
  if (now < startDate) return 'upcoming'
  if (now > endDate) return 'completed'
  return 'ongoing'
}

export default function TripPage() {
  const { isLoggedIn, token } = useStore()
  const [activeTab, setActiveTab] = useState<'upcoming' | 'completed'>('upcoming')
  const [trips, setTrips] = useState<TripItem[]>([])
  const [loading, setLoading] = useState(false)
  
  // 加载行程列表
  const loadTrips = useCallback(async () => {
    // 确保有有效的token才发送请求
    if (!token || !isLoggedIn) {
      setTrips([])
      setLoading(false)
      return
    }
    
    setLoading(true)
    try {
      const res = await Taro.request({
        url: `${API_BASE}/plans`,
        method: 'GET',
        header: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (res.data.success) {
        setTrips(res.data.data.plans || [])
      }
    } catch (e) {
      console.error('加载行程失败', e)
      setTrips([])
    } finally {
      setLoading(false)
    }
  }, [token, isLoggedIn])
  
  // 页面显示时刷新
  useDidShow(() => {
    if (token && isLoggedIn) {
      loadTrips()
    }
  })
  
  useEffect(() => {
    if (token && isLoggedIn) {
      loadTrips()
    }
  }, [token, isLoggedIn])

  // 根据状态过滤行程
  const filteredTrips = trips.filter(trip => {
    const status = getTripStatus(trip.start_date, trip.end_date)
    return activeTab === 'upcoming' 
      ? status !== 'completed' 
      : status === 'completed'
  })

  const handleCreateTrip = () => {
    Taro.switchTab({ url: '/pages/chat/index' })
  }
  
  // 查看详情 - 优先使用id（自己的攻略）
  const handleViewDetail = (trip: TripItem) => {
    Taro.navigateTo({ url: `/pages/plan/detail?id=${trip.id}` })
  }
  
  // 分享行程
  const handleShare = async (trip: TripItem) => {
    if (!trip.share_code) {
      // 先设为公开获取分享码
      try {
        const res = await Taro.request({
          url: `${API_BASE}/plans/${trip.id}/share`,
          method: 'POST',
          header: {
            'Authorization': `Bearer ${token}`
          },
          data: { is_public: true }
        })
        
        if (res.data.success && res.data.data.share_code) {
          Taro.setClipboardData({
            data: `【${trip.destination} ${trip.days}日游】\n🔗 分享码: ${res.data.data.share_code}\n\n—— 由「旅行路算子」生成`,
            success: () => {
              Taro.showToast({ title: '已复制分享内容', icon: 'success' })
              loadTrips() // 刷新列表
            }
          })
        }
      } catch (e) {
        Taro.showToast({ title: '分享失败', icon: 'none' })
      }
    } else {
      Taro.setClipboardData({
        data: `【${trip.destination} ${trip.days}日游】\n🔗 分享码: ${trip.share_code}\n\n—— 由「旅行路算子」生成`,
        success: () => {
          Taro.showToast({ title: '已复制分享内容', icon: 'success' })
        }
      })
    }
  }
  
  // 删除行程
  const handleDelete = (trip: TripItem) => {
    Taro.showModal({
      title: '确认删除',
      content: `确定要删除「${trip.destination} ${trip.days}日游」吗？`,
      confirmColor: '#ef4444',
      success: async (res) => {
        if (res.confirm) {
          try {
            const response = await Taro.request({
              url: `${API_BASE}/plans/${trip.id}`,
              method: 'DELETE',
              header: {
                'Authorization': `Bearer ${token}`
              }
            })
            
            if (response.data.success) {
              Taro.showToast({ title: '删除成功', icon: 'success' })
              loadTrips() // 刷新列表
            } else {
              Taro.showToast({ title: response.data.detail || '删除失败', icon: 'none' })
            }
          } catch (e) {
            Taro.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  }

  return (
    <View className="trip-page">
      {/* 顶部标签 */}
      <View className="tabs">
        <View 
          className={`tab ${activeTab === 'upcoming' ? 'active' : ''}`}
          onClick={() => setActiveTab('upcoming')}
        >
          <Text>即将出发</Text>
        </View>
        <View 
          className={`tab ${activeTab === 'completed' ? 'active' : ''}`}
          onClick={() => setActiveTab('completed')}
        >
          <Text>已完成</Text>
        </View>
      </View>

      <ScrollView className="trip-list" scrollY>
        {filteredTrips.length > 0 ? (
          filteredTrips.map(trip => (
            <View key={trip.id} className="trip-card" onClick={() => handleViewDetail(trip)}>
              {/* 头部背景图片 */}
              <View className="trip-header-bg">
                {trip.cover_url ? (
                  <Image className="trip-cover-image" src={trip.cover_url} mode="aspectFill" />
                ) : (
                  <View className="trip-cover-gradient" />
                )}
                <View className="trip-header-overlay" />
                <View className="trip-header-content">
                  <Text className="trip-destination">{trip.destination}</Text>
                  <Text className="trip-days-badge">{trip.days}日游</Text>
                </View>
              </View>
              
              {/* 路线地图 */}
              {trip.plan_data?.route_map_url && (
                <View className="trip-map-section">
                  <View className="map-label">
                    <Text>🗺️ 推荐路线</Text>
                    <Text className="map-hint">点击放大</Text>
                  </View>
                  <Image 
                    className="trip-map-image" 
                    src={trip.plan_data.route_map_url} 
                    mode="aspectFit"
                    onClick={(e) => {
                      e.stopPropagation()
                      Taro.previewImage({
                        current: trip.plan_data!.route_map_url!,
                        urls: [trip.plan_data!.route_map_url!]
                      })
                    }}
                  />
                </View>
              )}
              
              {/* 底部信息和操作 */}
              <View className="trip-footer">
                <Text className="trip-date">
                  📅 {formatDateRange(trip.start_date, trip.end_date) || '日期待定'}
                </Text>
                <View className="trip-actions">
                  <View className="action-btn primary" onClick={(e) => { e.stopPropagation(); handleViewDetail(trip) }}>
                    <Text>查看详情</Text>
                  </View>
                  <View className="action-btn" onClick={(e) => { e.stopPropagation(); handleShare(trip) }}>
                    <Text>分享</Text>
                  </View>
                  <View className="action-btn danger" onClick={(e) => { e.stopPropagation(); handleDelete(trip) }}>
                    <Text>删除</Text>
                  </View>
                </View>
              </View>
            </View>
          ))
        ) : (
          <View className="empty-state">
            <Text className="empty-icon">🗺️</Text>
            <Text className="empty-title">
              {activeTab === 'upcoming' ? '还没有行程计划' : '还没有完成的行程'}
            </Text>
            <Text className="empty-desc">
              {activeTab === 'upcoming' ? '和我聊聊，开始规划你的下一次旅行吧！' : '完成的行程会显示在这里'}
            </Text>
            {activeTab === 'upcoming' && (
              <View className="create-btn" onClick={handleCreateTrip}>
                <Text>开始规划</Text>
              </View>
            )}
          </View>
        )}
      </ScrollView>

      {/* 悬浮按钮 */}
      {filteredTrips.length > 0 && (
        <View className="fab" onClick={handleCreateTrip}>
          <Text className="fab-icon">+</Text>
        </View>
      )}
    </View>
  )
}
