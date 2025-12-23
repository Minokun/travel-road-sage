"""
用户管理 API 路由
包含微信登录、用户信息管理
"""
import httpx
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel

from app.config import settings
from app.services.database import db


router = APIRouter(prefix="/user", tags=["用户管理"])


# ==================== 请求/响应模型 ====================

class WxLoginRequest(BaseModel):
    """微信登录请求"""
    code: str  # wx.login 获取的 code
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    gender: Optional[int] = 0


class UserUpdateRequest(BaseModel):
    """用户信息更新请求"""
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    gender: Optional[int] = None
    city: Optional[str] = None
    province: Optional[str] = None


# ==================== 工具函数 ====================

async def get_wx_session(code: str) -> dict:
    """
    通过 code 获取微信 session
    调用微信 code2session 接口
    """
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.WX_APPID,
        "secret": settings.WX_SECRET,
        "js_code": code,
        "grant_type": "authorization_code"
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        
        if "errcode" in data and data["errcode"] != 0:
            raise HTTPException(
                status_code=400, 
                detail=f"微信登录失败: {data.get('errmsg', '未知错误')}"
            )
        
        return data


def get_current_user_id(authorization: str = Header(None)) -> str:
    """
    从请求头获取当前用户ID
    简化版：直接使用 user_id 作为 token
    生产环境应使用 JWT
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    # 简化处理：Bearer {user_id}
    if authorization.startswith("Bearer "):
        user_id = authorization[7:]
        user = db.get_user_by_id(user_id)
        if user:
            return user_id
    
    raise HTTPException(status_code=401, detail="无效的登录凭证")


# ==================== API 路由 ====================

@router.post("/login")
async def wx_login(request: WxLoginRequest):
    """
    微信登录
    
    1. 通过 code 获取 openid
    2. 查找或创建用户
    3. 返回用户信息和 token
    """
    try:
        # 获取微信 session
        wx_data = await get_wx_session(request.code)
        openid = wx_data.get("openid")
        
        if not openid:
            raise HTTPException(status_code=400, detail="获取用户信息失败")
        
        # 获取或创建用户
        user = db.get_or_create_user(
            openid=openid,
            nickname=request.nickname,
            avatar_url=request.avatar_url,
            gender=request.gender
        )
        
        # 简化版 token（生产环境应使用 JWT）
        token = user["id"]
        
        return {
            "success": True,
            "data": {
                "token": token,
                "user": {
                    "id": user["id"],
                    "nickname": user["nickname"],
                    "avatar_url": user["avatar_url"],
                    "gender": user["gender"]
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login/dev")
async def dev_login(nickname: str = "全世界", avatar_url: str = None):
    """
    开发环境登录（跳过微信验证）
    仅用于开发测试
    """
    # 使用固定的测试 openid
    test_openid = "dev_test_openid_12345"
    
    # 使用可靠的默认头像（UI Avatars服务）
    default_avatar = f"https://ui-avatars.com/api/?name={nickname}&background=6366f1&color=fff&size=128"
    
    user = db.get_or_create_user(
        openid=test_openid,
        nickname=nickname,
        avatar_url=avatar_url or default_avatar
    )
    
    # 如果传入了昵称，更新用户昵称和头像
    if nickname and user["nickname"] != nickname:
        user = db.update_user(user["id"], nickname=nickname, avatar_url=default_avatar)
    
    return {
        "success": True,
        "data": {
            "token": user["id"],
            "user": {
                "id": user["id"],
                "nickname": user["nickname"],
                "avatar_url": user["avatar_url"],
                "gender": user["gender"]
            }
        }
    }


@router.get("/profile")
async def get_profile(authorization: str = Header(None)):
    """获取当前用户信息"""
    user_id = get_current_user_id(authorization)
    user = db.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 获取用户攻略数量
    plans = db.get_user_plans(user_id, limit=1000)
    
    # 获取会员等级和今日生成次数
    limit_check = db.check_generation_limit(user_id)
    
    return {
        "success": True,
        "data": {
            "id": user["id"],
            "nickname": user["nickname"],
            "avatar_url": user["avatar_url"],
            "gender": user["gender"],
            "city": user["city"],
            "province": user["province"],
            "plan_count": len(plans),
            "created_at": user["created_at"].isoformat() if user["created_at"] else None,
            "membership_tier": user.get("membership_tier", "regular"),
            "tier_name": limit_check["tier_name"],
            "daily_limit": limit_check["daily_limit"],
            "today_count": limit_check["today_count"],
            "remaining_count": limit_check["remaining"]
        }
    }


@router.put("/profile")
async def update_profile(
    request: UserUpdateRequest,
    authorization: str = Header(None)
):
    """更新用户信息"""
    user_id = get_current_user_id(authorization)
    
    user = db.update_user(
        user_id,
        nickname=request.nickname,
        avatar_url=request.avatar_url,
        gender=request.gender,
        city=request.city,
        province=request.province
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {
        "success": True,
        "data": {
            "id": user["id"],
            "nickname": user["nickname"],
            "avatar_url": user["avatar_url"],
            "gender": user["gender"]
        }
    }
