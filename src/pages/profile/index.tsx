import { useState, useEffect } from 'react'
import { View, Text, Image, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useStore } from '@/store'
import { API_BASE } from '@/config'
import './index.scss'

export default function ProfilePage() {
  const { isLoggedIn, userInfo, token, setAuth, logout } = useStore()
  const [myPlans, setMyPlans] = useState<any[]>([])
  const [favoritesCount, setFavoritesCount] = useState(0)
  const [loading, setLoading] = useState(false)

  // 加载我的攻略
  const loadMyPlans = async () => {
    if (!token || !isLoggedIn) return
    
    try {
      const res = await Taro.request({
        url: `${API_BASE}/plans`,
        method: 'GET',
        header: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (res.data.success) {
        setMyPlans(res.data.data.plans || [])
      }
    } catch (e) {
      console.error('加载攻略失败', e)
    }
  }

  // 加载收藏数量
  const loadFavoritesCount = async () => {
    if (!token || !isLoggedIn) return
    
    try {
      const res = await Taro.request({
        url: `${API_BASE}/plans/user/favorites`,
        method: 'GET',
        header: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (res.data.success) {
        setFavoritesCount(res.data.data.total || 0)
      }
    } catch (e) {
      console.error('加载收藏失败', e)
    }
  }

  useEffect(() => {
    if (isLoggedIn && token) {
      loadMyPlans()
      loadFavoritesCount()
    }
  }, [isLoggedIn, token])

  // 微信登录
  const handleLogin = async () => {
    setLoading(true)
    
    try {
      // 1. 获取用户信息（需要用户授权）
      const userProfile = await Taro.getUserProfile({
        desc: '用于完善用户资料'
      })
      
      // 2. 获取登录 code
      const loginRes = await Taro.login()
      
      if (!loginRes.code) {
        Taro.showToast({ title: '登录失败', icon: 'none' })
        return
      }
      
      // 3. 调用后端登录接口
      const res = await Taro.request({
        url: `${API_BASE}/user/login`,
        method: 'POST',
        data: {
          code: loginRes.code,
          nickname: userProfile.userInfo.nickName,
          avatar_url: userProfile.userInfo.avatarUrl,
          gender: userProfile.userInfo.gender
        }
      })
      
      if (res.data.success) {
        const { token: newToken, user } = res.data.data
        setAuth(newToken, user)
        Taro.showToast({ title: '登录成功', icon: 'success' })
        loadMyPlans()
      } else {
        Taro.showToast({ title: res.data.detail || '登录失败', icon: 'none' })
      }
    } catch (e: any) {
      console.error('登录失败', e)
      // 用户拒绝授权或其他错误
      if (e.errMsg?.includes('cancel')) {
        Taro.showToast({ title: '已取消授权', icon: 'none' })
      } else {
        // 开发环境使用测试登录
        handleDevLogin()
      }
    } finally {
      setLoading(false)
    }
  }

  // 开发环境测试登录
  const handleDevLogin = async () => {
    try {
      const res = await Taro.request({
        url: `${API_BASE}/user/login/dev`,
        method: 'POST',
        data: {
          nickname: '测试用户',
          avatar_url: ''
        }
      })
      
      if (res.data.success) {
        const { token: newToken, user } = res.data.data
        setAuth(newToken, user)
        Taro.showToast({ title: '测试登录成功', icon: 'success' })
      }
    } catch (e) {
      Taro.showToast({ title: '登录失败', icon: 'none' })
    }
  }

  // 退出登录
  const handleLogout = () => {
    Taro.showModal({
      title: '提示',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          logout()
          setMyPlans([])
          Taro.showToast({ title: '已退出登录', icon: 'success' })
        }
      }
    })
  }

  // 查看攻略详情
  const viewPlan = (plan: any) => {
    Taro.navigateTo({
      url: `/pages/plan/detail?id=${plan.id}`
    })
  }

  // 删除攻略
  const handleDeletePlan = (e: any, plan: any) => {
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
              setMyPlans(prev => prev.filter(p => p.id !== plan.id))
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

  // 菜单点击处理
  const handleMenuClick = (action: string) => {
    switch (action) {
      case 'plans':
        Taro.switchTab({ url: '/pages/trip/index' })
        break
      case 'favorites':
        Taro.navigateTo({ url: '/pages/favorites/index' })
        break
      case 'settings':
        Taro.navigateTo({ url: '/pages/settings/index' })
        break
      case 'feedback':
        Taro.showToast({ title: '功能开发中', icon: 'none' })
        break
      case 'about':
        Taro.showModal({
          title: '关于旅行路算子',
          content: '旅行路算子是一款AI驱动的智能旅行规划助手，帮助您轻松规划完美旅程。\n\n版本：1.0.0',
          showCancel: false
        })
        break
    }
  }

  const menuItems = [
    { icon: '📋', title: '我的攻略', desc: `${myPlans.length} 个攻略`, action: 'plans' },
    { icon: '⭐', title: '我的收藏', desc: `${favoritesCount} 个收藏`, action: 'favorites' },
    { icon: '⚙️', title: '设置', desc: '偏好设置', action: 'settings' },
    { icon: '💬', title: '意见反馈', desc: '帮助我们改进', action: 'feedback' },
    { icon: '📖', title: '关于我们', desc: '了解旅行路算子', action: 'about' }
  ]

  return (
    <View className="profile-page">
      {/* 用户信息卡片 */}
      <View className="user-card">
        {isLoggedIn && userInfo ? (
          <>
            <View className="user-info">
              <View className="avatar">
                {userInfo.avatar_url ? (
                  <Image className="avatar-img" src={userInfo.avatar_url} mode="aspectFill" />
                ) : (
                  <Text className="avatar-text">🧭</Text>
                )}
              </View>
              <View className="info">
                <Text className="nickname">{userInfo.nickname || '旅行者'}</Text>
                <Text className="desc">ID: {userInfo.id}</Text>
              </View>
            </View>
            <View className="logout-btn" onClick={handleLogout}>
              <Text>退出</Text>
            </View>
          </>
        ) : (
          <>
            <View className="user-info">
              <View className="avatar">
                <Text className="avatar-text">🧭</Text>
              </View>
              <View className="info">
                <Text className="nickname">点击登录</Text>
                <Text className="desc">登录后同步你的旅行数据</Text>
              </View>
            </View>
            <View 
              className={`login-btn ${loading ? 'loading' : ''}`} 
              onClick={!loading ? handleLogin : undefined}
            >
              <Text>{loading ? '登录中...' : '微信登录'}</Text>
            </View>
          </>
        )}
      </View>

      {/* 数据统计 */}
      <View className="stats-card">
        <View className="stat-item">
          <Text className="stat-value">{myPlans.length}</Text>
          <Text className="stat-label">攻略</Text>
        </View>
        <View className="stat-item">
          <Text className="stat-value">{favoritesCount}</Text>
          <Text className="stat-label">收藏</Text>
        </View>
        <View className="stat-item">
          <Text className="stat-value">{myPlans.filter(p => p.is_public).length}</Text>
          <Text className="stat-label">分享</Text>
        </View>
      </View>

      {/* 我的攻略列表 */}
      {isLoggedIn && myPlans.length > 0 && (
        <View className="plans-section">
          <View className="section-header">
            <Text className="section-title">我的攻略</Text>
            <Text className="section-more" onClick={() => Taro.navigateTo({ url: '/pages/myplans/index' })}>查看全部 ›</Text>
          </View>
          <View className="plans-list">
            {myPlans.slice(0, 3).map(plan => (
              <View key={plan.id} className="plan-item" onClick={() => viewPlan(plan)}>
                <View className="plan-info">
                  <Text className="plan-title">{plan.destination} {plan.days}日游</Text>
                  <Text className="plan-date">
                    {new Date(plan.created_at).toLocaleDateString()}
                  </Text>
                </View>
                <View className="plan-actions">
                  {plan.is_public && (
                    <View className="plan-badge">
                      <Text>已分享</Text>
                    </View>
                  )}
                  <View className="plan-delete" onClick={(e) => handleDeletePlan(e, plan)}>
                    <Text>🗑️</Text>
                  </View>
                </View>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* 菜单列表 */}
      <View className="menu-list">
        {menuItems.map((item, index) => (
          <View key={index} className="menu-item" onClick={() => handleMenuClick(item.action)}>
            <View className="menu-left">
              <Text className="menu-icon">{item.icon}</Text>
              <View className="menu-text">
                <Text className="menu-title">{item.title}</Text>
                <Text className="menu-desc">{item.desc}</Text>
              </View>
            </View>
            <Text className="menu-arrow">›</Text>
          </View>
        ))}
      </View>

      {/* 版本信息 */}
      <View className="version">
        <Text>旅行路算子 v1.0.0</Text>
      </View>
    </View>
  )
}
