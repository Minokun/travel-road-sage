import { useState, useMemo } from 'react'
import { View, Text, Input, ScrollView, Textarea, Image, Picker } from '@tarojs/components'
import Taro, { useShareAppMessage, useShareTimeline } from '@tarojs/taro'
import Markdown from '@/components/Markdown'
import Calendar from '@/components/Calendar'
import { useStore } from '@/store'
import { API_BASE } from '@/config'
import './index.scss'

// 生成状态
type GenerateStatus = 
  | 'idle'           // 空闲
  | 'extracting'     // 信息提取
  | 'weather'        // 天气查询
  | 'searching'      // 搜索攻略
  | 'attractions'    // 搜索景点
  | 'generating'     // AI生成中
  | 'enriching'      // 补充详情
  | 'done'           // 完成
  | 'error'          // 错误

const STATUS_TEXT: Record<GenerateStatus, string> = {
  idle: '',
  extracting: '📝 正在提取旅行信息...',
  weather: '🌤️ 正在查询目的地天气...',
  searching: '🔍 正在搜索旅行攻略...',
  attractions: '🏛️ 正在搜索热门景点...',
  generating: '✨ AI正在生成行程规划...',
  enriching: '📍 正在补充路线详情...',
  done: '✅ 攻略生成完成！',
  error: '❌ 生成失败，请重试'
}

// 偏好选项
const PREFERENCES = [
  { label: '美食', value: '美食', icon: '🍜' },
  { label: '自然', value: '自然', icon: '🌿' },
  { label: '文化', value: '文化', icon: '🏛️' },
  { label: '购物', value: '购物', icon: '🛍️' },
  { label: '亲子', value: '亲子', icon: '👨‍👩‍👧' },
  { label: '摄影', value: '摄影', icon: '📷' },
  { label: '休闲', value: '休闲', icon: '☕' },
  { label: '冒险', value: '冒险', icon: '🎢' },
  { label: '网红打卡', value: '网红打卡', icon: '📱' },
  { label: '小众秘境', value: '小众秘境', icon: '🗺️' }
]

// 计算两个日期之间的天数
const calcDays = (start: string, end: string): number => {
  if (!start || !end) return 0
  const startDate = new Date(start)
  const endDate = new Date(end)
  const diff = endDate.getTime() - startDate.getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24)) + 1
}

// 格式化日期显示
const formatDate = (dateStr: string): string => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const month = date.getMonth() + 1
  const day = date.getDate()
  const weekDays = ['日', '一', '二', '三', '四', '五', '六']
  const weekDay = weekDays[date.getDay()]
  return `${month}月${day}日 周${weekDay}`
}

// 交通方式选项
const TRANSPORT_MODES = [
  { label: '公共交通', value: 'transit', icon: '🚇', desc: '地铁公交' },
  { label: '步行', value: 'walking', icon: '🚶', desc: '深度慢游' },
  { label: '骑行', value: 'bicycling', icon: '🚴', desc: '环湖滨海' },
  { label: '自驾', value: 'driving', icon: '🚗', desc: '自由灵活' }
]

// 出行人群选项
const TRAVEL_WITH = [
  { label: '独自旅行', value: '独自旅行', icon: '🧳' },
  { label: '情侣出游', value: '情侣出游', icon: '💑' },
  { label: '闺蜜/兄弟', value: '朋友结伴', icon: '👯' },
  { label: '家庭亲子', value: '家庭亲子', icon: '👨‍👩‍👧' },
  { label: '带父母', value: '带父母', icon: '👴👵' }
]

// 预算范围
const BUDGET_OPTIONS = [
  { label: '穷游', value: 'low', icon: '💰', desc: '省钱为主' },
  { label: '舒适', value: 'medium', icon: '💰💰', desc: '性价比' },
  { label: '轻奢', value: 'high', icon: '💰💰💰', desc: '品质优先' }
]

