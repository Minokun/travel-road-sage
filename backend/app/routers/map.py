"""
地图服务 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from app.models import SearchRequest, WeatherRequest, RouteRequest, TransportMode
from app.services.amap_mcp import amap_client

router = APIRouter(prefix="/map", tags=["地图服务"])


@router.get("/search")
async def search_poi(
    keyword: str = Query(..., description="搜索关键词"),
    city: Optional[str] = Query(None, description="城市"),
    max_results: int = Query(10, ge=1, le=50, description="最大结果数")
):
    """
    POI 关键词搜索
    
    搜索景点、餐厅、酒店等兴趣点
    """
    try:
        results = await amap_client.text_search(keyword, city)
        return {
            "success": True,
            "data": results[:max_results]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/around")
async def search_around(
    keyword: str = Query(..., description="搜索关键词"),
    location: str = Query(..., description="中心点坐标 lng,lat"),
    radius: int = Query(3000, ge=100, le=50000, description="搜索半径(米)")
):
    """
    周边搜索
    
    搜索指定位置周边的 POI
    """
    try:
        results = await amap_client.around_search(keyword, location, radius)
        return {
            "success": True,
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/poi/{poi_id}")
async def get_poi_detail(poi_id: str):
    """
    获取 POI 详情
    """
    try:
        result = await amap_client.search_detail(poi_id)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/geocode")
async def geocode(
    address: str = Query(..., description="地址"),
    city: Optional[str] = Query(None, description="城市")
):
    """
    地理编码
    
    将地址转换为经纬度坐标
    """
    try:
        result = await amap_client.geocode(address, city)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regeocode")
async def regeocode(
    location: str = Query(..., description="坐标 lng,lat")
):
    """
    逆地理编码
    
    将经纬度坐标转换为地址
    """
    try:
        result = await amap_client.regeocode(location)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weather")
async def get_weather(
    city: str = Query(..., description="城市名称或 adcode")
):
    """
    查询天气
    
    获取城市天气预报
    """
    try:
        result = await amap_client.get_weather(city)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route")
async def calculate_route(request: RouteRequest):
    """
    路径规划
    
    支持步行、驾车、公交、骑行多种方式
    """
    try:
        if request.mode == TransportMode.WALKING:
            result = await amap_client.route_walking(
                request.origin, request.destination
            )
        elif request.mode == TransportMode.DRIVING:
            result = await amap_client.route_driving(
                request.origin, request.destination
            )
        elif request.mode == TransportMode.BICYCLING:
            result = await amap_client.route_bicycling(
                request.origin, request.destination
            )
        else:  # TRANSIT
            if not request.city:
                raise HTTPException(
                    status_code=400, 
                    detail="公交规划需要指定城市"
                )
            result = await amap_client.route_transit(
                request.origin, request.destination, request.city
            )
        
        return {
            "success": True,
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/distance")
async def measure_distance(
    origin: str = Query(..., description="起点坐标 lng,lat"),
    destination: str = Query(..., description="终点坐标 lng,lat")
):
    """
    距离测量
    
    测量两点之间的距离
    """
    try:
        result = await amap_client.distance(origin, destination)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
