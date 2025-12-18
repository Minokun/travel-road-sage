import { useState, useEffect } from 'react'
import { View, Text, ScrollView, Image } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useStore } from '@/store'
import { API_BASE } from '@/config'
import './index.scss'

interface FavoriteItem {
  id: string
  destination: string
  days: number
  content: string
  cover_url: string | null
  share_code: string
  author: {
    nickname: string
    avatar_url: string | null
  }
}

export default function FavoritesPage() {
  const { token } = useStore()
  const [favorites, setFavorites] = useState<FavoriteItem[]>([])
  const [loading, setLoading] = useState(true)

  const loadFavorites = async () => {
    if (!token) {
      setLoading(false)
      return
    }

    try {
      const res = await Taro.request({
        url: `${API_BASE}/plans/user/favorites`,
        method: 'GET',
        header: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (res.data.success) {
        setFavorites(res.data.data.plans || [])
      }
    } catch (e) {
      console.error('加载收藏失败', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadFavorites()
  }, [token])

  const handleViewDetail = (item: FavoriteItem) => {
    if (item.share_code) {
      Taro.navigateTo({ url: `/pages/plan/detail?code=${item.share_code}` })
    }
  }

  const handleRemoveFavorite = async (e: any, item: FavoriteItem) => {
    e.stopPropagation()
    
    try {
      const res = await Taro.request({
        url: `${API_BASE}/plans/${item.id}/favorite`,
        method: 'POST',
        header: { 'Authorization': `Bearer ${token}` }
      })

      if (res.data.success && !res.data.data.is_favorited) {
        setFavorites(prev => prev.filter(f => f.id !== item.id))
        Taro.showToast({ title: '已取消收藏', icon: 'none' })
      }
    } catch (e) {
      console.error('取消收藏失败', e)
    }
  }

  if (loading) {
    return (
      <View className="favorites-page">
        <View className="loading-container">
          <Text>加载中...</Text>
        </View>
      </View>
    )
  }

  return (
    <View className="favorites-page">
      <View className="page-header">
        <Text className="page-title">我的收藏</Text>
        <Text className="page-count">{favorites.length} 个收藏</Text>
      </View>

      <ScrollView className="favorites-list" scrollY>
        {favorites.length > 0 ? (
          favorites.map(item => (
            <View key={item.id} className="favorite-card" onClick={() => handleViewDetail(item)}>
              <View className="card-cover">
                {item.cover_url ? (
                  <Image className="cover-image" src={item.cover_url} mode="aspectFill" />
                ) : (
                  <View className="cover-placeholder">
                    <Text>🏞️</Text>
                  </View>
                )}
              </View>
              <View className="card-content">
                <Text className="card-title">{item.destination} {item.days}日游</Text>
                <Text className="card-author">by {item.author.nickname}</Text>
                <Text className="card-desc">{item.content.slice(0, 50)}...</Text>
              </View>
              <View className="card-action" onClick={(e) => handleRemoveFavorite(e, item)}>
                <Text>⭐</Text>
              </View>
            </View>
          ))
        ) : (
          <View className="empty-state">
            <Text className="empty-icon">⭐</Text>
            <Text className="empty-title">还没有收藏</Text>
            <Text className="empty-desc">去发现页面看看有趣的攻略吧</Text>
          </View>
        )}
      </ScrollView>
    </View>
  )
}