export default function ChatPage() {
  const { isLoggedIn, token } = useStore()
  
  // 表单状态
  const [destination, setDestination] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [selectedPrefs, setSelectedPrefs] = useState<string[]>([])
  const [description, setDescription] = useState('')
  const [transportMode, setTransportMode] = useState('transit')
  const [travelWith, setTravelWith] = useState('')
  const [budgetLevel, setBudgetLevel] = useState('')
  
  // 计算天数
  const days = useMemo(() => calcDays(startDate, endDate), [startDate, endDate])
  
  // 获取今天的日期字符串
  const today = useMemo(() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  }, [])
  
  // 日历显示状态
  const [showCalendar, setShowCalendar] = useState(false)
  
  // 生成状态
  const [status, setStatus] = useState<GenerateStatus>('idle')
  const [result, setResult] = useState<string>('')
  const [planData, setPlanData] = useState<any>(null)
  const [routeMapUrl, setRouteMapUrl] = useState<string>('')
  const [savedPlanId, setSavedPlanId] = useState<string | null>(null)

  // 过滤掉AI回复中的JSON代码块
  const filterJsonFromReply = (reply: string): string => {
    // 移除 ```json ... ``` 代码块
    return reply.replace(/```json[\s\S]*?```/g, '').trim()
  }

  // 切换偏好
  const togglePref = (pref: string) => {
    setSelectedPrefs(prev => 
      prev.includes(pref) 
        ? prev.filter(p => p !== pref)
        : [...prev, pref]
    )
  }

  // 模拟状态更新（实际应该由后端SSE推送）
  const simulateStatusUpdates = async () => {
    const statuses: GenerateStatus[] = [
      'extracting', 'weather', 'searching', 'attractions', 'generating', 'enriching'
    ]
    for (const s of statuses) {
      setStatus(s)
      await new Promise(resolve => setTimeout(resolve, 800))
    }
  }

  // 生成攻略
  const generatePlan = async () => {
    if (!destination.trim()) {
      Taro.showToast({ title: '请输入目的地', icon: 'none' })
      return
    }
    
    if (!startDate || !endDate) {
      Taro.showToast({ title: '请选择出行日期', icon: 'none' })
      return
    }
    
    if (days <= 0) {
      Taro.showToast({ title: '结束日期需晚于开始日期', icon: 'none' })
      return
    }

    setStatus('extracting')
    setResult('')
    setPlanData(null)

    // 开始状态模拟
    simulateStatusUpdates()

    try {
      // 构建完整的描述信息
      let fullDescription = description.trim()
      if (travelWith) {
        fullDescription = `出行人群：${travelWith}。${fullDescription}`
      }
      if (budgetLevel) {
        const budgetMap = { low: '穷游省钱', medium: '舒适性价比', high: '轻奢品质' }
        fullDescription = `预算偏好：${budgetMap[budgetLevel] || budgetLevel}。${fullDescription}`
      }
      
      const res = await Taro.request({
        url: `${API_BASE}/plan`,
        method: 'POST',
        timeout: 900000, // 15分钟超时（AI生成+路径规划需要较长时间）
        data: {
          destination: destination.trim(),
          days: days,
          preferences: selectedPrefs,
          description: fullDescription,
          transport_mode: transportMode
        },
        header: {
          'Content-Type': 'application/json'
        }
      })

      if (res.data.success) {
        setStatus('done')
        // 过滤掉JSON数据块
        const cleanReply = filterJsonFromReply(res.data.data.reply || '')
        setResult(cleanReply)
        setPlanData(res.data.data.plan)
        // 优先使用base64数据，避免微信域名校验问题
        setRouteMapUrl(res.data.data.route_map_base64 || res.data.data.route_map_url || '')
        
        // 自动保存到行程
        if (isLoggedIn && token) {
          await autoSavePlan(cleanReply, res.data.data.plan)
        }
      } else {
        setStatus('error')
        setResult(res.data.error || '生成失败')
      }
    } catch (error: any) {
      console.error('生成攻略失败:', error)
      setStatus('error')
      setResult(error.errMsg || '网络请求失败，请检查网络连接')
    }
  }
  
  // 自动保存攻略到行程
  const autoSavePlan = async (content: string, plan: any) => {
    try {
      const res = await Taro.request({
        url: `${API_BASE}/plans`,
        method: 'POST',
        header: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        data: {
          destination,
          days,
          start_date: startDate,
          end_date: endDate,
          preferences: selectedPrefs,
          description,
          content: content,
          plan_data: plan,
          is_public: false
        }
      })
      
      if (res.data.success) {
        setSavedPlanId(res.data.data.id)
        Taro.showToast({ title: '已保存到行程', icon: 'success' })
      }
    } catch (e) {
      console.error('自动保存失败', e)
    }
  }

  // 重置表单
  const resetForm = () => {
    setDestination('')
    setStartDate('')
    setEndDate('')
    setSelectedPrefs([])
    setDescription('')
    setTransportMode('transit')
    setTravelWith('')
    setBudgetLevel('')
    setStatus('idle')
    setResult('')
    setPlanData(null)
    setRouteMapUrl('')
    setSavedPlanId(null)
  }

  // 保存攻略到云端
  const savePlan = async () => {
    if (!result || !destination) return
    
    // 检查是否已保存
    if (savedPlanId) {
      Taro.showToast({ title: '攻略已保存', icon: 'none' })
      return
    }
    
    // 检查登录状态
    if (!isLoggedIn || !token) {
      Taro.showModal({
        title: '提示',
        content: '请先登录后再保存攻略',
        confirmText: '去登录',
        success: (res) => {
          if (res.confirm) {
            Taro.switchTab({ url: '/pages/profile/index' })
          }
        }
      })
      return
    }
    
    try {
      const res = await Taro.request({
        url: `${API_BASE}/plans`,
        method: 'POST',
        header: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        data: {
          destination,
          days,
          start_date: startDate,
          end_date: endDate,
          preferences: selectedPrefs,
          description,
          content: result,
          plan_data: planData,
          is_public: false
        }
      })
      
      if (res.data.success) {
        setSavedPlanId(res.data.data.id)
        Taro.showToast({ title: '保存成功', icon: 'success' })
      } else {
        Taro.showToast({ title: res.data.detail || '保存失败', icon: 'none' })
      }
    } catch (e) {
      console.error('保存失败', e)
      Taro.showToast({ title: '保存失败', icon: 'none' })
    }
  }

  // 分享攻略（设为公开并获取分享链接）
  const sharePlan = async () => {
    if (!result) return
    
    // 显示分享选项
    Taro.showActionSheet({
      itemList: ['分享给微信好友', '复制攻略内容'],
      success: async (res) => {
        if (res.tapIndex === 0) {
          // 分享给微信好友 - 需要先保存并获取分享码
          let shareCode = ''
          if (savedPlanId && token) {
            try {
              const shareRes = await Taro.request({
                url: `${API_BASE}/plans/${savedPlanId}/share`,
                method: 'POST',
                header: {
                  'Authorization': `Bearer ${token}`
                },
                data: { is_public: true }
              })
              if (shareRes.data.success) {
                shareCode = shareRes.data.data.share_code
              }
            } catch (e) {
              console.error('获取分享码失败', e)
            }
          }
          
          // 触发微信分享
          // 注意：小程序中需要通过button的open-type="share"或页面的onShareAppMessage来触发
          // 这里我们设置分享数据，然后提示用户点击右上角分享
          Taro.showModal({
            title: '分享攻略',
            content: '请点击右上角「...」按钮，选择「发送给朋友」即可分享给微信好友',
            showCancel: false,
            confirmText: '我知道了'
          })
        } else if (res.tapIndex === 1) {
          // 复制攻略内容
          let shareText = `【${destination} ${days}日攻略】\n\n${result}\n\n—— 由「旅行路算子」生成`
          
          // 如果已保存，尝试获取分享码
          if (savedPlanId && token) {
            try {
              const shareRes = await Taro.request({
                url: `${API_BASE}/plans/${savedPlanId}/share`,
                method: 'POST',
                header: {
                  'Authorization': `Bearer ${token}`
                },
                data: { is_public: true }
              })
              if (shareRes.data.success && shareRes.data.data.share_code) {
                shareText = `【${destination} ${days}日攻略】\n\n${result}\n\n🔗 分享码: ${shareRes.data.data.share_code}\n\n—— 由「旅行路算子」生成`
              }
            } catch (e) {
              console.error('获取分享码失败', e)
            }
          }
          
          Taro.setClipboardData({
            data: shareText,
            success: () => {
              Taro.showToast({ title: '已复制到剪贴板', icon: 'success' })
            }
          })
        }
      }
    })
  }
  
  // 配置页面分享给好友
  useShareAppMessage(() => {
    // 需要使用分享码而不是planId
    return {
      title: `🗺️ ${destination || '旅行'} ${days || ''}日攻略 | 旅行路算子`,
      path: savedPlanId ? `/pages/plan/detail?code=${savedPlanId}` : '/pages/chat/index',
      imageUrl: routeMapUrl || undefined
    }
  })

  // 配置分享到朋友圈
  useShareTimeline(() => {
    return {
      title: `${destination || '旅行'} ${days || ''}日攻略 | 旅行路算子`,
      query: savedPlanId ? `code=${savedPlanId}` : ''
    }
  })

  // 热门目的地
  const hotDestinations = ['杭州', '成都', '重庆', '西安', '厦门', '三亚']

  return (
    <View className="plan-page">
      <ScrollView className="plan-scroll" scrollY>
        {/* 头部 */}
        <View className="plan-header">
          <Text className="header-title">旅行路算子</Text>
          <Text className="header-subtitle">告诉我你想去哪，一键生成专属攻略</Text>
        </View>

        {/* 输入表单 */}
        <View className="plan-form">
          {/* 目的地 */}
          <View className="form-section">
            <Text className="form-label">📍 目的地</Text>
            <Input
              className="form-input"
              placeholder="输入城市名称，如：杭州"
              placeholderClass="placeholder"
              value={destination}
              onInput={(e) => setDestination(e.detail.value)}
            />
            <View className="hot-destinations">
              {hotDestinations.map(city => (
                <View 
                  key={city} 
                  className={`hot-item ${destination === city ? 'active' : ''}`}
                  onClick={() => setDestination(city)}
                >
                  <Text>{city}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 出行日期 */}
          <View className="form-section">
            <Text className="form-label">📅 出行日期</Text>
            <View className="date-selector" onClick={() => setShowCalendar(true)}>
              <View className={`date-picker-item ${startDate ? 'has-value' : ''}`}>
                <Text className="date-label">出发</Text>
                <Text className="date-value">{startDate ? formatDate(startDate) : '选择日期'}</Text>
              </View>
              <View className="date-arrow">→</View>
              <View className={`date-picker-item ${endDate ? 'has-value' : ''}`}>
                <Text className="date-label">返回</Text>
                <Text className="date-value">{endDate ? formatDate(endDate) : '选择日期'}</Text>
              </View>
            </View>
            {days > 0 && (
              <View className="days-summary">
                <Text>共 {days} 天行程</Text>
              </View>
            )}
          </View>

          {/* 偏好 */}
          <View className="form-section">
            <Text className="form-label">❤️ 旅行偏好（可多选）</Text>
            <View className="pref-list">
              {PREFERENCES.map(pref => (
                <View
                  key={pref.value}
                  className={`pref-item ${selectedPrefs.includes(pref.value) ? 'active' : ''}`}
                  onClick={() => togglePref(pref.value)}
                >
                  <Text>{pref.icon} {pref.label}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 出行人群 */}
          <View className="form-section">
            <Text className="form-label">👥 和谁一起（选填）</Text>
            <View className="travel-with-list">
              {TRAVEL_WITH.map(item => (
                <View
                  key={item.value}
                  className={`travel-with-item ${travelWith === item.value ? 'active' : ''}`}
                  onClick={() => setTravelWith(travelWith === item.value ? '' : item.value)}
                >
                  <Text>{item.icon} {item.label}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 预算范围 */}
          <View className="form-section">
            <Text className="form-label">💰 预算范围（选填）</Text>
            <View className="budget-list">
              {BUDGET_OPTIONS.map(item => (
                <View
                  key={item.value}
                  className={`budget-item ${budgetLevel === item.value ? 'active' : ''}`}
                  onClick={() => setBudgetLevel(budgetLevel === item.value ? '' : item.value)}
                >
                  <Text className="budget-icon">{item.icon}</Text>
                  <Text className="budget-label">{item.label}</Text>
                  <Text className="budget-desc">{item.desc}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 交通方式 */}
          <View className="form-section">
            <Text className="form-label">🚗 出行方式</Text>
            <View className="transport-list">
              {TRANSPORT_MODES.map(mode => (
                <View
                  key={mode.value}
                  className={`transport-item ${transportMode === mode.value ? 'active' : ''}`}
                  onClick={() => setTransportMode(mode.value)}
                >
                  <Text>{mode.icon} {mode.label}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 具体描述 */}
          <View className="form-section">
            <Text className="form-label">💬 具体描述（选填）</Text>
            <Textarea
              className="form-textarea"
              placeholder="描述你的特别需求，如：想去网红打卡点、带老人出行、预算有限..."
              placeholderClass="placeholder"
              value={description}
              onInput={(e) => setDescription(e.detail.value)}
              maxlength={200}
            />
            <Text className="char-count">{description.length}/200</Text>
          </View>

          {/* 生成按钮 */}
          <View 
            className={`generate-btn ${status !== 'idle' && status !== 'done' && status !== 'error' ? 'loading' : ''}`}
            onClick={status === 'idle' || status === 'done' || status === 'error' ? generatePlan : undefined}
          >
            <Text>
              {status === 'idle' || status === 'done' || status === 'error' 
                ? '🚀 生成攻略' 
                : '生成中...'}
            </Text>
          </View>
        </View>

        {/* 状态显示 */}
        {status !== 'idle' && (
          <View className="status-section">
            <View className="status-card">
              <View className="status-header">
                <Text className="status-title">生成进度</Text>
                {(status === 'done' || status === 'error') && (
                  <Text className="status-reset" onClick={resetForm}>重新生成</Text>
                )}
              </View>
              
              <View className="status-steps">
                {(['extracting', 'weather', 'searching', 'attractions', 'generating', 'enriching'] as GenerateStatus[]).map((s, idx) => {
                  const isActive = status === s
                  const isDone = ['extracting', 'weather', 'searching', 'attractions', 'generating', 'enriching', 'done'].indexOf(status) > idx
                  const isError = status === 'error'
                  
                  return (
                    <View key={s} className={`step-item ${isActive ? 'active' : ''} ${isDone ? 'done' : ''} ${isError ? 'error' : ''}`}>
                      <View className="step-dot">
                        {isDone && !isActive ? <Text>✓</Text> : <Text>{idx + 1}</Text>}
                      </View>
                      <Text className="step-text">{STATUS_TEXT[s]}</Text>
                    </View>
                  )
                })}
              </View>

              {!['idle', 'done', 'error'].includes(status) && (
                <View className="status-loading">
                  <View className="loading-bar">
                    <View className="loading-progress" />
                  </View>
                  <View className="loading-tip">
                    <Text className="tip-icon">⏱️</Text>
                    <Text className="tip-text">攻略生成需要1-3分钟，请耐心等待</Text>
                  </View>
                  <Text className="tip-hint">正在为您规划最佳路线，请勿离开页面</Text>
                </View>
              )}
            </View>
          </View>
        )}

        {/* 结果展示 */}
        {result && status === 'done' && (
          <View className="result-section">
            {/* 路线地图 */}
            {routeMapUrl && (
              <View className="route-map-card">
                <View className="map-header">
                  <Text className="map-title">🗺️ 推荐路线</Text>
                  <Text className="map-hint">点击放大</Text>
                </View>
                <Image 
                  className="route-map-image" 
                  src={routeMapUrl} 
                  mode="aspectFit"
                  showMenuByLongpress
                  onError={(e) => console.error('地图加载失败:', e, routeMapUrl)}
                  onLoad={() => console.log('地图加载成功')}
                  onClick={() => {
                    Taro.previewImage({
                      current: routeMapUrl,
                      urls: [routeMapUrl]
                    })
                  }}
                />
              </View>
            )}
            
            <View className="result-card">
              <View className="result-header">
                <Text className="result-title">📋 {destination} {days}日攻略</Text>
              </View>
              <View className="result-content">
                <Markdown content={result} />
              </View>
              
              {/* 操作按钮 */}
              <View className="result-actions">
                <View className="action-btn save-btn" onClick={savePlan}>
                  <Text>💾 保存攻略</Text>
                </View>
                <View className="action-btn share-btn" onClick={sharePlan}>
                  <Text>📤 分享攻略</Text>
                </View>
              </View>
            </View>
            
            {/* 重置按钮 */}
            <View className="reset-section">
              <View className="reset-btn" onClick={resetForm}>
                <Text>🔄 生成新攻略</Text>
              </View>
            </View>
          </View>
        )}

        <View style={{ height: '100px' }} />
      </ScrollView>
      
      {/* 日历选择器 */}
      {showCalendar && (
        <Calendar
          startDate={startDate}
          endDate={endDate}
          onSelect={(start, end) => {
            setStartDate(start)
            setEndDate(end)
          }}
          onClose={() => setShowCalendar(false)}
        />
      )}
    </View>
  )
}
