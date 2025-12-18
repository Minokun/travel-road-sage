import { useState, useEffect } from 'react'
import { View, Text, ScrollView, Image } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useStore } from '@/store'
import { API_BASE } from '@/config'
import './index.scss'

interface PlanItem {
  id: string
  destination: string
  days: number
  content: string
  cover_url: string | null
  share_code: string | null
  is_public: boolean
  created_at: string
}

export default function MyPlansPage() {
  const { token } = useStore()
  const [plans, setPlans] = useState<PlanItem[]>([])
  const [loading, setLoading] = useState(true)

  const loadPlans = async () => {
    if (!token) {
      setLoading(false)
      return
    }

    try {
      const res = await Taro.request({
        url: `${API_BASE}/plans`,
        method: 'GET',
        header: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (res.data.success) {
        setPlans(res.data.data.plans || [])
      }
    } catch (e) {
      console.error('加载攻略失败', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPlans()
  }, [token])

  const handleViewDetail = (plan: PlanItem) => {
    if (plan.share_code) {
      Taro.navigateTo({ url: `/pages/plan/detail?code=${plan.share_code}` })
    } else {
      Taro.navigateTo({ url: `/pages/plan/detail?id=${plan.id}` })
    }
  }

  const handleDelete = (e: any, plan: PlanItem) => {
    e.stopPropagation()
    
    Taro.showModal({
      title: '确认删除',
      content: `确定要删除「${plan.destination} ${plan.days}日游」吗？`,
      confirmColor: '#ef4444',
      success: async (res) => {
        if (res.confirm) {
          try {
            const response = await Taro.request({
              url: `${API_BASE}/plans/${plan.id}`,
              method: 'DELETE',
              header: {
                'Authorization': `Bearer ${token}`
              }
            })
            
            if (response.data.success) {
              setPlans(prev => prev.filter(p => p.id !== plan.id))
              Taro.showToast({ title: '删除成功', icon: 'success' })
            } else {
              Taro.showToast({ title: response.data.detail || '删除失败', icon: 'none' })
            }
          } catch (err) {
            Taro.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  }

  const handleShare = async (e: any, plan: PlanItem) => {
    e.stopPropagation()
    
    if (!plan.share_code) {
      try {
        const res = await Taro.request({
          url: `${API_BASE}/plans/${plan.id}/share`,
          method: 'POST',
          header: { 'Authorization': `Bearer ${token}` },
          data: { is_public: true }
        })
        
        if (res.data.success && res.data.data.share_code) {
          Taro.setClipboardData({
            data: `【${plan.destination} ${plan.days}日游】\n🔗 分享码: ${res.data.data.share_code}\n\n—— 由「旅行路算子」生成`,
            success: () => {
              Taro.showToast({ title: '已复制分享内容', icon: 'success' })
              loadPlans()
            }
          })
        }
      } catch (err) {
        Taro.showToast({ title: '分享失败', icon: 'none' })
      }
    } else {
      Taro.setClipboardData({
        data: `【${plan.destination} ${plan.days}日游】\n🔗 分享码: ${plan.share_code}\n\n—— 由「旅行路算子」生成`,
        success: () => {
          Taro.showToast({ title: '已复制分享内容', icon: 'success' })
        }
      })
    }
  }

  if (loading) {
    return (
      <View className="myplans-page">
        <View className="loading-container">
          <Text>加载中...</Text>
        </View>
      </View>
    )
  }

  return (
    <View className="myplans-page">
      <View className="page-header">
        <Text className="page-title">我的攻略</Text>
        <Text className="page-count">{plans.length} 个攻略</Text>
      </View>

      <ScrollView className="plans-list" scrollY>
        {plans.length > 0 ? (
          plans.map(plan => (
            <View key={plan.id} className="plan-card" onClick={() => handleViewDetail(plan)}>
              <View className="card-cover">
                {plan.cover_url ? (
                  <Image className="cover-image" src={plan.cover_url} mode="aspectFill" />
                ) : (
                  <View className="cover-placeholder">
                    <Text>🏞️</Text>
                  </View>
                )}
                {plan.is_public && (
                  <View className="public-badge">
                    <Text>已分享</Text>
                  </View>
                )}
              </View>
              <View className="card-content">
                <Text className="card-title">{plan.destination} {plan.days}日游</Text>
                <Text className="card-date">
                  {new Date(plan.created_at).toLocaleDateString()}
                </Text>
                <View className="card-actions">
                  <View className="action-btn share" onClick={(e) => handleShare(e, plan)}>
                    <Text>📤 分享</Text>
                  </View>
                  <View className="action-btn delete" onClick={(e) => handleDelete(e, plan)}>
                    <Text>🗑️ 删除</Text>
                  </View>
                </View>
              </View>
            </View>
          ))
        ) : (
          <View className="empty-state">
            <Text className="empty-icon">📋</Text>
            <Text className="empty-title">还没有攻略</Text>
            <Text className="empty-desc">去生成你的第一个旅行攻略吧</Text>
            <View className="create-btn" onClick={() => Taro.switchTab({ url: '/pages/chat/index' })}>
              <Text>开始规划</Text>
            </View>
          </View>
        )}
      </ScrollView>
    </View>
  )
}
