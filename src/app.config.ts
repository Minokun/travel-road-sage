export default defineAppConfig({
  pages: [
    'pages/chat/index',
    'pages/trip/index',
    'pages/explore/index',
    'pages/profile/index',
    'pages/plan/detail',
    'pages/favorites/index',
    'pages/settings/index',
    'pages/myplans/index'
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#1a1a2e',
    navigationBarTitleText: '旅行路算子',
    navigationBarTextStyle: 'white',
    backgroundColor: '#f5f5f7'
  },
  tabBar: {
    color: '#999999',
    selectedColor: '#6366f1',
    backgroundColor: '#ffffff',
    borderStyle: 'white',
    list: [
      {
        pagePath: 'pages/chat/index',
        text: '攻略'
      },
      {
        pagePath: 'pages/trip/index',
        text: '行程'
      },
      {
        pagePath: 'pages/explore/index',
        text: '发现'
      },
      {
        pagePath: 'pages/profile/index',
        text: '我的'
      }
    ]
  }
})
