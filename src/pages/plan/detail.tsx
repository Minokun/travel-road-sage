import { useState, useEffect } from 'react'
import { View, Text, ScrollView, Image } from '@tarojs/components'
import Taro, { useRouter, useShareAppMessage, useShareTimeline } from '@tarojs/taro'
import Markdown from '@/components/Markdown'
import { API_BASE } from '@/config'
import './detail.scss'

interface PlanDetail {
  id: string
  destination: string
  days: number
  preferences: string[]
  content: string
  view_count: number
  cover_url: string | null
  created_at: string
  plan_data: {
    route_map_url?: string
  } | null
  author: {
    nickname: string
    avatar_url: string | null
  }
}

export default function PlanDetailPage() {
  const router = useRouter()
  const { code, id } = router.params  // 支持code和id两种参数
  
  const [plan, setPlan] = useState<PlanDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [shareCode, setShareCode] = useState<string>('')  // 用于分享

  useEffect(() => {
    if (code) {
      setShareCode(code)
      loadPlanByShareCode(code)
    } else if (id) {
      loadPlanById(id)
    } else {
      setError('缺少攻略参数')
      setLoading(false)
    }
  }, [code, id])

  // 通过分享码加载（公开攻略）
  const loadPlanByShareCode = async (shareCodeParam: string) => {
    setLoading(true)
    setError('')
    
    try {
      const res = await Taro.request({
        url: `${API_BASE}/plans/share/${shareCodeParam}`,
        method: 'GET'
      })
      
      if (res.data.success) {
        setPlan(res.data.data)
      } else {
        setError(res.data.detail || '攻略不存在')
      }
    } catch (e) {
      console.error('加载攻略失败', e)
      setError('加载失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  // 通过ID加载（我的攻略，需要登录）
  const loadPlanById = async (planId: string) => {
    setLoading(true)
    setError('')
    
    try {
      const token = Taro.getStorageSync('token')
      const res = await Taro.request({
        url: `${API_BASE}/plans/${planId}`,
        method: 'GET',
        header: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
      
      if (res.data.success) {
        const planData = res.data.data
        // 设置分享码用于分享功能
        if (planData.share_code) {
          setShareCode(planData.share_code)
        }
        // 获取用户信息作为作者
        const userStr = Taro.getStorageSync('user')
        const user = userStr ? JSON.parse(userStr) : null
        setPlan({
          ...planData,
          author: {
            nickname: user?.nickname || '我',
            avatar_url: user?.avatar_url || null
          }
        })
      } else {
        setError(res.data.detail || '攻略不存在')
      }
    } catch (e) {
      console.error('加载攻略失败', e)
      setError('加载失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  const handleShare = () => {
    if (!plan) return
    
    const shareText = shareCode 
      ? `【${plan.destination} ${plan.days}日攻略】\n\n${plan.content.slice(0, 200)}...\n\n🔗 分享码: ${shareCode}\n\n—— 由「旅行路算子」生成`
      : `【${plan.destination} ${plan.days}日攻略】\n\n${plan.content.slice(0, 200)}...\n\n—— 由「旅行路算子」生成`
    
    Taro.setClipboardData({
      data: shareText,
      success: () => {
        Taro.showToast({ title: '已复制分享内容', icon: 'success' })
      }
    })
  }

  // 配置微信分享给好友（hooks必须在条件语句之前）
  useShareAppMessage(() => {
    const sharePath = shareCode ? `/pages/plan/detail?code=${shareCode}` : `/pages/plan/detail?id=${id}`
    return {
      title: `🗺️ ${plan?.destination || '旅行'} ${plan?.days || ''}日攻略`,
      path: sharePath,
      imageUrl: plan?.cover_url || plan?.plan_data?.route_map_url || undefined
    }
  })

  // 配置分享到朋友圈
  useShareTimeline(() => {
    const shareQuery = shareCode ? `code=${shareCode}` : `id=${id}`
    return {
      title: `${plan?.destination || '旅行'} ${plan?.days || ''}日攻略 | 旅行路算子`,
      query: shareQuery
    }
  })

  if (loading) {
    return (
      <View className="detail-page">
        <View className="loading-container">
          <Text className="loading-text">加载中...</Text>
        </View>
      </View>
    )
  }

  if (error) {
    return (
      <View className="detail-page">
        <View className="error-container">
          <Text className="error-icon">😕</Text>
          <Text className="error-text">{error}</Text>
          <View className="back-btn" onClick={() => Taro.navigateBack()}>
            <Text>返回</Text>
          </View>
        </View>
      </View>
    )
  }

  if (!plan) return null

  return (
    <View className="detail-page">
      <ScrollView className="detail-scroll" scrollY>
        {/* 头部信息 */}
        <View className="detail-header">
          {plan.cover_url ? (
            <Image className="header-bg-image" src={plan.cover_url} mode="aspectFill" />
          ) : (
            <View className="header-bg" />
          )}
          <View className="header-overlay" />
          <View className="header-content">
            <Text className="destination">{plan.destination}</Text>
            <Text className="days">{plan.days}日游攻略</Text>
            <View className="tags">
              {plan.preferences.map((pref, idx) => (
                <View key={idx} className="tag">
                  <Text>{pref}</Text>
                </View>
              ))}
            </View>
          </View>
        </View>

        {/* 作者信息 */}
        <View className="author-section">
          <View className="author-info">
            {plan.author.avatar_url ? (
              <Image className="author-avatar" src={plan.author.avatar_url} />
            ) : (
              <View className="author-avatar-placeholder">
                <Text>👤</Text>
              </View>
            )}
            <View className="author-detail">
              <Text className="author-name">{plan.author.nickname}</Text>
              <Text className="publish-time">
                {plan.created_at ? new Date(plan.created_at).toLocaleDateString() : ''}
              </Text>
            </View>
          </View>
          <View className="view-count">
            <Text>👁️ {plan.view_count}</Text>
          </View>
        </View>

        {/* 路线地图 */}
        {plan.plan_data?.route_map_url && (
          <View className="route-map-section">
            <View className="section-title">
              <Text>🗺️ 推荐路线</Text>
              <Text className="section-hint">点击放大</Text>
            </View>
            <Image 
              className="route-map-image" 
              src={plan.plan_data.route_map_url} 
              mode="aspectFit"
              showMenuByLongpress
              onClick={() => {
                Taro.previewImage({
                  current: plan.plan_data!.route_map_url!,
                  urls: [plan.plan_data!.route_map_url!]
                })
              }}
            />
          </View>
        )}

        {/* 攻略内容 */}
        <View className="content-section">
          <Markdown content={plan.content} />
        </View>

        <View style={{ height: '120px' }} />
      </ScrollView>

      {/* 底部操作栏 */}
      <View className="bottom-bar">
        <View className="action-btn share-btn" onClick={handleShare}>
          <Text>📤 分享攻略</Text>
        </View>
      </View>
    </View>
  )
}
