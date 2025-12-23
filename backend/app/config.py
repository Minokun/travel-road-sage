"""
配置管理模块
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Settings:
    """应用配置"""
    
    # 高德地图 MCP 配置 (小程序绑定服务)
    AMAP_KEY_NAME: str = os.getenv("AMAP_KEY_NAME", "")
    AMAP_KEY_VALUE: str = os.getenv("AMAP_KEY_VALUE", "")
    AMAP_MCP_URL: str = os.getenv("AMAP_MCP_URL", "")
    
    # 高德地图 Web 服务 API (天气查询等)
    AMAP_WEB_KEY: str = os.getenv("AMAP_KEY_VALUE_2", "")
    
    # DeepSeek AI 配置
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    
    # 小红书搜索配置
    XIAOHONGSHU_SEARCH_URL: str = "https://www.xiaohongshu.com/search_result"
    
    # 微信小程序配置
    WX_APPID: str = os.getenv("WX_APPID", "")
    WX_SECRET: str = os.getenv("WX_SECRET", "")
    
    # Unsplash API 配置（图片搜索）
    UNSPLASH_ACCESS_KEY: str = os.getenv("UNSPLASH_ACCESS_KEY", "")
    
    # 服务配置
    APP_NAME: str = "旅行路算子 API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()
