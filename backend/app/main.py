"""
旅行陆算子 API 主入口
Travel Road Sage - 智能旅行规划后端服务
"""
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.routers import chat, plan, map, search, user, plans, admin

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 设置第三方库日志级别
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    
    # 掩码处理 MCP URL
    mcp_url = settings.AMAP_MCP_URL
    if "key=" in mcp_url:
        base, key = mcp_url.split("key=")
        masked_key = key[:4] + "*" * 8 + key[-4:] if len(key) > 8 else "****"
        mcp_url = f"{base}key={masked_key}"
    
    print(f"📍 高德 MCP: {mcp_url}")
    print(f"🤖 DeepSeek Model: {settings.DEEPSEEK_MODEL}")
    yield
    # 关闭时
    print("👋 服务关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## 旅行路算子 API

**「运筹帷幄，决胜千里之外」**

不仅懂攻略，更懂实时路况与天气的超级导游

### 核心能力

- 🤖 **智能对话** - 自然语言交互，理解旅行需求
- 🗺️ **路线规划** - 基于高德地图的智能路径规划
- ⛅ **天气查询** - 实时天气预报，动态调整行程
- 🔍 **攻略搜索** - 整合多源信息，提供最新攻略
- 📍 **POI 搜索** - 景点、美食、住宿一站式搜索
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api")
app.include_router(plan.router, prefix="/api")
app.include_router(map.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(plans.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/", tags=["健康检查"])
async def root():
    """API 根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "services": {
            "amap_mcp": bool(settings.AMAP_MCP_URL),
            "deepseek": bool(settings.DEEPSEEK_API_KEY)
        }
    }
