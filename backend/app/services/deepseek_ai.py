"""
DeepSeek AI 对话服务
使用 OpenAI 兼容接口
"""
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI
from app.config import settings
from app.models import ChatMessage


# 系统提示词
SYSTEM_PROMPT = """你是「旅行路算子」，一个专业的智能旅行规划助手。你的核心能力是：

1. **懂攻略**：能够根据用户需求，推荐合适的景点、美食、住宿
2. **懂路线**：基于真实地理位置，规划最优路线，避免"时空跳跃"
3. **懂天气**：根据天气预报，动态调整户外行程
4. **懂预算**：估算行程花费，帮助用户控制预算
5. **懂应变**：提供备选方案，应对突发情况

## 工作流程

当用户提出旅行需求时，你需要：
1. 解析用户意图：目的地、天数、偏好、预算等
2. 搜索相关信息：景点、美食、住宿、天气
3. 规划合理路线：考虑地理位置、交通时间
4. 生成结构化行程：包含每日安排、路线、预估花费

## 输出格式

当生成行程规划时，请在回复末尾附上 JSON 格式的结构化数据：

```json
{
  "type": "trip_plan",
  "title": "行程标题",
  "destination": "目的地城市",
  "days": 天数,
  "daily_plans": [
    {
      "day": 1,
      "pois": [
        {"name": "景点名称", "type": "景点/美食/住宿", "duration": "建议游玩时长", "cost": 预估花费}
      ],
      "tips": ["当日提示"]
    }
  ],
  "estimated_cost": 总预估花费
}
```

## 注意事项

- 保持友好、专业的语气
- 给出具体、可执行的建议
- 考虑季节、天气等因素
- 路线安排要合理，避免来回奔波
- 如果信息不足，主动询问用户
"""


class DeepSeekAI:
    """DeepSeek AI 服务"""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.model = settings.DEEPSEEK_MODEL
    
    async def chat(
        self, 
        message: str, 
        history: List[ChatMessage] = None,
        tools_context: str = None
    ) -> str:
        """
        对话接口
        
        Args:
            message: 用户消息
            history: 历史对话
            tools_context: 工具调用结果上下文
            
        Returns:
            AI 回复
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # 添加历史对话
        if history:
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})
        
        # 添加工具上下文
        if tools_context:
            messages.append({
                "role": "system", 
                "content": f"以下是相关信息供参考：\n{tools_context}"
            })
        
        # 添加当前消息
        messages.append({"role": "user", "content": message})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"DeepSeek API 调用失败: {e}")
    
    async def chat_stream(
        self, 
        message: str, 
        history: List[ChatMessage] = None,
        tools_context: str = None
    ) -> AsyncGenerator[str, None]:
        """
        流式对话接口
        
        Args:
            message: 用户消息
            history: 历史对话
            tools_context: 工具调用结果上下文
            
        Yields:
            AI 回复片段
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        if history:
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})
        
        if tools_context:
            messages.append({
                "role": "system", 
                "content": f"以下是相关信息供参考：\n{tools_context}"
            })
        
        messages.append({"role": "user", "content": message})
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n\n[错误: {e}]"
    
    def parse_plan_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        从 AI 回复中解析行程规划 JSON
        
        Args:
            response: AI 回复文本
            
        Returns:
            解析出的行程规划，如果没有则返回 None
        """
        try:
            # 查找 JSON 代码块
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                plan = json.loads(json_str)
                if plan.get("type") == "trip_plan":
                    return plan
            return None
        except Exception:
            return None


# 全局 AI 服务实例
deepseek_ai = DeepSeekAI()
