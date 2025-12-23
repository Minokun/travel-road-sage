"""
高德地图 MCP Server 客户端
使用 SSE 协议与高德 MCP Server 通信
"""
import json
import httpx
from httpx_sse import aconnect_sse
from typing import Dict, Any, List, Optional
from urllib.parse import quote
from app.config import settings


class AmapClient:
    """高德地图客户端 (支持 MCP 和 Web API)"""
    
    def __init__(self):
        # MCP 服务 Key (小程序绑定)
        self.mcp_key = settings.AMAP_KEY_VALUE
        self.mcp_url = f"https://mcp.amap.com/mcp?key={self.mcp_key}"
        
        # Web 服务 API Key (天气查询等)
        self.web_key = settings.AMAP_WEB_KEY
        self.web_api_url = "https://restapi.amap.com/v3"
        
        self.timeout = httpx.Timeout(300.0, connect=30.0)  # 5分钟超时
        self._session_url = None
    
    async def _web_api_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用高德 Web 服务 API
        
        Args:
            endpoint: API 端点
            params: 请求参数
            
        Returns:
            API 返回结果
        """
        url = f"{self.web_api_url}/{endpoint}"
        if not self.web_key:
            raise Exception("高德 Web API Key 未配置")
        params["key"] = self.web_key
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = response.json()
                
                if result.get("status") == "0":
                    info = result.get("info", "未知错误")
                    infocode = result.get("infocode", "")
                    raise Exception(f"高德 API 错误: {info} (infocode={infocode}, endpoint={endpoint})")
                
                return result
            except httpx.HTTPError as e:
                raise Exception(f"HTTP 请求错误: {e}")
    
    async def _init_session(self) -> str:
        """初始化 SSE 会话，获取消息发送 URL"""
        if self._session_url:
            return self._session_url
        
        sse_url = f"https://mcp.amap.com/sse?key={self.mcp_key}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with aconnect_sse(client, "GET", sse_url) as event_source:
                async for event in event_source.aiter_sse():
                    if event.event == "endpoint":
                        # 获取消息发送端点
                        self._session_url = event.data
                        return self._session_url
        
        raise Exception("无法初始化 MCP 会话")
    
    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具返回结果
        """
        # MCP JSON-RPC 请求格式
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # 使用 Streamable HTTP 方式调用
                mcp_url = f"https://mcp.amap.com/mcp?key={self.key}"
                response = await client.post(
                    mcp_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream"
                    }
                )
                response.raise_for_status()
                
                # 解析响应
                content_type = response.headers.get("content-type", "")
                if "text/event-stream" in content_type:
                    # SSE 响应，解析事件
                    for line in response.text.split("\n"):
                        if line.startswith("data:"):
                            data = json.loads(line[5:].strip())
                            if "result" in data:
                                return self._extract_content(data["result"])
                else:
                    # JSON 响应
                    result = response.json()
                    if "error" in result:
                        raise Exception(f"MCP Error: {result['error']}")
                    return self._extract_content(result.get("result", {}))
                
                return {}
            except httpx.HTTPError as e:
                raise Exception(f"HTTP 请求错误: {e}")
    
    def _extract_content(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """从 MCP 结果中提取内容"""
        content = result.get("content", [])
        if content and isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    try:
                        return json.loads(item.get("text", "{}"))
                    except json.JSONDecodeError:
                        return {"text": item.get("text", "")}
        return result
    
    async def text_search(self, keywords: str, city: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        关键词搜索 POI (使用 Web 服务 API)
        
        Args:
            keywords: 搜索关键词
            city: 城市名称（可选）
        """
        params = {"keywords": keywords}
        if city:
            params["city"] = city
        
        result = await self._web_api_request("place/text", params)
        return self._parse_pois(result)
    
    async def around_search(
        self, 
        keywords: str, 
        location: str, 
        radius: int = 3000
    ) -> List[Dict[str, Any]]:
        """
        周边搜索 POI (使用 Web 服务 API)
        
        Args:
            keywords: 搜索关键词
            location: 中心点坐标 lng,lat
            radius: 搜索半径(米)
        """
        params = {
            "keywords": keywords,
            "location": location,
            "radius": str(radius)
        }
        result = await self._web_api_request("place/around", params)
        return self._parse_pois(result)
    
    async def search_detail(self, poi_id: str) -> Dict[str, Any]:
        """
        查询 POI 详情 (使用 Web 服务 API)
        
        Args:
            poi_id: POI ID
        """
        result = await self._web_api_request("place/detail", {"id": poi_id})
        pois = result.get("pois", [])
        return pois[0] if pois else {}
    
    async def geocode(self, address: str, city: Optional[str] = None) -> Dict[str, Any]:
        """
        地理编码：地址 -> 坐标 (使用 Web 服务 API)
        
        Args:
            address: 地址
            city: 城市（可选）
        """
        params = {"address": address}
        if city:
            params["city"] = city
        
        result = await self._web_api_request("geocode/geo", params)
        geocodes = result.get("geocodes", [])
        if geocodes:
            return {
                "adcode": geocodes[0].get("adcode", ""),
                "location": geocodes[0].get("location", ""),
                "formatted_address": geocodes[0].get("formatted_address", ""),
                "city": geocodes[0].get("city", ""),
                "district": geocodes[0].get("district", "")
            }
        return {}
    
    async def regeocode(self, location: str) -> Dict[str, Any]:
        """
        逆地理编码：坐标 -> 地址 (使用 Web 服务 API)
        
        Args:
            location: 坐标 lng,lat
        """
        result = await self._web_api_request("geocode/regeo", {"location": location})
        regeocode = result.get("regeocode", {})
        return {
            "formatted_address": regeocode.get("formatted_address", ""),
            "addressComponent": regeocode.get("addressComponent", {})
        }
    
    async def get_weather(self, city: str) -> Dict[str, Any]:
        """
        查询天气 (使用 Web 服务 API)
        
        Args:
            city: 城市名称或 adcode
        """
        weather_city = city
        if not weather_city.isdigit():
            try:
                geo = await self.geocode(weather_city)
                if geo.get("adcode"):
                    weather_city = geo["adcode"]
            except Exception:
                pass

        try:
            result_base = await self._web_api_request("weather/weatherInfo", {
                "city": weather_city,
                "extensions": "base"
            })
            
            result_all = await self._web_api_request("weather/weatherInfo", {
                "city": weather_city,
                "extensions": "all"
            })
        except Exception as e:
            if "infocode=20003" in str(e):
                geo = {}
                try:
                    geo = await self.geocode(city)
                except Exception:
                    geo = {}
                location = geo.get("location")
                if location:
                    tz = "Asia/Shanghai"
                    if "香港" in city or weather_city == "810000":
                        tz = "Asia/Hong_Kong"
                    elif "澳门" in city or weather_city == "820000":
                        tz = "Asia/Macau"
                    elif "台湾" in city or weather_city.startswith("71"):
                        tz = "Asia/Taipei"
                    return await self._get_weather_open_meteo(location=location, timezone=tz)
            raise
        
        lives = result_base.get("lives", [])
        forecasts = result_all.get("forecasts", [])
        
        return {
            "live": lives[0] if lives else {},
            "forecasts": forecasts[0].get("casts", []) if forecasts else []
        }

    async def _get_weather_open_meteo(self, location: str, timezone: str) -> Dict[str, Any]:
        lng_lat = location.split(",")
        if len(lng_lat) != 2:
            raise Exception(f"无效坐标: {location}")
        lng = float(lng_lat[0])
        lat = float(lng_lat[1])

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lng,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
            "timezone": timezone,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        current = data.get("current") or {}
        daily = data.get("daily") or {}

        times = daily.get("time") or []
        tmax = daily.get("temperature_2m_max") or []
        tmin = daily.get("temperature_2m_min") or []
        precip = daily.get("precipitation_sum") or []
        wcode = daily.get("weather_code") or []

        forecasts = []
        for i in range(min(len(times), len(tmax), len(tmin), len(precip), len(wcode))):
            forecasts.append({
                "date": times[i],
                "daytemp": tmax[i],
                "nighttemp": tmin[i],
                "precipitation_sum": precip[i],
                "weather_code": wcode[i],
            })

        return {
            "live": {
                "reporttime": current.get("time", ""),
                "temperature": current.get("temperature_2m"),
                "apparent_temperature": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "wind_speed": current.get("wind_speed_10m"),
                "weather_code": current.get("weather_code"),
                "provider": "open-meteo",
            },
            "forecasts": forecasts,
        }
    
    async def route_walking(self, origin: str, destination: str) -> Dict[str, Any]:
        """
        步行路径规划 (使用 Web 服务 API)
        
        Args:
            origin: 起点坐标 lng,lat
            destination: 终点坐标 lng,lat
        """
        result = await self._web_api_request("direction/walking", {
            "origin": origin,
            "destination": destination
        })
        return self._parse_route(result)
    
    async def route_driving(self, origin: str, destination: str) -> Dict[str, Any]:
        """
        驾车路径规划 (使用 Web 服务 API)
        
        Args:
            origin: 起点坐标 lng,lat
            destination: 终点坐标 lng,lat
        """
        result = await self._web_api_request("direction/driving", {
            "origin": origin,
            "destination": destination
        })
        return self._parse_route(result)
    
    async def route_transit(
        self, 
        origin: str, 
        destination: str, 
        city: str,
        cityd: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        公交路径规划 (使用 Web 服务 API)
        
        Args:
            origin: 起点坐标 lng,lat
            destination: 终点坐标 lng,lat
            city: 起点城市
            cityd: 终点城市（跨城时需要）
        """
        params = {
            "origin": origin,
            "destination": destination,
            "city": city
        }
        if cityd:
            params["cityd"] = cityd
        
        result = await self._web_api_request("direction/transit/integrated", params)
        return self._parse_route(result)
    
    async def route_bicycling(self, origin: str, destination: str) -> Dict[str, Any]:
        """
        骑行路径规划 (使用 Web 服务 API)
        
        Args:
            origin: 起点坐标 lng,lat
            destination: 终点坐标 lng,lat
        """
        result = await self._web_api_request("direction/bicycling", {
            "origin": origin,
            "destination": destination
        })
        return self._parse_route(result)
    
    async def distance(self, origins: str, destination: str) -> Dict[str, Any]:
        """
        距离测量 (使用 Web 服务 API)
        
        Args:
            origins: 起点坐标 lng,lat
            destination: 终点坐标 lng,lat
        """
        result = await self._web_api_request("distance", {
            "origins": origins,
            "destination": destination,
            "type": "1"  # 1=直线距离
        })
        results = result.get("results", [])
        if results:
            return {
                "distance": int(results[0].get("distance", 0)),
                "duration": int(results[0].get("duration", 0))
            }
        return {"distance": 0, "duration": 0}
    
    def get_navigation_url(self, destination: str, dest_name: str = "") -> str:
        """
        获取高德导航唤端链接
        
        Args:
            destination: 目的地坐标 lng,lat
            dest_name: 目的地名称
        """
        # 高德地图 URI Scheme
        lng, lat = destination.split(",")
        name = quote(dest_name) if dest_name else "目的地"
        return f"https://uri.amap.com/navigation?to={lng},{lat},{name}&mode=car&coordinate=gaode"
    
    def _parse_pois(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析 POI 列表"""
        pois = []
        raw_pois = result.get("pois", [])
        if isinstance(raw_pois, list):
            for poi in raw_pois:
                biz_ext = poi.get("biz_ext", {}) if isinstance(poi.get("biz_ext"), dict) else {}
                pois.append({
                    "id": poi.get("id", ""),
                    "name": poi.get("name", ""),
                    "address": poi.get("address", "") if isinstance(poi.get("address"), str) else "",
                    "location": poi.get("location", ""),
                    "type": poi.get("type", ""),
                    "tel": poi.get("tel", "") if isinstance(poi.get("tel"), str) else "",
                    "rating": biz_ext.get("rating"),
                    "cost": biz_ext.get("cost"),
                })
        return pois
    
    def _parse_route(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """解析路线结果"""
        # MCP 返回的结果可能已经是解析好的格式
        if "distance" in result and "duration" in result:
            return {
                "distance": int(result.get("distance", 0)),
                "duration": int(result.get("duration", 0)),
                "steps": result.get("steps", [])
            }
        
        # 尝试从 route 中解析
        route = result.get("route", {})
        paths = route.get("paths", route.get("transits", []))
        if not paths:
            return {"distance": 0, "duration": 0, "steps": []}
        
        path = paths[0] if isinstance(paths, list) else paths
        return {
            "distance": int(path.get("distance", 0)),
            "duration": int(path.get("duration", 0)),
            "steps": path.get("steps", [])
        }
    
    def generate_static_map_url(
        self,
        markers: List[Dict[str, Any]] = None,
        paths: List[str] = None,
        size: str = "750*400",
        zoom: int = None
    ) -> str:
        """
        生成高德静态地图URL
        
        Args:
            markers: 标记点列表，每个包含 location(经纬度), label(标签), color(颜色)
            paths: 路径坐标列表，每个元素是 "lng,lat" 格式的坐标字符串
            size: 图片尺寸，默认 750*400
            zoom: 缩放级别，不指定则自动计算
            
        Returns:
            静态地图URL
        """
        base_url = "https://restapi.amap.com/v3/staticmap"
        params = [f"key={self.web_key}", f"size={size}"]
        
        # 添加标记点
        if markers:
            marker_strs = []
            for i, m in enumerate(markers):
                loc = m.get("location", "")
                label = m.get("label", chr(65 + i))  # A, B, C...
                color = m.get("color", "0x6366f1")
                marker_strs.append(f"mid,{color},{label}:{loc}")
            params.append(f"markers={'|'.join(marker_strs)}")
        
        # 添加路径
        if paths and len(paths) > 1:
            path_coords = ";".join(paths)
            # 路径样式：粗细,颜色,透明度(0-1),填充颜色,填充透明度:坐标
            # 使用蓝色线条，粗细6，完全不透明
            params.append(f"paths=6,0x3366FF,1,,:{ path_coords}")
        
        # 缩放级别
        if zoom:
            params.append(f"zoom={zoom}")
        
        return f"{base_url}?{'&'.join(params)}"
    
    async def download_static_map_as_base64(self, url: str) -> tuple:
        """
        下载静态地图并转换为base64
        
        Args:
            url: 静态地图URL
            
        Returns:
            (base64_data, original_url) - base64编码的图片数据和原始URL
        """
        import base64
        
        if not url:
            return "", ""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    # 转换为base64
                    image_data = base64.b64encode(response.content).decode('utf-8')
                    # 添加data URI前缀
                    base64_data = f"data:image/png;base64,{image_data}"
                    return base64_data, url
        except Exception as e:
            print(f"下载静态地图失败: {e}")
        
        return "", url
    
    async def generate_route_map(
        self,
        pois: List[Dict[str, Any]],
        transport_mode: str = "walking"
    ) -> str:
        """
        根据POI列表生成路径规划静态地图
        
        Args:
            pois: POI列表，每个包含 name, location
            transport_mode: 交通方式 walking/driving/transit
            
        Returns:
            静态地图URL
        """
        if not pois or len(pois) < 2:
            return ""
        
        # 收集所有坐标点
        all_coords = []
        markers = []
        
        for i, poi in enumerate(pois):
            loc = poi.get("location", "")
            if loc:
                all_coords.append(loc)
                markers.append({
                    "location": loc,
                    "label": chr(65 + i) if i < 26 else str(i + 1),
                    "color": "0x6366f1" if i == 0 else ("0xef4444" if i == len(pois) - 1 else "0x22c55e")
                })
        
        # 获取路径规划的详细坐标
        path_coords = []
        for i in range(len(all_coords) - 1):
            origin = all_coords[i]
            dest = all_coords[i + 1]
            
            try:
                if transport_mode == "driving":
                    route = await self.route_driving(origin, dest)
                else:
                    route = await self.route_walking(origin, dest)
                
                # 从步骤中提取路径坐标
                steps = route.get("steps", [])
                segment_coords = []
                for step in steps:
                    polyline = step.get("polyline", "")
                    if polyline:
                        # polyline 格式: "lng1,lat1;lng2,lat2;..."
                        segment_coords.extend(polyline.split(";"))
                
                # 对路径坐标进行采样，每段路径最多保留20个点
                if len(segment_coords) > 20:
                    step_size = len(segment_coords) // 20
                    segment_coords = segment_coords[::step_size]
                
                path_coords.extend(segment_coords)
            except:
                # 路径规划失败，直接连接两点
                path_coords.append(origin)
                path_coords.append(dest)
        
        # 如果没有获取到路径，使用直线连接
        if not path_coords:
            path_coords = all_coords
        
        # 最终路径最多保留100个点，避免URL过长
        if len(path_coords) > 100:
            step_size = len(path_coords) // 100
            path_coords = path_coords[::step_size]
        
        return self.generate_static_map_url(markers=markers, paths=path_coords)


# 全局客户端实例
amap_client = AmapClient()
