"""
搜索服务模块
包含小红书搜索和 DuckDuckGo 搜索
"""
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import sys
import os
import logging
from urllib.parse import urlencode

# 添加 utils 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.ddgs_utils import search_ddgs
from app.config import settings

logger = logging.getLogger(__name__)


class SearchService:
    """搜索服务"""
    
    def __init__(self):
        self.xiaohongshu_base_url = "https://www.xiaohongshu.com/search_result"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
    
    async def search_unsplash_image(self, destination: str) -> Optional[str]:
        """
        使用 Unsplash API 搜索旅行图片
        
        Args:
            destination: 目的地名称
            
        Returns:
            图片 URL 或 None
        """
        if not settings.UNSPLASH_ACCESS_KEY:
            logger.warning("Unsplash API Key 未配置")
            return None
        
        try:
            url = "https://api.unsplash.com/search/photos"
            params = {
                "query": f"{destination} travel scenery landscape",
                "per_page": 5,
                "orientation": "landscape",
                "content_filter": "high"
            }
            headers = {
                "Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}",
                "Accept-Version": "v1"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        if results:
                            # 返回第一张图片的 regular 尺寸 URL
                            image_url = results[0]["urls"]["regular"]
                            logger.info(f"✅ Unsplash 搜索成功: {destination}")
                            return image_url
                    else:
                        logger.warning(f"Unsplash API 返回 {response.status}")
        except Exception as e:
            logger.error(f"Unsplash 搜索失败: {str(e)}")
        
        return None
    
    def get_amap_static_image(self, location: str, markers: List[Dict] = None, zoom: int = 12) -> str:
        """
        生成高德地图静态图 URL
        
        Args:
            location: 中心点坐标 "lng,lat" 或地址
            markers: 标记点列表 [{"lng": "", "lat": ""}]
            zoom: 缩放级别 3-18
            
        Returns:
            高德静态地图 URL
        """
        base_url = "https://restapi.amap.com/v3/staticmap"
        params = {
            "location": location,
            "zoom": zoom,
            "size": "750*500",
            "scale": 2,
            "key": settings.AMAP_WEB_KEY
        }
        
        # 添加标记点
        if markers and len(markers) > 0:
            # 格式: "标记大小,标记颜色,标记标签:经度,纬度|经度,纬度"
            markers_str = "mid,0x2CB67D,A:" + "|".join(
                [f"{m.get('lng', '')},{m.get('lat', '')}" for m in markers[:5]]
            )
            params["markers"] = markers_str
        
        url = f"{base_url}?{urlencode(params)}"
        logger.info(f"📍 生成高德静态地图: {location}")
        return url
    
    async def search_xiaohongshu(
        self, 
        keyword: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索小红书攻略
        
        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            
        Returns:
            搜索结果列表
        """
        url = f"{self.xiaohongshu_base_url}?keyword={keyword}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=10) as response:
                    if response.status != 200:
                        return []
                    
                    html = await response.text()
                    return self._parse_xiaohongshu_results(html, max_results)
        except Exception as e:
            print(f"小红书搜索失败: {e}")
            return []
    
    def _parse_xiaohongshu_results(
        self, 
        html: str, 
        max_results: int
    ) -> List[Dict[str, Any]]:
        """解析小红书搜索结果"""
        results = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            # 小红书的搜索结果通常在特定的容器中
            # 由于小红书是动态加载的，这里可能需要调整
            # 返回搜索 URL 供前端使用
            results.append({
                "type": "xiaohongshu",
                "title": f"小红书搜索结果",
                "url": f"{self.xiaohongshu_base_url}?keyword={html[:50]}",
                "source": "xiaohongshu"
            })
        except Exception as e:
            print(f"解析小红书结果失败: {e}")
        
        return results[:max_results]
    
    async def search_web(
        self, 
        query: str, 
        search_type: str = "text",
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        使用 DuckDuckGo 搜索网页
        
        Args:
            query: 搜索关键词
            search_type: 搜索类型 (text/images/videos/news)
            max_results: 最大结果数
            
        Returns:
            搜索结果列表
        """
        try:
            # 在线程池中运行同步的 ddgs 搜索
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, 
                lambda: search_ddgs(query, search_type, max_results)
            )
            return results
        except Exception as e:
            print(f"DDGS 搜索失败: {e}")
            return []
    
    def _is_valid_image_url(self, url: str) -> bool:
        """
        检查图片URL是否有效（基础检查）
        
        Args:
            url: 图片URL
            
        Returns:
            是否有效
        """
        if not url:
            return False
        
        # 必须是HTTPS（微信小程序要求）
        if not url.startswith("https://"):
            return False
        
        # 排除已知无效的域名（有防盗链或不支持外链）
        invalid_domains = [
            "mmbiz.qpic.cn",  # 微信图片
            "kuaizhan.com",   # 快站
            "qpic.cn",        # QQ图片
            "sinaimg.cn",     # 新浪图片
            "dmjnb.com",      # 403防盗链
            "bdimg.com",      # 百度图片
            "baidustatic.com",
            "sogoucdn.com",   # 搜狗
            "360buyimg.com",  # 京东
            "alicdn.com",     # 阿里（部分有防盗链）
            "ctrip.com",      # 携程
            "mafengwo.net",   # 马蜂窝
            "duitang.com",    # 堆糖
            "huaban.com",     # 花瓣
            "nipic.com",      # 昵图网
            "58pic.com",      # 千图网
            "zcool.cn",       # 站酷
        ]
        for domain in invalid_domains:
            if domain in url:
                return False
        
        # 检查是否有常见图片扩展名或可靠图片服务
        valid_patterns = [
            ".jpg", ".jpeg", ".png", ".webp", ".gif",
            "unsplash.com", "pexels.com", "pixabay.com",
            "cloudfront.net", "amazonaws.com",  # AWS CDN
            "googleusercontent.com",
            "flickr.com", "staticflickr.com",
            "wikimedia.org", "wikipedia.org",
        ]
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in valid_patterns)
    
    async def _verify_image_accessible(self, url: str) -> bool:
        """
        验证图片URL是否可以访问（HEAD请求）
        
        Args:
            url: 图片URL
            
        Returns:
            是否可访问
        """
        import httpx
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                response = await client.head(url)
                if response.status_code != 200:
                    return False
                # 检查Content-Type是否为图片
                content_type = response.headers.get("content-type", "")
                if not any(t in content_type.lower() for t in ["image/", "octet-stream"]):
                    return False
                return True
        except Exception as e:
            print(f"  验证图片失败: {e}")
            return False
    
    async def search_destination_image(
        self, 
        destination: str,
        location: str = None,
        markers: List[Dict] = None
    ) -> Optional[str]:
        """
        搜索目的地图片 - 多级降级策略
        
        优先级:
        1. Unsplash API (高质量旅行图片)
        2. 高德地图静态图 (可靠的地图视图)
        3. DDGS 搜索 (备选方案)
        
        Args:
            destination: 目的地名称
            location: 地图中心点坐标 "lng,lat"
            markers: 地图标记点列表
            
        Returns:
            图片URL，如果没找到返回None
        """
        logger.info(f"🖼️ 开始搜索 {destination} 的封面图片...")
        
        # 策略1: 尝试 Unsplash API
        try:
            unsplash_url = await self.search_unsplash_image(destination)
            if unsplash_url:
                logger.info(f"✅ 使用 Unsplash 图片")
                return unsplash_url
        except Exception as e:
            logger.error(f"Unsplash 搜索异常: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
        
        # 策略2: 使用高德地图静态图
        if location and settings.AMAP_WEB_KEY:
            try:
                amap_url = self.get_amap_static_image(location, markers)
                logger.info(f"✅ 使用高德地图静态图")
                return amap_url
            except Exception as e:
                logger.warning(f"高德地图生成异常: {str(e)}")
        
        # 策略3: DDGS 搜索（备选）
        logger.info("⚠️ Unsplash 和高德地图都不可用，尝试 DDGS...")
        try:
            # 只尝试一次最有效的搜索词
            queries = [
                f"{destination} travel scenery landscape",
            ]
            
            valid_images = []
            total_filtered = 0
            filter_reasons = {}
            
            for idx, query in enumerate(queries, 1):
                try:
                    print(f"  🔍 查询 {idx}/{len(queries)}: '{query}'")
                    results = await self.search_web(query, "images", 20)
                    print(f"     DDGS返回 {len(results)} 个结果")
                    
                    if results and len(results) > 0:
                        for result in results:
                            # 优先使用image字段，其次是thumbnail
                            image_url = result.get("image") or result.get("thumbnail")
                            
                            if not image_url:
                                total_filtered += 1
                                filter_reasons["无URL"] = filter_reasons.get("无URL", 0) + 1
                                continue
                            
                            # 检查是否有效
                            if not image_url.startswith("https://"):
                                total_filtered += 1
                                filter_reasons["非HTTPS"] = filter_reasons.get("非HTTPS", 0) + 1
                                print(f"     ❌ 过滤(非HTTPS): {image_url[:80]}")
                                continue
                            
                            # 检查域名黑名单
                            invalid_domains = [
                                "mmbiz.qpic.cn", "kuaizhan.com", "qpic.cn", "sinaimg.cn",
                                "dmjnb.com", "bdimg.com", "baidustatic.com", "sogoucdn.com",
                                "360buyimg.com", "alicdn.com", "ctrip.com", "mafengwo.net",
                                "duitang.com", "huaban.com", "nipic.com", "58pic.com", "zcool.cn"
                            ]
                            is_blacklisted = False
                            for domain in invalid_domains:
                                if domain in image_url:
                                    total_filtered += 1
                                    filter_reasons[f"黑名单-{domain}"] = filter_reasons.get(f"黑名单-{domain}", 0) + 1
                                    print(f"     ❌ 过滤(黑名单-{domain}): {image_url[:80]}")
                                    is_blacklisted = True
                                    break
                            
                            if is_blacklisted:
                                continue
                            
                            # 检查是否有可信扩展名或域名
                            valid_patterns = [
                                ".jpg", ".jpeg", ".png", ".webp", ".gif",
                                "unsplash.com", "pexels.com", "pixabay.com",
                                "cloudfront.net", "amazonaws.com",
                                "googleusercontent.com", "flickr.com", "staticflickr.com",
                                "wikimedia.org", "wikipedia.org",
                            ]
                            url_lower = image_url.lower()
                            if not any(pattern in url_lower for pattern in valid_patterns):
                                total_filtered += 1
                                filter_reasons["无可信标识"] = filter_reasons.get("无可信标识", 0) + 1
                                print(f"     ❌ 过滤(无可信标识): {image_url[:80]}")
                                continue
                            
                            # 通过所有检查
                            valid_images.append(image_url)
                            print(f"     ✅ 候选图片: {image_url[:80]}")
                            
                            # 收集足够多的候选图片后开始验证
                            if len(valid_images) >= 5:
                                break
                except Exception as e:
                    print(f"     ❌ 搜索异常: {e}")
                    continue
                
                # 如果已经有候选图片，开始验证
                if valid_images:
                    print(f"  📊 过滤统计: 总共过滤 {total_filtered} 张，通过 {len(valid_images)} 张")
                    if filter_reasons:
                        print(f"     过滤原因: {filter_reasons}")
                    break
            
            if not valid_images:
                print(f"  ⚠️ 所有查询都没有返回有效候选图片")
                print(f"  📊 过滤统计: 总共过滤 {total_filtered} 张")
                if filter_reasons:
                    print(f"     过滤原因: {filter_reasons}")
                return None
            
            # 验证候选图片
            print(f"  🔍 开始验证 {len(valid_images)} 个候选图片...")
            for idx, image_url in enumerate(valid_images, 1):
                try:
                    print(f"     验证 {idx}/{len(valid_images)}: {image_url[:80]}")
                    if await self._verify_image_accessible(image_url):
                        print(f"  ✅ 找到有效图片: {image_url}")
                        return image_url
                    else:
                        print(f"     ❌ 图片无法访问(HTTP检查失败)")
                except Exception as e:
                    print(f"     ❌ 验证异常: {e}")
                    continue
            
            print(f"  ⚠️ 未找到 {destination} 的有效封面图片（所有候选图片验证失败）")
            return None
        except Exception as e:
            print(f"❌ 搜索目的地图片失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def search_travel_guides(
        self, 
        destination: str, 
        preferences: List[str] = None
    ) -> Dict[str, Any]:
        """
        综合搜索旅行攻略
        
        Args:
            destination: 目的地
            preferences: 偏好标签
            
        Returns:
            综合搜索结果
        """
        prefs = " ".join(preferences) if preferences else ""
        query = f"{destination} 旅游攻略 {prefs}".strip()
        
        # 并行搜索多个来源
        tasks = [
            self.search_web(query, "text", 5),
            self.search_web(f"{destination} 美食推荐", "text", 5),
            self.search_web(f"{destination} 景点", "text", 5),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "general": results[0] if not isinstance(results[0], Exception) else [],
            "food": results[1] if not isinstance(results[1], Exception) else [],
            "attractions": results[2] if not isinstance(results[2], Exception) else [],
            "xiaohongshu_url": f"{self.xiaohongshu_base_url}?keyword={destination}攻略"
        }


# 全局搜索服务实例
search_service = SearchService()
