"""
管理员 API 路由 - 用于测试
"""
import logging
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

from app.services.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["管理"])

class UpdateTierRequest(BaseModel):
    user_id: str
    tier: str  # regular, member, super

@router.get("/users")
async def list_users():
    """列出所有用户"""
    try:
        users = db.conn.execute("""
            SELECT 
                id, 
                openid, 
                nickname, 
                membership_tier,
                created_at
            FROM users 
            ORDER BY created_at DESC 
            LIMIT 50
        """).fetchall()
        
        result = []
        for user in users:
            result.append({
                "user_id": user[0],
                "openid": user[1],
                "nickname": user[2] or "未设置",
                "membership_tier": user[3],
                "tier_name": {
                    'regular': '普通用户',
                    'member': '普通会员',
                    'super': '超级会员'
                }.get(user[3], user[3]),
                "created_at": user[4]
            })
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"查询用户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update-tier")
async def update_user_tier(request: UpdateTierRequest):
    """修改用户会员等级"""
    valid_tiers = ['regular', 'member', 'super']
    if request.tier not in valid_tiers:
        raise HTTPException(
            status_code=400, 
            detail=f"无效的会员等级: {request.tier}，有效值: {', '.join(valid_tiers)}"
        )
    
    try:
        # 检查用户是否存在
        user = db.conn.execute(
            "SELECT id, nickname, membership_tier FROM users WHERE id = ?",
            [request.user_id]
        ).fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail=f"未找到用户: {request.user_id}")
        
        old_tier = user[2]
        
        # 更新会员等级
        db.conn.execute(
            "UPDATE users SET membership_tier = ? WHERE id = ?",
            [request.tier, request.user_id]
        )
        
        tier_names = {
            'regular': '普通用户',
            'member': '普通会员',
            'super': '超级会员'
        }
        
        logger.info(f"✅ 会员等级更新: {user[1] or request.user_id} {tier_names[old_tier]} -> {tier_names[request.tier]}")
        
        return {
            "success": True,
            "message": "会员等级更新成功",
            "data": {
                "user_id": request.user_id,
                "nickname": user[1],
                "old_tier": old_tier,
                "old_tier_name": tier_names[old_tier],
                "new_tier": request.tier,
                "new_tier_name": tier_names[request.tier]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新会员等级失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}/stats")
async def get_user_stats(user_id: str):
    """查看用户生成统计"""
    try:
        limit_check = db.check_generation_limit(user_id)
        
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "tier_name": limit_check['tier_name'],
                "membership_tier": limit_check['membership_tier'],
                "daily_limit": limit_check['daily_limit'],
                "today_count": limit_check['today_count'],
                "remaining": limit_check['daily_limit'] - limit_check['today_count'],
                "can_generate": limit_check['can_generate']
            }
        }
    except Exception as e:
        logger.error(f"查询用户统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
