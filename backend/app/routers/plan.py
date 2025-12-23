"""
行程规划 API 路由
"""
import logging
import traceback
from fastapi import APIRouter, HTTPException, Header
from typing import Optional

from app.models import PlanRequest, NavigateRequest
from app.services.planner import trip_planner
from app.services.database import db
from app.routers.user import get_current_user_id

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plan", tags=["行程规划"])


@router.post("")
async def create_plan(request: PlanRequest, authorization: str = Header(None)):
    """
    创建行程规划（未来规划建议模式）
    
    根据用户需求生成完整的旅行行程，包括：
    - 每日景点安排
    - 路线规划
    - 预估花费
    - 天气提示
    
    需要登录，受会员等级限制：
    - 普通用户：每天2次
    - 普通会员：每天5次
    - 超级会员：每天10次
    """
    # 检查登录
    user_id = None
    try:
        if authorization:
            user_id = get_current_user_id(authorization)
    except HTTPException:
        pass
    
    # 如果已登录，检查生成次数限制
    if user_id:
        limit_check = db.check_generation_limit(user_id)
        if not limit_check['can_generate']:
            logger.warning(f"⚠️ 用户 {user_id} 今日生成次数已达上限")
            raise HTTPException(
                status_code=429,
                detail={
                    "message": f"今日生成次数已用完！",
                    "tier_name": limit_check['tier_name'],
                    "daily_limit": limit_check['daily_limit'],
                    "today_count": limit_check['today_count'],
                    "upgrade_tip": "升级会员或分享给好友让好友生成" if limit_check['membership_tier'] == 'regular' else "已达今日上限，明天再来吧"
                }
            )
        
        logger.info(f"📊 用户 {user_id} 今日生成次数: {limit_check['today_count']}/{limit_check['daily_limit']}")
    
    logger.info(f"📥 收到攻略生成请求: {request.destination} {request.days}天")
    logger.info(f"   偏好: {request.preferences}, 描述: {request.description[:50] if request.description else '无'}...")
    
    try:
        logger.info("🚀 开始生成攻略...")
        result = await trip_planner.create_plan(request, mode="planning")
        
        # 如果已登录，记录生成次数
        if user_id:
            db.record_generation(user_id, request.destination)
            logger.info(f"✅ 已记录生成次数")
        
        logger.info(f"✅ 攻略生成成功: {request.destination}")
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"❌ 攻略生成失败: {request.destination}")
        logger.error(f"   错误信息: {str(e)}")
        logger.error(f"   堆栈跟踪:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/limit")
async def check_generation_limit(authorization: str = Header(None)):
    """
    查询用户今日生成次数限制
    
    返回：
    - 会员等级
    - 每日限制
    - 今日已用次数
    - 剩余次数
    """
    user_id = get_current_user_id(authorization)
    limit_check = db.check_generation_limit(user_id)
    
    return {
        "success": True,
        "data": limit_check
    }


@router.post("/travelogue")
async def create_travelogue(request: PlanRequest):
    """
    创建游记攻略（已发生的旅行分享模式）
    
    生成模拟真实旅行经历的游记风格攻略，用于发现页面展示
    """
    try:
        result = await trip_planner.create_plan(request, mode="travelogue")
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/navigate")
async def get_navigate_url(request: NavigateRequest):
    """
    获取导航链接
    
    生成高德地图导航唤端链接
    """
    try:
        url = trip_planner.get_navigation_url(
            request.destination, 
            request.destination_name or ""
        )
        return {
            "success": True,
            "data": {
                "url": url,
                "destination": request.destination,
                "destination_name": request.destination_name
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
