"""
攻略管理 API 路由
包含攻略的增删改查和分享功能
"""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel

from app.services.database import db
from app.routers.user import get_current_user_id


router = APIRouter(prefix="/plans", tags=["攻略管理"])


# ==================== 请求/响应模型 ====================

class CreatePlanRequest(BaseModel):
    """创建攻略请求"""
    destination: str
    days: int
    content: str
    preferences: Optional[List[str]] = []
    description: Optional[str] = None
    plan_data: Optional[dict] = None
    is_public: Optional[bool] = False
    cover_url: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class UpdatePlanRequest(BaseModel):
    """更新攻略请求"""
    destination: Optional[str] = None
    days: Optional[int] = None
    content: Optional[str] = None
    preferences: Optional[List[str]] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


# ==================== API 路由 ====================

@router.post("")
async def create_plan(
    request: CreatePlanRequest,
    authorization: str = Header(None)
):
    """
    创建攻略
    需要登录
    """
    user_id = get_current_user_id(authorization)
    
    try:
        plan = db.create_plan(
            user_id=user_id,
            destination=request.destination,
            days=request.days,
            content=request.content,
            preferences=request.preferences,
            description=request.description,
            plan_data=request.plan_data,
            is_public=request.is_public,
            cover_url=request.cover_url,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        return {
            "success": True,
            "data": plan
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_my_plans(
    authorization: str = Header(None),
    limit: int = 50,
    offset: int = 0
):
    """
    获取我的攻略列表
    需要登录
    """
    user_id = get_current_user_id(authorization)
    
    plans = db.get_user_plans(user_id, limit=limit, offset=offset)
    
    return {
        "success": True,
        "data": {
            "plans": plans,
            "total": len(plans)
        }
    }


@router.get("/public")
async def get_public_plans(
    category: str = None,
    limit: int = 20,
    offset: int = 0
):
    """
    获取公开攻略列表（发现页面）
    无需登录
    """
    plans = db.get_public_plans(category=category, limit=limit, offset=offset)
    
    # 为每个攻略添加作者信息
    result = []
    for plan in plans:
        author = db.get_user_by_id(plan["user_id"])
        result.append({
            "id": plan["id"],
            "destination": plan["destination"],
            "days": plan["days"],
            "preferences": plan["preferences"],
            "content": plan["content"][:200] + "..." if len(plan["content"]) > 200 else plan["content"],
            "view_count": plan["view_count"],
            "share_code": plan["share_code"],
            "cover_url": plan.get("cover_url"),
            "plan_data": plan.get("plan_data"),
            "created_at": plan["created_at"].isoformat() if plan["created_at"] else None,
            "author": {
                "nickname": author["nickname"] if author else "匿名用户",
                "avatar_url": author["avatar_url"] if author else None
            }
        })
    
    return {
        "success": True,
        "data": {
            "plans": result,
            "total": db.get_public_plans_count()
        }
    }


@router.get("/share/{share_code}")
async def get_shared_plan(share_code: str):
    """
    通过分享码获取攻略
    无需登录
    """
    plan = db.get_plan_by_share_code(share_code)
    
    if not plan:
        raise HTTPException(status_code=404, detail="攻略不存在或未公开")
    
    # 获取作者信息
    author = db.get_user_by_id(plan["user_id"])
    
    return {
        "success": True,
        "data": {
            **plan,
            "author": {
                "nickname": author["nickname"] if author else "匿名用户",
                "avatar_url": author["avatar_url"] if author else None
            }
        }
    }


@router.get("/{plan_id}")
async def get_plan(
    plan_id: str,
    authorization: str = Header(None)
):
    """
    获取攻略详情
    需要登录（只能查看自己的）
    """
    user_id = get_current_user_id(authorization)
    
    plan = db.get_plan_by_id(plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail="攻略不存在")
    
    if plan["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权访问此攻略")
    
    return {
        "success": True,
        "data": plan
    }


@router.put("/{plan_id}")
async def update_plan(
    plan_id: str,
    request: UpdatePlanRequest,
    authorization: str = Header(None)
):
    """
    更新攻略
    需要登录（只能更新自己的）
    """
    user_id = get_current_user_id(authorization)
    
    # 检查攻略是否存在且属于当前用户
    existing = db.get_plan_by_id(plan_id)
    if not existing:
        raise HTTPException(status_code=404, detail="攻略不存在")
    if existing["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权修改此攻略")
    
    plan = db.update_plan(
        plan_id=plan_id,
        user_id=user_id,
        destination=request.destination,
        days=request.days,
        content=request.content,
        preferences=request.preferences,
        description=request.description,
        is_public=request.is_public
    )
    
    return {
        "success": True,
        "data": plan
    }


@router.delete("/{plan_id}")
async def delete_plan(
    plan_id: str,
    authorization: str = Header(None)
):
    """
    删除攻略
    需要登录（只能删除自己的）
    """
    user_id = get_current_user_id(authorization)
    
    success = db.delete_plan(plan_id, user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="攻略不存在或无权删除")
    
    return {
        "success": True,
        "message": "删除成功"
    }


@router.post("/{plan_id}/share")
async def toggle_share(
    plan_id: str,
    is_public: bool = True,
    authorization: str = Header(None)
):
    """
    设置攻略公开/私密状态
    公开后会生成分享码
    """
    user_id = get_current_user_id(authorization)
    
    # 检查攻略是否存在且属于当前用户
    existing = db.get_plan_by_id(plan_id)
    if not existing:
        raise HTTPException(status_code=404, detail="攻略不存在")
    if existing["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权操作此攻略")
    
    plan = db.update_plan(
        plan_id=plan_id,
        user_id=user_id,
        is_public=is_public
    )
    
    return {
        "success": True,
        "data": {
            "is_public": plan["is_public"],
            "share_code": plan["share_code"],
            "share_url": f"/pages/plan/detail?code={plan['share_code']}" if plan["share_code"] else None
        }
    }


# ==================== 收藏相关 ====================

@router.post("/{plan_id}/favorite")
async def toggle_favorite(
    plan_id: str,
    authorization: str = Header(None)
):
    """
    收藏/取消收藏攻略
    需要登录
    """
    user_id = get_current_user_id(authorization)
    
    # 检查攻略是否存在且公开
    plan = db.get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="攻略不存在")
    if not plan["is_public"] and plan["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权访问此攻略")
    
    # 切换收藏状态
    is_favorited = db.is_favorited(user_id, plan_id)
    if is_favorited:
        db.remove_favorite(user_id, plan_id)
        return {"success": True, "data": {"is_favorited": False}}
    else:
        db.add_favorite(user_id, plan_id)
        return {"success": True, "data": {"is_favorited": True}}


@router.get("/user/favorites")
async def get_my_favorites(
    authorization: str = Header(None),
    limit: int = 50,
    offset: int = 0
):
    """
    获取我的收藏列表
    需要登录
    """
    user_id = get_current_user_id(authorization)
    
    favorites = db.get_user_favorites(user_id, limit=limit, offset=offset)
    
    # 为每个攻略添加作者信息
    result = []
    for plan in favorites:
        author = db.get_user_by_id(plan["user_id"])
        result.append({
            **plan,
            "author": {
                "nickname": author["nickname"] if author else "匿名用户",
                "avatar_url": author["avatar_url"] if author else None
            }
        })
    
    return {
        "success": True,
        "data": {
            "plans": result,
            "total": db.get_user_favorites_count(user_id)
        }
    }


# ==================== 点赞相关 ====================

@router.post("/{plan_id}/like")
async def toggle_like(
    plan_id: str,
    authorization: str = Header(None)
):
    """
    点赞/取消点赞攻略
    需要登录
    """
    user_id = get_current_user_id(authorization)
    
    # 检查攻略是否存在且公开
    plan = db.get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="攻略不存在")
    if not plan["is_public"] and plan["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权访问此攻略")
    
    # 切换点赞状态
    is_liked = db.is_liked(user_id, plan_id)
    if is_liked:
        db.remove_like(user_id, plan_id)
        like_count = db.get_plan_like_count(plan_id)
        return {"success": True, "data": {"is_liked": False, "like_count": like_count}}
    else:
        db.add_like(user_id, plan_id)
        like_count = db.get_plan_like_count(plan_id)
        return {"success": True, "data": {"is_liked": True, "like_count": like_count}}


@router.get("/{plan_id}/interaction")
async def get_plan_interaction(
    plan_id: str,
    authorization: str = Header(None)
):
    """
    获取攻略的互动状态（是否已收藏、是否已点赞）
    可选登录，未登录返回默认状态
    """
    user_id = None
    if authorization:
        try:
            user_id = get_current_user_id(authorization)
        except:
            pass
    
    plan = db.get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="攻略不存在")
    
    is_favorited = db.is_favorited(user_id, plan_id) if user_id else False
    is_liked = db.is_liked(user_id, plan_id) if user_id else False
    like_count = db.get_plan_like_count(plan_id)
    favorite_count = db.get_plan_favorite_count(plan_id)
    
    return {
        "success": True,
        "data": {
            "is_favorited": is_favorited,
            "is_liked": is_liked,
            "like_count": like_count,
            "favorite_count": favorite_count
        }
    }
