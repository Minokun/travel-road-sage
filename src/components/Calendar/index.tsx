import { useState, useMemo } from 'react'
import { View, Text } from '@tarojs/components'
import './index.scss'

interface CalendarProps {
  startDate?: string
  endDate?: string
  onSelect: (start: string, end: string) => void
  onClose: () => void
}

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

export default function Calendar({ startDate, endDate, onSelect, onClose }: CalendarProps) {
  const [currentMonth, setCurrentMonth] = useState(() => {
    const now = new Date()
    return { year: now.getFullYear(), month: now.getMonth() }
  })
  
  const [selectStart, setSelectStart] = useState(startDate || '')
  const [selectEnd, setSelectEnd] = useState(endDate || '')
  
  // 生成日历数据
  const calendarData = useMemo(() => {
    const { year, month } = currentMonth
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    const daysInMonth = lastDay.getDate()
    const startWeekday = firstDay.getDay()
    
    const days: Array<{ date: string; day: number; isCurrentMonth: boolean; isToday: boolean; isPast: boolean }> = []
    
    // 上个月的日期填充
    const prevMonthLastDay = new Date(year, month, 0).getDate()
    for (let i = startWeekday - 1; i >= 0; i--) {
      const d = prevMonthLastDay - i
      const prevMonth = month === 0 ? 11 : month - 1
      const prevYear = month === 0 ? year - 1 : year
      days.push({
        date: `${prevYear}-${String(prevMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`,
        day: d,
        isCurrentMonth: false,
        isToday: false,
        isPast: true
      })
    }
    
    // 当月日期
    const today = new Date()
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
    
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      const isPast = new Date(dateStr) < new Date(todayStr)
      days.push({
        date: dateStr,
        day: d,
        isCurrentMonth: true,
        isToday: dateStr === todayStr,
        isPast
      })
    }
    
    // 下个月的日期填充
    const remainingDays = 42 - days.length // 6行7列
    for (let d = 1; d <= remainingDays; d++) {
      const nextMonth = month === 11 ? 0 : month + 1
      const nextYear = month === 11 ? year + 1 : year
      days.push({
        date: `${nextYear}-${String(nextMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`,
        day: d,
        isCurrentMonth: false,
        isToday: false,
        isPast: false
      })
    }
    
    return days
  }, [currentMonth])
  
  // 切换月份
  const changeMonth = (delta: number) => {
    setCurrentMonth(prev => {
      let newMonth = prev.month + delta
      let newYear = prev.year
      if (newMonth < 0) {
        newMonth = 11
        newYear--
      } else if (newMonth > 11) {
        newMonth = 0
        newYear++
      }
      return { year: newYear, month: newMonth }
    })
  }
  
  // 选择日期
  const handleSelectDate = (date: string, isPast: boolean) => {
    if (isPast) return
    
    if (!selectStart || (selectStart && selectEnd)) {
      // 开始新的选择
      setSelectStart(date)
      setSelectEnd('')
    } else {
      // 选择结束日期
      if (date < selectStart) {
        // 如果选择的日期早于开始日期，交换
        setSelectEnd(selectStart)
        setSelectStart(date)
      } else {
        setSelectEnd(date)
      }
    }
  }
  
  // 判断日期是否在选择范围内
  const isInRange = (date: string) => {
    if (!selectStart || !selectEnd) return false
    return date > selectStart && date < selectEnd
  }
  
  // 确认选择
  const handleConfirm = () => {
    if (selectStart && selectEnd) {
      onSelect(selectStart, selectEnd)
      onClose()
    } else if (selectStart) {
      // 如果只选了开始日期，结束日期默认为开始日期
      onSelect(selectStart, selectStart)
      onClose()
    }
  }
  
  // 格式化显示日期
  const formatDisplayDate = (dateStr: string) => {
    if (!dateStr) return '请选择'
    const [y, m, d] = dateStr.split('-')
    const date = new Date(parseInt(y), parseInt(m) - 1, parseInt(d))
    const weekday = WEEKDAYS[date.getDay()]
    return `${m}月${d}日 周${weekday}`
  }
  
  // 计算天数
  const dayCount = useMemo(() => {
    if (!selectStart || !selectEnd) return 0
    const start = new Date(selectStart)
    const end = new Date(selectEnd)
    return Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1
  }, [selectStart, selectEnd])

  return (
    <View className="calendar-overlay" onClick={onClose}>
      <View className="calendar-container" onClick={e => e.stopPropagation()}>
        {/* 头部 */}
        <View className="calendar-header">
          <Text className="header-title">选择出行日期</Text>
          <Text className="header-close" onClick={onClose}>✕</Text>
        </View>
        
        {/* 已选日期显示 */}
        <View className="selected-dates">
          <View className="date-item">
            <Text className="date-label">出发</Text>
            <Text className={`date-value ${selectStart ? 'active' : ''}`}>
              {formatDisplayDate(selectStart)}
            </Text>
          </View>
          <View className="date-arrow">→</View>
          <View className="date-item">
            <Text className="date-label">返回</Text>
            <Text className={`date-value ${selectEnd ? 'active' : ''}`}>
              {formatDisplayDate(selectEnd)}
            </Text>
          </View>
          {dayCount > 0 && (
            <View className="day-count">
              <Text>共{dayCount}天</Text>
            </View>
          )}
        </View>
        
        {/* 月份切换 */}
        <View className="month-nav">
          <Text className="nav-btn" onClick={() => changeMonth(-1)}>‹</Text>
          <Text className="month-title">{currentMonth.year}年{currentMonth.month + 1}月</Text>
          <Text className="nav-btn" onClick={() => changeMonth(1)}>›</Text>
        </View>
        
        {/* 星期标题 */}
        <View className="weekday-row">
          {WEEKDAYS.map(w => (
            <Text key={w} className={`weekday-item ${w === '日' || w === '六' ? 'weekend' : ''}`}>{w}</Text>
          ))}
        </View>
        
        {/* 日期网格 */}
        <View className="days-grid">
          {calendarData.map((item, idx) => {
            const isStart = item.date === selectStart
            const isEnd = item.date === selectEnd
            const inRange = isInRange(item.date)
            
            return (
              <View
                key={idx}
                className={`day-cell 
                  ${!item.isCurrentMonth ? 'other-month' : ''} 
                  ${item.isToday ? 'today' : ''} 
                  ${item.isPast ? 'past' : ''} 
                  ${isStart ? 'start' : ''} 
                  ${isEnd ? 'end' : ''} 
                  ${inRange ? 'in-range' : ''}
                `}
                onClick={() => handleSelectDate(item.date, item.isPast)}
              >
                <Text className="day-num">{item.day}</Text>
                {item.isToday && <Text className="day-tag">今天</Text>}
                {isStart && <Text className="day-tag">出发</Text>}
                {isEnd && !isStart && <Text className="day-tag">返回</Text>}
              </View>
            )
          })}
        </View>
        
        {/* 确认按钮 */}
        <View className="calendar-footer">
          <View 
            className={`confirm-btn ${selectStart ? 'active' : ''}`}
            onClick={handleConfirm}
          >
            <Text>确定</Text>
          </View>
        </View>
      </View>
    </View>
  )
}
