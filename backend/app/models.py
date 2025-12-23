"""
数据模型定义
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class TransportMode(str, Enum):
    """交通方式"""
    WALKING = "walking"
    DRIVING = "driving"
    TRANSIT = "transit"
    BICYCLING = "bicycling"


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="消息角色: user/assistant/system")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., description="用户消息")
    history: List[ChatMessage] = Field(default=[], description="历史对话")
    stream: bool = Field(default=False, description="是否流式返回")


class ChatResponse(BaseModel):
    """对话响应"""
    reply: str = Field(..., description="AI回复")
    plan: Optional[Dict[str, Any]] = Field(default=None, description="生成的行程规划")
    tool_calls: List[Dict[str, Any]] = Field(default=[], description="调用的工具列表")


class POI(BaseModel):
    """兴趣点"""
    id: str = Field(default="", description="POI ID")
    name: str = Field(..., description="名称")
    address: str = Field(default="", description="地址")
    location: str = Field(default="", description="经纬度坐标 lng,lat")
    type: str = Field(default="", description="类型")
    tel: str = Field(default="", description="电话")
    rating: Optional[float] = Field(default=None, description="评分")
    cost: Optional[float] = Field(default=None, description="人均消费")


class RouteSegment(BaseModel):
    """路线段"""
    origin: str = Field(..., description="起点名称")
    destination: str = Field(..., description="终点名称")
    mode: TransportMode = Field(..., description="交通方式")
    distance: int = Field(default=0, description="距离(米)")
    duration: int = Field(default=0, description="耗时(秒)")
    polyline: str = Field(default="", description="路线坐标串")


class DayPlan(BaseModel):
    """单日行程"""
    day: int = Field(..., description="第几天")
    date: Optional[str] = Field(default=None, description="日期")
    pois: List[POI] = Field(default=[], description="当日POI列表")
    routes: List[RouteSegment] = Field(default=[], description="路线列表")
    weather: Optional[Dict[str, Any]] = Field(default=None, description="天气信息")
    tips: List[str] = Field(default=[], description="当日提示")


class TripPlan(BaseModel):
    """完整行程规划"""
    id: str = Field(default="", description="行程ID")
    title: str = Field(..., description="行程标题")
    destination: str = Field(..., description="目的地城市")
    days: int = Field(..., description="天数")
    budget: Optional[float] = Field(default=None, description="预算")
    daily_plans: List[DayPlan] = Field(default=[], description="每日行程")
    total_distance: int = Field(default=0, description="总距离(米)")
    total_duration: int = Field(default=0, description="总耗时(秒)")
    estimated_cost: Optional[float] = Field(default=None, description="预估花费")
    created_at: Optional[str] = Field(default=None, description="创建时间")


class PlanRequest(BaseModel):
    """行程规划请求"""
    destination: str = Field(..., description="目的地城市")
    days: int = Field(default=2, ge=1, le=14, description="天数")
    preferences: List[str] = Field(default=[], description="偏好标签，如: 美食、自然、文化")
    description: Optional[str] = Field(default=None, description="用户具体描述和特殊需求")
    budget: Optional[float] = Field(default=None, description="预算(元)")
    budget_level: Optional[str] = Field(default=None, description="预算级别: low/medium/high")
    travel_with: Optional[str] = Field(default=None, description="出行人群: solo/couple/family/friends")
    start_date: Optional[str] = Field(default=None, description="出发日期")
    transport_mode: TransportMode = Field(default=TransportMode.TRANSIT, description="主要交通方式")


class SearchRequest(BaseModel):
    """搜索请求"""
    keyword: str = Field(..., description="搜索关键词")
    city: Optional[str] = Field(default=None, description="城市")
    max_results: int = Field(default=10, ge=1, le=50, description="最大结果数")


class WeatherRequest(BaseModel):
    """天气查询请求"""
    city: str = Field(..., description="城市名称或adcode")


class RouteRequest(BaseModel):
    """路线规划请求"""
    origin: str = Field(..., description="起点坐标 lng,lat")
    destination: str = Field(..., description="终点坐标 lng,lat")
    mode: TransportMode = Field(default=TransportMode.TRANSIT, description="交通方式")
    city: Optional[str] = Field(default=None, description="城市(公交规划需要)")


class NavigateRequest(BaseModel):
    """导航请求"""
    destination: str = Field(..., description="目的地坐标 lng,lat")
    destination_name: Optional[str] = Field(default=None, description="目的地名称")
