import { PropsWithChildren, useEffect } from 'react'
import Taro from '@tarojs/taro'
import { useStore } from './store'
import { API_BASE } from './config'
import './app.scss'

function App({ children }: PropsWithChildren) {
  const { loadAuth, setAuth, isLoggedIn } = useStore()

  // 自动登录函数
  const autoLogin = async () => {
    try {
      // 1. 获取用户信息（需要用户授权）
      const userProfile = await Taro.getUserProfile({
        desc: '用于完善用户资料'
      })
      
      // 2. 获取登录 code
      const loginRes = await Taro.login()
      
      if (!loginRes.code) {
        console.log('获取登录code失败')
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
        console.log('自动登录成功')
      }
    } catch (e: any) {
      console.log('用户取消授权或登录失败', e?.errMsg)
      // 用户取消授权，不做处理，可以稍后在个人页面登录
    }
  }

  useEffect(() => {
    // 加载本地存储的登录状态
    loadAuth()
  }, [])

  // 小程序启动时检查登录状态并请求授权
  Taro.useLaunch(() => {
    console.log('App launched.')
    
    // 延迟检查，确保loadAuth完成
    setTimeout(() => {
      const token = Taro.getStorageSync('token')
      if (!token) {
        // 未登录，请求用户授权
        autoLogin()
      }
    }, 500)
  })

  return children
}

export default App
