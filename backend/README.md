# 旅行路算子 Backend

**Travel Road Sage - 智能旅行规划后端服务**

> 运筹帷幄，决胜千里之外 —— 不仅懂攻略，更懂实时路况与天气的超级导游

## 🚀 快速开始

### 环境要求

- Python 3.12+
- uv (推荐) 或 pip

### 安装依赖

```bash
# 使用 uv (推荐)
uv sync

# 或使用 pip
pip install -e .
```

### 配置环境变量

创建 `.env` 文件：

```env
# 高德地图 MCP
AMAP_KEY_NAME=your-key-name
AMAP_KEY_VALUE=your-key-value
AMAP_MCP_URL=https://mcp.amap.com/mcp?key=your-key-value

# DeepSeek AI
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=your-api-key
```

### 启动服务

```bash
# 方式 1: 直接运行
python main.py

# 方式 2: 使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后访问：
- API 文档: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📚 API 接口

### 对话接口

| 接口 | 方法 | 描述 |
|:---|:---|:---|
| `/api/chat` | POST | 智能对话 |
| `/api/chat/stream` | POST | 流式对话 |

### 行程规划

| 接口 | 方法 | 描述 |
|:---|:---|:---|
| `/api/plan` | POST | 创建行程规划 |
| `/api/plan/navigate` | POST | 获取导航链接 |

### 地图服务

| 接口 | 方法 | 描述 |
|:---|:---|:---|
| `/api/map/search` | GET | POI 搜索 |
| `/api/map/around` | GET | 周边搜索 |
| `/api/map/poi/{id}` | GET | POI 详情 |
| `/api/map/geocode` | GET | 地理编码 |
| `/api/map/regeocode` | GET | 逆地理编码 |
| `/api/map/weather` | GET | 天气查询 |
| `/api/map/route` | POST | 路径规划 |
| `/api/map/distance` | GET | 距离测量 |

### 搜索服务

| 接口 | 方法 | 描述 |
|:---|:---|:---|
| `/api/search/web` | GET | 网页搜索 |
| `/api/search/guides` | GET | 攻略搜索 |
| `/api/search/xiaohongshu` | GET | 小红书链接 |

## 🏗️ 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI 应用入口
│   ├── config.py        # 配置管理
│   ├── models.py        # 数据模型
│   ├── routers/         # API 路由
│   │   ├── chat.py      # 对话接口
│   │   ├── plan.py      # 行程规划
│   │   ├── map.py       # 地图服务
│   │   └── search.py    # 搜索服务
│   └── services/        # 业务服务
│       ├── amap_mcp.py  # 高德 MCP 客户端
│       ├── deepseek_ai.py # DeepSeek AI
│       ├── search.py    # 搜索服务
│       └── planner.py   # 行程规划器
├── utils/
│   └── ddgs_utils.py    # DuckDuckGo 搜索
├── main.py              # 启动脚本
├── pyproject.toml       # 项目配置
└── .env                 # 环境变量
```

## 🔧 技术栈

- **Web 框架**: FastAPI
- **AI 模型**: DeepSeek V3 (OpenAI 兼容接口)
- **地图服务**: 高德 MCP Server (SSE)
- **搜索引擎**: DuckDuckGo (ddgs)
- **HTTP 客户端**: httpx, aiohttp

## 📝 使用示例

### 创建行程规划

```bash
curl -X POST http://localhost:8000/api/plan \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "杭州",
    "days": 2,
    "preferences": ["美食", "自然"],
    "budget": 2000
  }'
```

### 智能对话

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "帮我规划一个杭州周末两天的行程，重点是美食"
  }'
```

### 查询天气

```bash
curl "http://localhost:8000/api/map/weather?city=杭州"
```

## 📄 License

MIT
