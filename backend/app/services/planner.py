"""
行程规划服务
整合 AI、地图、搜索能力，生成完整行程
"""
import json
import uuid
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.models import (
    PlanRequest, TripPlan, DayPlan, POI, RouteSegment, TransportMode
)
from app.services.amap_mcp import amap_client
from app.services.deepseek_ai import deepseek_ai
from app.services.search import search_service

# 配置日志
logger = logging.getLogger(__name__)


class TripPlanner:
    """行程规划器"""
    
    async def create_plan(self, request: PlanRequest, mode: str = "planning") -> Dict[str, Any]:
        """
        创建行程规划
        
        优化后的流程：
        1. AI提取旅行意图 - 从表单和描述中提取关键信息
        2. 智能查询高德 - 基于提取的信息精准查询
        3. AI生成攻略 - 结合查询结果生成精准攻略
        
        Args:
            request: 规划请求
            mode: 模式，"planning"=未来规划建议，"travelogue"=已发生的游记分享
            
        Returns:
            包含 AI 回复和结构化行程的结果
        """
        total_start = time.time()
        logger.info(f"🎯 开始规划: {request.destination} {request.days}天 (模式: {mode})")
        
        # 1. 第一步：AI提取旅行意图
        t0 = time.time()
        logger.info("📝 步骤1: 提取旅行意图...")
        travel_intent = await self._extract_travel_intent(request)
        logger.info(f"   ✓ 提取完成 ({time.time() - t0:.2f}s)")
        logger.debug(f"   意图: {json.dumps(travel_intent, ensure_ascii=False)}")
        
        # 2. 第二步：基于意图智能查询高德
        t1 = time.time()
        logger.info("🔍 步骤2: 查询高德地图...")
        context = await self._gather_context_with_intent(request, travel_intent)
        logger.info(f"   ✓ 查询完成 ({time.time() - t1:.2f}s)")
        logger.info(f"   找到 {len(context.get('attractions', []))} 个景点")
        
        # 3. 构建 AI 提示（包含意图和上下文）
        logger.info("📋 步骤3: 构建AI提示...")
        prompt = self._build_prompt_with_intent(request, context, travel_intent, mode)
        
        # 4. 调用 AI 生成行程
        t2 = time.time()
        logger.info("🤖 步骤4: AI生成攻略内容...")
        ai_response = await deepseek_ai.chat(prompt, tools_context=context["summary"])
        logger.info(f"   ✓ AI生成完成 ({time.time() - t2:.2f}s)")
        logger.info(f"   内容长度: {len(ai_response)} 字符")
        
        # 4. 解析行程规划
        logger.info("📊 步骤5: 解析行程规划...")
        plan = deepseek_ai.parse_plan_from_response(ai_response)
        
        # 5. 如果有规划，补充详细信息
        t3 = time.time()
        if plan:
            logger.info("📍 步骤6: 补充路线详情...")
            plan = await self._enrich_plan(plan, request)
            logger.info(f"   ✓ 补充完成 ({time.time() - t3:.2f}s)")
        
        # 6. 生成路径规划静态地图
        t4 = time.time()
        route_map_url = ""
        route_map_base64 = ""
        if context.get("attractions"):
            try:
                logger.info("🗺️ 步骤7: 生成路线地图...")
                # 取前5个景点生成路线图
                pois = context["attractions"][:5]
                map_url = await amap_client.generate_route_map(
                    pois, 
                    request.transport_mode.value if request.transport_mode else "walking"
                )
                # 下载图片并转换为base64
                if map_url:
                    route_map_base64, route_map_url = await amap_client.download_static_map_as_base64(map_url)
                    logger.info(f"   ✓ 地图生成完成 ({time.time() - t4:.2f}s)")
            except Exception as e:
                logger.error(f"   ✗ 生成路线图失败: {e}")
        
        # 7. 搜索目的地封面图（Unsplash + 高德地图 + DDGS）
        t5 = time.time()
        cover_url = None
        try:
            logger.info("🖼️ 步骤8: 搜索目的地封面图...")
            # 准备地图参数（如果有POI数据）
            location = None
            markers = []
            if plan and isinstance(plan, dict) and plan.get("days") and isinstance(plan["days"], list):
                # 获取第一天的第一个景点作为中心点
                first_day = plan["days"][0] if len(plan["days"]) > 0 else None
                if first_day and isinstance(first_day, dict) and first_day.get("pois") and isinstance(first_day["pois"], list):
                    first_poi = first_day["pois"][0] if len(first_day["pois"]) > 0 else None
                    if first_poi and isinstance(first_poi, dict) and first_poi.get("location"):
                        loc = first_poi["location"]
                        location = f"{loc.get('lng', '')},{loc.get('lat', '')}"
                        # 收集所有景点作为标记点
                        for day in plan["days"]:
                            if isinstance(day, dict):
                                pois = day.get("pois", [])
                                if isinstance(pois, list):
                                    for poi in pois[:3]:  # 每天最多3个标记
                                        if isinstance(poi, dict) and poi.get("location"):
                                            markers.append(poi["location"])
            
            cover_url = await search_service.search_destination_image(
                request.destination,
                location=location,
                markers=markers
            )
            if cover_url:
                logger.info(f"   ✓ 封面图获取成功 ({time.time() - t5:.2f}s)")
            else:
                logger.info(f"   ⚠️ 未找到合适的封面图 ({time.time() - t5:.2f}s)")
        except Exception as e:
            logger.error(f"   ✗ 搜索封面图失败: {e}")
        
        total_time = time.time() - total_start
        logger.info(f"🎉 规划完成! 总耗时: {total_time:.2f}s")
        
        return {
            "reply": ai_response,
            "plan": plan,
            "route_map_url": route_map_url,  # 原始URL，用于存储
            "route_map_base64": route_map_base64,  # base64数据，用于前端显示
            "cover_url": cover_url,  # DDGS搜索的目的地封面图
            "context": {
                "weather": context.get("weather"),
                "search_results": context.get("guides"),
                "travel_intent": travel_intent
            }
        }
    
    async def _extract_travel_intent(self, request: PlanRequest) -> Dict[str, Any]:
        """
        第一步：使用AI从用户输入中提取旅行意图
        
        提取内容包括：
        - 具体想去的景点/地点
        - 特殊需求（如带小孩、老人、拍照等）
        - 美食偏好
        - 预算敏感度
        - 行程节奏偏好
        """
        # 构建提取意图的prompt
        extract_prompt = f"""请分析以下旅行需求，提取关键信息并返回JSON格式：

**用户输入：**
- 目的地：{request.destination}
- 天数：{request.days}天
- 偏好标签：{', '.join(request.preferences) if request.preferences else '无'}
- 详细描述：{request.description or '无'}
- 出行方式：{request.transport_mode.value if request.transport_mode else '未指定'}
- 预算级别：{request.budget_level or '未指定'}
- 出行人群：{request.travel_with or '未指定'}
- 出发日期：{request.start_date or '未指定'}

**请提取以下信息，返回JSON格式：**
```json
{{
    "specific_places": ["用户明确提到想去的具体地点/景点"],
    "must_eat": ["用户明确提到想吃的美食/餐厅"],
    "travel_style": "休闲慢游/紧凑高效/深度体验/打卡拍照",
    "special_needs": ["特殊需求，如带小孩、老人、轮椅、宠物等"],
    "budget_sensitivity": "高/中/低",
    "photo_spots_needed": true/false,
    "local_experience": true/false,
    "avoid_crowds": true/false,
    "food_priority": "高/中/低",
    "suggested_areas": ["建议重点游览的区域"],
    "search_keywords": ["用于搜索景点的关键词列表"]
}}
```

只返回JSON，不要其他内容。"""

        try:
            response = await deepseek_ai.chat(extract_prompt)
            # 直接解析JSON（不使用parse_plan_from_response，因为那个方法只解析trip_plan类型）
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                intent = json.loads(json_match.group(1))
                return intent
            # 尝试直接解析整个响应
            intent = json.loads(response)
            return intent
        except Exception as e:
            print(f"提取旅行意图失败: {e}")
        
        # 返回默认意图
        return {
            "specific_places": [],
            "must_eat": [],
            "travel_style": "综合体验",
            "special_needs": [],
            "budget_sensitivity": "中",
            "photo_spots_needed": True,
            "local_experience": True,
            "avoid_crowds": False,
            "food_priority": "中",
            "suggested_areas": [request.destination],
            "search_keywords": [f"{request.destination}必去景点", f"{request.destination}网红打卡"]
        }
    
    async def _gather_context_with_intent(self, request: PlanRequest, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        第二步：基于提取的意图智能查询高德
        
        根据意图中的关键词和偏好进行精准查询
        """
        context = {}
        summary_parts = []
        
        # 1. 查询天气（根据出发日期）
        try:
            weather = await amap_client.get_weather(request.destination)
            context["weather"] = weather
            summary_parts.append(f"天气信息：{json.dumps(weather, ensure_ascii=False)}")
        except Exception as e:
            print(f"获取天气失败: {e}")
        
        # 2. 获取城市中心坐标（用于后续周边搜索）
        city_location = None
        try:
            geo_result = await amap_client.geocode(request.destination)
            if geo_result and geo_result.get("location"):
                city_location = geo_result["location"]
        except Exception as e:
            print(f"获取城市坐标失败: {e}")
        
        # 3. 搜索用户明确提到的地点
        specific_attractions = []
        for place in intent.get("specific_places", []):
            try:
                results = await amap_client.text_search(
                    f"{request.destination} {place}",
                    request.destination
                )
                if results:
                    specific_attractions.extend(results[:2])
            except:
                pass
        
        # 4. 根据搜索关键词查询景点
        search_keywords = intent.get("search_keywords", [f"{request.destination} 景点"])
        general_attractions = []
        for keyword in search_keywords[:3]:  # 最多3个关键词
            try:
                results = await amap_client.text_search(keyword, request.destination)
                if results:
                    general_attractions.extend(results[:5])
            except:
                pass
        
        # 合并去重景点
        all_attractions = specific_attractions + general_attractions
        seen_names = set()
        unique_attractions = []
        for attr in all_attractions:
            if attr['name'] not in seen_names:
                seen_names.add(attr['name'])
                unique_attractions.append(attr)
        
        context["attractions"] = unique_attractions[:15]
        if unique_attractions:
            summary_parts.append(f"热门景点：{', '.join([p['name'] for p in unique_attractions[:8]])}")
        
        # 5. 搜索美食（根据意图中的美食偏好）
        food_priority = intent.get("food_priority", "中")
        must_eat = intent.get("must_eat", [])
        
        food_list = []
        # 先搜索用户明确想吃的
        for food_name in must_eat:
            try:
                results = await amap_client.text_search(
                    f"{request.destination} {food_name}",
                    request.destination
                )
                if results:
                    food_list.extend(results[:2])
            except:
                pass
        
        # 再搜索当地特色美食
        if city_location and food_priority in ["高", "中"]:
            try:
                local_food = await amap_client.around_search(
                    keywords="特色菜|本地菜|老字号",
                    location=city_location,
                    radius=5000
                )
                food_list.extend(local_food[:10])
            except:
                pass
        
        context["food"] = food_list[:15]
        if food_list:
            food_names = [f"{p['name']}({p.get('rating', '暂无')}分)" for p in food_list[:5] if p.get('name')]
            summary_parts.append(f"美食推荐：{', '.join(food_names)}")
        
        # 6. 搜索住宿（根据建议区域）
        suggested_areas = intent.get("suggested_areas", [request.destination])
        hotels = []
        for area in suggested_areas[:2]:
            try:
                results = await amap_client.text_search(
                    f"{area} 酒店 住宿",
                    request.destination
                )
                if results:
                    hotels.extend(results[:5])
            except:
                pass
        
        context["hotels"] = hotels[:10]
        if hotels:
            summary_parts.append(f"推荐住宿：{', '.join([p['name'] for p in hotels[:3]])}")
        
        # 7. 如果需要拍照点，额外搜索
        if intent.get("photo_spots_needed"):
            try:
                photo_spots = await amap_client.text_search(
                    f"{request.destination} 拍照 打卡 网红",
                    request.destination
                )
                context["photo_spots"] = photo_spots[:5]
                if photo_spots:
                    summary_parts.append(f"拍照打卡点：{', '.join([p['name'] for p in photo_spots[:3]])}")
            except:
                pass
        
        context["summary"] = "\n".join(summary_parts)
        context["intent"] = intent
        return context
    
    def _build_prompt_with_intent(self, request: PlanRequest, context: Dict[str, Any], 
                                   intent: Dict[str, Any], mode: str = "planning") -> str:
        """
        第三步：基于意图和上下文构建精准的AI提示
        """
        prefs = "、".join(request.preferences) if request.preferences else "综合体验"
        
        # 构建意图摘要
        intent_summary = []
        if intent.get("specific_places"):
            intent_summary.append(f"用户明确想去：{', '.join(intent['specific_places'])}")
        if intent.get("must_eat"):
            intent_summary.append(f"用户想吃：{', '.join(intent['must_eat'])}")
        if intent.get("travel_style"):
            intent_summary.append(f"旅行风格：{intent['travel_style']}")
        if intent.get("special_needs"):
            intent_summary.append(f"特殊需求：{', '.join(intent['special_needs'])}")
        if intent.get("avoid_crowds"):
            intent_summary.append("用户希望避开人多的地方")
        
        intent_text = "\n".join(intent_summary) if intent_summary else "无特殊要求"
        
        # 交通方式描述
        transport_desc = {
            "walking": "步行为主",
            "driving": "自驾出行",
            "transit": "公共交通"
        }.get(request.transport_mode.value if request.transport_mode else "", "灵活安排")
        
        # 预算描述
        budget_str = ""
        if request.budget_level:
            budget_map = {"low": "穷游省钱", "medium": "舒适性价比", "high": "轻奢品质"}
            budget_str = f"\n- 💰 预算偏好：{budget_map.get(request.budget_level, request.budget_level)}"
        
        # 日期描述
        date_str = ""
        if request.start_date:
            date_str = f"\n- 📅 出发日期：{request.start_date}"
        
        # 描述
        desc_str = ""
        if request.description:
            desc_str = f"\n- 📝 详细需求：{request.description}"
        
        # 景点信息
        attractions_info = ""
        if context.get("attractions"):
            attr_names = [f"{a['name']}" for a in context['attractions'][:10]]
            attractions_info = f"\n\n**已查询到的热门景点（可参考）：**\n{', '.join(attr_names)}"
        
        # 美食信息
        food_info = ""
        if context.get("food"):
            food_names = [f"{f['name']}({f.get('rating', '暂无')}分)" for f in context['food'][:8]]
            food_info = f"\n\n**当地热门餐厅（可参考）：**\n{', '.join(food_names)}"
        
        # 住宿信息
        hotel_info = ""
        if context.get("hotels"):
            hotel_names = [h['name'] for h in context['hotels'][:5]]
            hotel_info = f"\n\n**推荐住宿区域/酒店：**\n{', '.join(hotel_names)}"
        
        # 拍照点信息
        photo_info = ""
        if context.get("photo_spots"):
            photo_names = [p['name'] for p in context['photo_spots'][:5]]
            photo_info = f"\n\n**拍照打卡点：**\n{', '.join(photo_names)}"
        
        # 天气信息
        weather_info = ""
        weather_tips = ""
        if context.get("weather"):
            weather = context["weather"]
            if weather.get("lives"):
                live = weather["lives"][0] if isinstance(weather["lives"], list) else weather["lives"]
                weather_info = f"当前天气：{live.get('weather', '未知')}，温度：{live.get('temperature', '未知')}℃，湿度：{live.get('humidity', '未知')}%，风向：{live.get('winddirection', '未知')}风"
            if weather.get("forecasts"):
                forecasts = weather["forecasts"]
                if isinstance(forecasts, list) and len(forecasts) > 0:
                    forecast_list = forecasts[0].get("casts", []) if isinstance(forecasts[0], dict) else []
                    if forecast_list:
                        forecast_strs = []
                        for f in forecast_list[:request.days]:
                            forecast_strs.append(f"{f.get('date', '')} {f.get('dayweather', '')} {f.get('nighttemp', '')}~{f.get('daytemp', '')}℃")
                        weather_tips = "未来天气预报：" + "；".join(forecast_strs)
        
        if mode == "travelogue":
            return self._build_travelogue_prompt(request, context, prefs, food_info, hotel_info)
        
        # 构建天气开头段落
        weather_section = ""
        if weather_info or weather_tips:
            weather_section = f"""
**🌤️ 天气情况与出行建议：**
{weather_info}
{weather_tips}

请在攻略开头根据以上天气信息，给出穿衣建议、防晒/防雨提醒、以及是否适合户外活动的建议。

"""
        
        # 规划模式的prompt - 专业导游角度
        prompt = f"""你是一位经验丰富、亲切专业的旅行规划师，请为游客规划 {request.destination} {request.days} 天的旅行攻略。
{weather_section}
**用户需求分析：**
{intent_text}

**基本信息：**
- 📍 目的地：{request.destination}
- 📅 天数：{request.days} 天
- 💝 偏好：{prefs}
- 🚗 出行方式：{transport_desc}{budget_str}{date_str}{desc_str}
{attractions_info}{food_info}{hotel_info}{photo_info}

**写作风格要求：**
- 以专业导游的口吻，亲切但不失专业
- 使用"您"称呼游客，给出贴心建议
- 适当使用emoji增加可读性 🎉✨🔥
- 推荐要具体实用，说明景点特色和游玩要点
- 提醒注意事项和避坑指南
- 使用标记符号：
  · 📍 地点  · 💰 费用  · ⭐ 推荐指数
  · 🔥 必去  · 💡 小贴士  · ⚠️ 注意事项
  · 📸 拍照点  · 🍜 美食  · 🏨 住宿  · 🚇 交通
- 标题用【】包裹，如【Day1 {request.destination}初印象】
- 段落清晰，阅读舒适

**交通信息要求（重要！）：**
每个景点之间必须给出详细的交通指引：
- � 地铁：具体到「X号线」，在「XX站」下车，从「X出口」出
- � 公交：具体到「X路/X路」公交车，在「XX站」上下车
- � 步行：标注大约步行时间，如「步行约10分钟」
- � 打车：标注预估费用和时间，如「打车约15分钟，费用20-30元」
- 示例格式：
  「🚇 交通：乘地铁1号线到龙翔桥站，A出口出站后步行5分钟即到」
  「� 交通：乘7路/K7路公交到断桥站下车」

**规划要求：**
1. **优先满足用户明确提到的地点和需求**
2. 路线合理，同一区域的景点安排在一起，避免来回折腾
3. 每天安排3-4个主要景点，节奏适中，留有休息时间
4. 每个景点标注：门票价格、建议游玩时长、最佳游玩时间
5. 🍜 推荐当地特色美食和餐厅，标注人均价格和招牌菜
6. 📸 标注拍照打卡点和最佳拍摄时间
7. 💰 每天末尾预估当日花费
8. ⚠️ 提醒注意事项（如提前预约、穿着建议、防晒防雨等）
9. 💡 给出实用的本地tips和省钱攻略

**时间安排：**
- 用大致时间段：「上午」「中午」「下午」「傍晚」「晚上」
- 或自然表达：「早起」「午后」「黄昏」「夜间」

**输出格式示例：**
【Day1 {request.destination}初印象】

📍 **上午 | 景点名称** ⭐⭐⭐⭐⭐
🔥 推荐理由：xxx
💰 门票：XX元 | ⏰ 建议游玩：2小时
📸 拍照点：xxx
💡 小贴士：xxx

🚇 **交通**：乘地铁X号线到XX站，X出口步行X分钟

🍜 **中午 | 午餐推荐**：餐厅名称
📍 地址：xxx
💰 人均：XX元 | 🌟 招牌菜：xxx

📍 **下午 | 景点名称** ⭐⭐⭐⭐
...

💰 **今日预估花费**：约XXX元

————————

请生成详细的行程攻略，最后附上JSON格式的结构化数据（用```json```包裹）。"""
        
        return prompt
    
    async def _gather_context(self, request: PlanRequest) -> Dict[str, Any]:
        """收集规划所需的上下文信息"""
        context = {}
        summary_parts = []
        
        # 1. 查询天气
        try:
            weather = await amap_client.get_weather(request.destination)
            context["weather"] = weather
            summary_parts.append(f"天气信息：{json.dumps(weather, ensure_ascii=False)}")
        except Exception as e:
            print(f"获取天气失败: {e}")
        
        # 2. 搜索攻略
        try:
            guides = await search_service.search_travel_guides(
                request.destination, 
                request.preferences
            )
            context["guides"] = guides
            if guides.get("general"):
                summary_parts.append(f"攻略信息：{json.dumps(guides['general'][:3], ensure_ascii=False)}")
        except Exception as e:
            print(f"搜索攻略失败: {e}")
        
        # 3. 搜索热门景点
        try:
            attractions = await amap_client.text_search(
                f"{request.destination} 景点", 
                request.destination
            )
            context["attractions"] = attractions[:10]
            if attractions:
                summary_parts.append(f"热门景点：{', '.join([p['name'] for p in attractions[:5]])}")
        except Exception as e:
            print(f"搜索景点失败: {e}")
        
        # 4. 搜索美食餐厅（使用周边搜索获取更精准的推荐）
        try:
            # 先获取城市中心坐标
            geo_result = await amap_client.geocode(request.destination)
            if geo_result and geo_result.get("location"):
                # 周边搜索餐厅
                food = await amap_client.around_search(
                    keywords="餐厅|美食|特色菜",
                    location=geo_result["location"],
                    radius=5000
                )
                context["food"] = food[:15]
                if food:
                    food_names = [f"{p['name']}({p.get('rating', '暂无评分')}分)" for p in food[:5] if p.get('name')]
                    summary_parts.append(f"周边美食推荐：{', '.join(food_names)}")
        except Exception as e:
            print(f"搜索美食失败: {e}")
            # 降级到文本搜索
            try:
                food = await amap_client.text_search(
                    f"{request.destination} 美食 餐厅", 
                    request.destination
                )
                context["food"] = food[:10]
                if food:
                    summary_parts.append(f"推荐美食：{', '.join([p['name'] for p in food[:5]])}")
            except:
                pass
        
        # 5. 搜索酒店住宿
        try:
            hotels = await amap_client.text_search(
                f"{request.destination} 酒店 住宿", 
                request.destination
            )
            context["hotels"] = hotels[:10]
            if hotels:
                summary_parts.append(f"推荐住宿：{', '.join([p['name'] for p in hotels[:3]])}")
        except Exception as e:
            print(f"搜索酒店失败: {e}")
        
        context["summary"] = "\n".join(summary_parts)
        return context
    
    def _build_prompt(self, request: PlanRequest, context: Dict[str, Any], mode: str = "planning") -> str:
        """
        构建 AI 提示
        
        Args:
            request: 规划请求
            context: 上下文信息
            mode: 模式，"planning"=未来规划建议，"travelogue"=已发生的游记分享
        """
        prefs = "、".join(request.preferences) if request.preferences else "综合体验"
        budget_str = f"，预算约 {request.budget} 元" if request.budget else ""
        date_str = f"，出发日期 {request.start_date}" if request.start_date else ""
        desc_str = f"\n- 特殊需求：{request.description}" if request.description else ""
        
        # 交通方式说明
        transport_hints = {
            "transit": "公共交通（地铁、公交为主，适合城市游玩）",
            "walking": "步行（适合老城区、景区内深度游）",
            "bicycling": "骑行（适合环湖、滨海等风景线路）",
            "driving": "自驾（适合郊区、跨城、带行李多的情况）"
        }
        transport_desc = transport_hints.get(request.transport_mode.value, "公共交通")
        
        # 获取上下文中的美食和景点信息
        food_info = ""
        if context.get("food"):
            food_names = [f['name'] for f in context['food'][:8]]
            food_info = f"\n\n**当地热门餐厅（可参考）：**\n{', '.join(food_names)}"
        
        hotel_info = ""
        if context.get("hotels"):
            hotel_names = [h['name'] for h in context['hotels'][:5]]
            hotel_info = f"\n\n**推荐住宿区域/酒店：**\n{', '.join(hotel_names)}"
        
        if mode == "travelogue":
            # 游记模式：模拟已经发生的旅行分享，开头多样化
            prompt = self._build_travelogue_prompt(request, context, prefs, food_info, hotel_info)
        else:
            # 规划模式：为用户规划未来的旅行
            prompt = f"""你是一个经验丰富的旅行规划师，同时也是小红书风格的旅行博主！请帮我规划 {request.destination} {request.days} 天的旅行行程～

**写作风格要求（小红书风格）：**
- 语气亲切活泼，像闺蜜/好友分享一样
- 大量使用emoji表情符号增加可读性和趣味性 🎉✨🔥💯
- 给出实用的本地tips和注意事项
- 推荐要具体，说明为什么值得去提醒可能的坑点和注意事项
- 时间安排合理，考虑实际游玩和休息时间
- 使用小红书常见的标记符号：
  · 📍 标注地点
  · ⏰ 标注时间
  · 💰 标注价格/费用
  · ⭐ 标注推荐指数
  · 🔥 标注热门/必去
  · 💡 标注小贴士
  · ⚠️ 标注注意事项/避坑
  · 📸 标注拍照点
  · 🍜 标注美食
  · 🏨 标注住宿
  · 🚇 标注交通
- 用「」『』等符号突出重点
- 适当使用分割线 ———— 或 ·····
- 每个景点给出「推荐指数」⭐⭐⭐⭐⭐
- 标题用【】包裹，如【Day1 初见{request.destination}】
- 段落之间空行，阅读舒适

**用户需求：**
- 📍 目的地：{request.destination}
- 📅 天数：{request.days} 天
- 💝 偏好：{prefs}
- 🚗 出行方式：{transport_desc}{budget_str}{date_str}{desc_str}

**交通建议原则：**
- 🚇 市区景点密集 → 地铁+步行
- 🚴 环湖/滨海/公园 → 可以骑行
- 🚕 郊区/山区 → 打车或自驾
- 🚶 老城区/古镇 → 步行慢逛
{food_info}{hotel_info}

**规划要求：**
1. 路线合理，避免来回折腾
2. 每天3-4个主要景点，节奏适中
3. 🍜 推荐当地特色美食，标注人均价格
4. 📸 标注最佳游玩时间和拍照点
5. 💰 预估每天花费
6. ⚠️ 提醒注意事项和避坑指南
7. 💡 给出实用的本地tips

**时间安排要求：**
- 不要写精确到分钟的时间如"9:00-12:00"
- 用大致时间段描述，如"上午"、"中午"、"下午"、"傍晚"、"晚上"
- 或者用"早起"、"午后"、"黄昏"等更自然的表达

**输出格式示例：**
【Day1 初见XX】

📍 **上午 | 景点名称** ⭐⭐⭐⭐⭐
💰 门票：XX元 | 建议游玩：2小时左右
📸 拍照点：xxx
💡 小贴士：xxx

🍜 **中午 | 午餐推荐**：xxx
💰 人均：XX元

📍 **下午 | 景点名称** ⭐⭐⭐⭐
...

————————

请生成详细的行程规划，最后附上JSON格式的结构化数据（用```json```包裹）。"""
        
        return prompt
    
    def _build_travelogue_prompt(self, request: PlanRequest, context: Dict[str, Any], 
                                  prefs: str, food_info: str, hotel_info: str) -> str:
        """构建游记风格的prompt，开头多样化"""
        import random
        
        # 多样化的开头风格
        opening_styles = [
            f"刚从{request.destination}回来！趁着记忆还热乎，赶紧把这{request.days}天的行程整理出来分享给大家～",
            f"终于把{request.destination}之旅的攻略整理好了！这次{request.days}天的旅程真的太难忘了，必须记录下来！",
            f"去了一趟{request.destination}，被彻底种草了！{request.days}天玩下来，感觉还没玩够，先把这次的经验分享给你们～",
            f"心心念念的{request.destination}终于去成了！{request.days}天行程安排得明明白白，现在来交作业啦～",
            f"上周刚结束的{request.destination}之旅，{request.days}天暴走但超值！来给姐妹们避坑+种草～",
            f"这次{request.destination}{request.days}日游真的是我今年最满意的一次旅行！忍不住要分享给大家～",
            f"作为一个去过{request.destination}三次的人，这次{request.days}天的深度游终于让我摸透了这座城市！",
            f"原本只是想去{request.destination}躺平几天，结果{request.days}天玩得比上班还累（但是很快乐）！",
            f"和朋友的{request.destination}{request.days}日游圆满结束！这份攻略请收好，亲测有效～",
            f"一直想去{request.destination}，这次终于成行！{request.days}天的行程安排分享给同样想去的朋友～"
        ]
        
        # 多样化的写作人设
        personas = [
            "作为一个资深吃货",
            "作为一个摄影爱好者",
            "作为一个喜欢深度游的人",
            "作为一个预算有限的学生党",
            "作为一个带娃出行的宝妈",
            "作为一个喜欢慢节奏的人",
            "作为一个第一次去的小白",
            "作为一个本地朋友带着玩的幸运儿"
        ]
        
        opening = random.choice(opening_styles)
        persona = random.choice(personas)
        
        prompt = f"""你是一个真实的小红书旅行博主，请以第一人称写一篇{request.destination}{request.days}天游记风格的攻略。

**重要：这是一篇"已经发生"的旅行分享，不是未来规划！**

**开头请使用这个风格（可以稍作修改）：**
"{opening}"

**写作人设：**
{persona}，分享自己真实的旅行体验。

**写作风格要求（小红书风格）：**
- 用第一人称"我"来写，像是在跟闺蜜/好友聊天分享
- 大量使用emoji表情符号 🎉✨🔥💯😍🥰
- 使用小红书常见的标记符号：
  · 📍 标注地点
  · 💰 标注价格/费用
  · ⭐ 标注推荐指数（⭐⭐⭐⭐⭐）
  · 🔥 标注热门/必去
  · 💡 标注小贴士
  · ⚠️ 标注避坑提醒
  · 📸 标注拍照点
  · 🍜 标注美食
- 用「」『』等符号突出重点
- 标题用【】包裹，如【Day1】【必吃美食】
- 适当使用分割线 ———— 或 ·····
- 要有真实感，可以说"我们当时..."、"到了才发现..."、"幸好提前..."
- 分享真实的感受，比如"比想象中更美"、"有点失望"、"意外惊喜"
- 可以吐槽一些小问题，增加真实感
- 推荐的店要说"我吃了xxx，味道..."而不是"推荐xxx"

**时间描述要求：**
- 不要写精确到分钟的时间如"9:00"、"14:30"
- 用大致时间段，如"上午"、"中午"、"下午"、"傍晚"、"晚上"等等
- 或用自然表达如"早起"、"午后"、"黄昏"、"睡前"等等

**旅行信息：**
- 📍 目的地：{request.destination}
- 📅 天数：{request.days} 天
- 💝 主题偏好：{prefs}
{food_info}{hotel_info}

**内容结构：**
1. 开头引入（用上面的风格）+ 行程概览
2. 💡 行前准备小tips
3. 每天的详细行程（【Day1】【Day2】...）
4. 🍜 美食推荐（要说自己吃了什么，标注人均💰）
5. ⚠️ 踩坑提醒（真实遇到的问题）
6. ✨ 总结和建议

请生成完整的游记攻略，最后附上JSON格式的结构化数据（用```json```包裹）。"""
        
        return prompt
    
    async def _enrich_plan(
        self, 
        plan: Dict[str, Any], 
        request: PlanRequest
    ) -> Dict[str, Any]:
        """补充行程详细信息（坐标、路线、图片等）"""
        plan["id"] = str(uuid.uuid4())[:8]
        plan["created_at"] = datetime.now().isoformat()
        
        # 为每个 POI 补充坐标信息和图片
        for day_plan in plan.get("daily_plans", []):
            pois = day_plan.get("pois", [])
            for poi in pois:
                if not poi.get("location"):
                    try:
                        # 搜索 POI 获取坐标
                        results = await amap_client.text_search(
                            poi["name"], 
                            request.destination
                        )
                        if results:
                            poi["location"] = results[0].get("location", "")
                            poi["address"] = results[0].get("address", "")
                            poi["id"] = results[0].get("id", "")
                    except Exception:
                        pass
                
                # 为每个景点搜索图片
                if not poi.get("image_url"):
                    try:
                        image_url = await search_service.search_destination_image(
                            f"{request.destination} {poi['name']}"
                        )
                        if image_url:
                            poi["image_url"] = image_url
                            logger.info(f"   为景点 {poi['name']} 找到图片")
                    except Exception as e:
                        logger.debug(f"   搜索景点图片失败: {e}")
            
            # 计算相邻 POI 之间的路线
            routes = []
            for i in range(len(pois) - 1):
                if pois[i].get("location") and pois[i+1].get("location"):
                    try:
                        route = await self._calculate_route(
                            pois[i]["location"],
                            pois[i+1]["location"],
                            request.transport_mode,
                            request.destination
                        )
                        routes.append({
                            "origin": pois[i]["name"],
                            "destination": pois[i+1]["name"],
                            "mode": request.transport_mode.value,
                            **route
                        })
                    except Exception:
                        pass
            
            day_plan["routes"] = routes
        
        return plan
    
    async def _calculate_route(
        self,
        origin: str,
        destination: str,
        mode: TransportMode,
        city: str
    ) -> Dict[str, Any]:
        """计算路线"""
        if mode == TransportMode.WALKING:
            return await amap_client.route_walking(origin, destination)
        elif mode == TransportMode.DRIVING:
            return await amap_client.route_driving(origin, destination)
        elif mode == TransportMode.BICYCLING:
            return await amap_client.route_bicycling(origin, destination)
        else:  # TRANSIT
            return await amap_client.route_transit(origin, destination, city)
    
    def get_navigation_url(self, destination: str, dest_name: str = "") -> str:
        """获取导航链接"""
        return amap_client.get_navigation_url(destination, dest_name)


# 全局规划器实例
trip_planner = TripPlanner()
