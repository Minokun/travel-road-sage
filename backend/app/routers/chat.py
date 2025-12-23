"""
对话 API 路由
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json

from app.models import ChatRequest, ChatResponse
from app.services.deepseek_ai import deepseek_ai
from app.services.planner import trip_planner

router = APIRouter(prefix="/chat", tags=["对话"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    智能对话接口
    
    支持自然语言交互，可以：
    - 询问旅行建议
    - 生成行程规划
    - 查询景点信息
    """
    try:
        # 调用 AI 对话
        reply = await deepseek_ai.chat(
            message=request.message,
            history=request.history
        )
        
        # 尝试解析行程规划
        plan = deepseek_ai.parse_plan_from_response(reply)
        
        return ChatResponse(
            reply=reply,
            plan=plan,
            tool_calls=[]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    流式对话接口
    
    返回 Server-Sent Events 格式的流式响应
    """
    async def generate():
        try:
            async for chunk in deepseek_ai.chat_stream(
                message=request.message,
                history=request.history
            ):
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
