import { useState, useEffect } from 'react'
import { View, Text, ScrollView, Image } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useStore } from '@/store'
import { API_BASE } from '@/config'
import './index.scss'

interface GuideItem {
  id: string
  destination: string
  days: number
  preferences: string[]
  content: string
  view_count: number
  like_count?: number
  share_code: string
  cover_url: string | null
  created_at: string
  is_liked?: boolean
  is_favorited?: boolean
  author: {
    nickname: string
    avatar_url: string | null
  }
}

export default function ExplorePage() {
  const { token } = useStore()
  const [activeCategory, setActiveCategory] = useState('热门')
  const [guides, setGuides] = useState<GuideItem[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  
  const categories = ['热门', '美食', '自然', '文化', '亲子', '休闲']

  // 加载攻略列表
  const loadGuides = async (category: string) => {
    setLoading(true)
    try {
      const res = await Taro.request({
        url: `${API_BASE}/plans/public`,
        method: 'GET',
        data: {
          category: category === '热门' ? '' : category,
          limit: 20,
          offset: 0
        }
      })
      
      if (res.data.success) {
        const plans = res.data.data.plans || []
        setGuides(plans.map((p: GuideItem) => ({ ...p, is_liked: false, is_favorited: false })))
        setTotal(res.data.data.total || 0)
      }
    } catch (e) {
      console.error('加载攻略失败', e)
      setGuides([])
    } finally {
      setLoading(false)
    }
  }

  // 点赞
  const handleLike = async (e: any, guide: GuideItem) => {
    e.stopPropagation()
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      return
    }
    
    try {
      const res = await Taro.request({
        url: `${API_BASE}/plans/${guide.id}/like`,
        method: 'POST',
        header: { 'Authorization': `Bearer ${token}` }
      })
      
      if (res.data.success) {
        setGuides(prev => prev.map(g => 
          g.id === guide.id 
            ? { ...g, is_liked: res.data.data.is_liked, like_count: res.data.data.like_count }
            : g
        ))
      }
    } catch (e) {
      console.error('点赞失败', e)
    }
  }

  // 收藏
  const handleFavorite = async (e: any, guide: GuideItem) => {
    e.stopPropagation()
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      return
    }
    
    try {
      const res = await Taro.request({
        url: `${API_BASE}/plans/${guide.id}/favorite`,
        method: 'POST',
        header: { 'Authorization': `Bearer ${token}` }
      })
      
      if (res.data.success) {
        setGuides(prev => prev.map(g => 
          g.id === guide.id 
            ? { ...g, is_favorited: res.data.data.is_favorited }
            : g
        ))
        Taro.showToast({ 
          title: res.data.data.is_favorited ? '已收藏' : '已取消收藏', 
          icon: 'none' 
        })
      }
    } catch (e) {
      console.error('收藏失败', e)
    }
  }

  // 页面显示时加载数据
  useDidShow(() => {
    loadGuides(activeCategory)
  })

  // 切换分类
  const handleCategoryChange = (category: string) => {
    setActiveCategory(category)
    loadGuides(category)
  }

  // 查看攻略详情
  const handleViewGuide = (guide: GuideItem) => {
    if (guide.share_code) {
      // 有分享码，跳转到详情页
      Taro.navigateTo({
        url: `/pages/plan/detail?code=${guide.share_code}`
      })
    } else {
      // 示例数据，显示提示
      Taro.showToast({ title: '这是示例攻略', icon: 'none' })
    }
  }

  const handleSearch = () => {
    Taro.showToast({ title: '搜索功能开发中', icon: 'none' })
  }

  return (
    <View className="explore-page">
      {/* 搜索栏 */}
      <View className="search-bar" onClick={handleSearch}>
        <Text className="search-icon">🔍</Text>
        <Text className="search-placeholder">搜索目的地、攻略...</Text>
      </View>

      {/* 分类标签 */}
      <ScrollView className="category-scroll" scrollX showScrollbar={false}>
        <View className="category-list">
          {categories.map(cat => (
            <View
              key={cat}
              className={`category-item ${activeCategory === cat ? 'active' : ''}`}
              onClick={() => handleCategoryChange(cat)}
            >
              <Text>{cat}</Text>
            </View>
          ))}
        </View>
      </ScrollView>

      {/* 攻略列表 */}
      <ScrollView className="guide-list" scrollY>
        {loading ? (
          <View className="loading-container">
            <Text className="loading-text">加载中...</Text>
          </View>
        ) : (
          <View className="guide-grid">
            {guides.map(guide => (
              <View 
                key={guide.id} 
                className="guide-card"
                onClick={() => handleViewGuide(guide)}
              >
                <View className="guide-cover">
                  {guide.cover_url ? (
                    <Image className="cover-image" src={guide.cover_url} mode="aspectFill" />
                  ) : (
                    <View className="cover-placeholder">
                      <Text className="cover-emoji">🏞️</Text>
                    </View>
                  )}
                  <View className="destination-tag">
                    <Text>📍 {guide.destination}</Text>
                  </View>
                  <View className="days-tag">
                    <Text>{guide.days}天</Text>
                  </View>
                </View>
                <View className="guide-content">
                  <Text className="guide-title">{guide.destination} {guide.days}日游攻略</Text>
                  <Text className="guide-desc">{guide.content}</Text>
                  <View className="guide-meta">
                    <Text className="guide-author">{guide.author.nickname}</Text>
                    <View className="guide-stats">
                      <View className="stat-item" onClick={(e) => handleLike(e, guide)}>
                        <Text className={guide.is_liked ? 'liked' : ''}>
                          {guide.is_liked ? '❤️' : '🤍'} {guide.like_count || 0}
                        </Text>
                      </View>
                      <View className="stat-item" onClick={(e) => handleFavorite(e, guide)}>
                        <Text className={guide.is_favorited ? 'favorited' : ''}>
                          {guide.is_favorited ? '⭐' : '☆'}
                        </Text>
                      </View>
                      <View className="stat-item">
                        <Text>👁️ {guide.view_count}</Text>
                      </View>
                    </View>
                  </View>
                </View>
              </View>
            ))}
          </View>
        )}
        
        {/* 底部提示 */}
        {!loading && total > 0 && (
          <View className="list-footer">
            <Text>共 {total} 篇攻略</Text>
          </View>
        )}
      </ScrollView>
    </View>
  )
}
