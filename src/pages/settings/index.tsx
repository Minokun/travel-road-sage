import { useState } from 'react'
import { View, Text, Switch } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useStore } from '@/store'
import './index.scss'

export default function SettingsPage() {
  const { logout } = useStore()
  const [notifications, setNotifications] = useState(true)
  const [autoSave, setAutoSave] = useState(true)

  const handleClearCache = () => {
    Taro.showModal({
      title: '清除缓存',
      content: '确定要清除本地缓存吗？',
      success: (res) => {
        if (res.confirm) {
          Taro.clearStorageSync()
          Taro.showToast({ title: '缓存已清除', icon: 'success' })
        }
      }
    })
  }

  const handleLogout = () => {
    Taro.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          logout()
          Taro.showToast({ title: '已退出登录', icon: 'success' })
          Taro.navigateBack()
        }
      }
    })
  }

  return (
    <View className="settings-page">
      <View className="settings-group">
        <View className="group-title">
          <Text>通用设置</Text>
        </View>
        <View className="settings-item">
          <View className="item-left">
            <Text className="item-icon">🔔</Text>
            <Text className="item-title">消息通知</Text>
          </View>
          <Switch 
            checked={notifications} 
            onChange={(e) => setNotifications(e.detail.value)}
            color="#6366f1"
          />
        </View>
        <View className="settings-item">
          <View className="item-left">
            <Text className="item-icon">💾</Text>
            <Text className="item-title">自动保存攻略</Text>
          </View>
          <Switch 
            checked={autoSave} 
            onChange={(e) => setAutoSave(e.detail.value)}
            color="#6366f1"
          />
        </View>
      </View>

      <View className="settings-group">
        <View className="group-title">
          <Text>存储管理</Text>
        </View>
        <View className="settings-item" onClick={handleClearCache}>
          <View className="item-left">
            <Text className="item-icon">🗑️</Text>
            <Text className="item-title">清除缓存</Text>
          </View>
          <Text className="item-arrow">›</Text>
        </View>
      </View>

      <View className="settings-group">
        <View className="group-title">
          <Text>账号</Text>
        </View>
        <View className="settings-item danger" onClick={handleLogout}>
          <View className="item-left">
            <Text className="item-icon">🚪</Text>
            <Text className="item-title">退出登录</Text>
          </View>
          <Text className="item-arrow">›</Text>
        </View>
      </View>

      <View className="version-info">
        <Text>旅行路算子 v1.0.0</Text>
      </View>
    </View>
  )
}
