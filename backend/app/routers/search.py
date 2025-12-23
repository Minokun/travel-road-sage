"""
搜索 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from app.services.search import search_service

router = APIRouter(prefix="/search", tags=["搜索"])


@router.get("/web")
async def search_web(
    query: str = Query(..., description="搜索关键词"),
    search_type: str = Query("text", description="搜索类型: text/images/videos/news"),
    max_results: int = Query(10, ge=1, le=30, description="最大结果数")
):
    """
    网页搜索
    
    使用 DuckDuckGo 搜索网页内容
    """
    try:
        results = await search_service.search_web(query, search_type, max_results)
        return {
            "success": True,
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/guides")
async def search_travel_guides(
    destination: str = Query(..., description="目的地"),
    preferences: Optional[str] = Query(None, description="偏好标签，逗号分隔")
):
    """
    搜索旅行攻略
    
    综合搜索多个来源的旅行攻略
    """
    try:
        prefs = preferences.split(",") if preferences else []
        results = await search_service.search_travel_guides(destination, prefs)
        return {
            "success": True,
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/xiaohongshu")
async def get_xiaohongshu_url(
    keyword: str = Query(..., description="搜索关键词")
):
    """
    获取小红书搜索链接
    
    返回小红书搜索页面 URL，供前端跳转使用
    """
    url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}"
    return {
        "success": True,
        "data": {
            "url": url,
            "keyword": keyword
        }
    }


@router.get("/image")
async def search_destination_image(
    destination: str = Query(..., description="目的地名称")
):
    """
    搜索目的地图片
    
    返回目的地相关的风景图片URL
    """
    try:
        image_url = await search_service.search_destination_image(destination)
        return {
            "success": True,
            "data": {
                "image_url": image_url,
                "destination": destination
            }
        }
    except Exception as e:
        return {
            "success": False,
            "data": {
                "image_url": None,
                "destination": destination
            },
            "error": str(e)
        }
