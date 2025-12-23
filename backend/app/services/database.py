"""
DuckDB 数据库服务
用于存储用户信息和攻略数据

注意：DuckDB 不支持多进程并发写入，需要注意：
1. 使用 access_mode='read_write' 确保正确的访问模式
2. 使用 wal_autocheckpoint 减少WAL文件大小
3. 捕获异常并尝试恢复
"""
import duckdb
import json
import os
import atexit
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class Database:
    """DuckDB 数据库服务"""
    
    _instance = None
    _conn = None
    
    def __new__(cls, db_path: str = None):
        """单例模式，确保只有一个数据库连接"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: str = None):
        # 避免重复初始化
        if Database._conn is not None:
            self.conn = Database._conn
            return
            
        if db_path is None:
            # 默认存储在 backend/data 目录
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "travel_ai.duckdb")
        
        self.db_path = db_path
        
        # 尝试连接数据库，如果WAL损坏则尝试恢复
        try:
            self.conn = duckdb.connect(
                db_path,
                config={
                    'access_mode': 'read_write',
                    'wal_autocheckpoint': '64MB',  # 自动checkpoint减少WAL大小
                    'checkpoint_threshold': '64MB'
                }
            )
        except Exception as e:
            print(f"⚠️ 数据库连接失败: {e}")
            # 尝试删除WAL文件恢复
            wal_path = db_path + ".wal"
            if os.path.exists(wal_path):
                print(f"🔧 尝试删除损坏的WAL文件: {wal_path}")
                os.remove(wal_path)
            # 重新连接
            self.conn = duckdb.connect(
                db_path,
                config={
                    'access_mode': 'read_write',
                    'wal_autocheckpoint': '64MB'
                }
            )
        
        Database._conn = self.conn
        
        # 注册退出时的清理函数
        atexit.register(self._cleanup)
        
        self._init_tables()
    
    def _init_tables(self):
        """初始化数据表"""
        # 用户表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR PRIMARY KEY,
                openid VARCHAR UNIQUE NOT NULL,
                union_id VARCHAR,
                nickname VARCHAR,
                avatar_url VARCHAR,
                gender INTEGER DEFAULT 0,
                city VARCHAR,
                province VARCHAR,
                country VARCHAR,
                membership_tier VARCHAR DEFAULT 'regular',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 攻略表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                destination VARCHAR NOT NULL,
                days INTEGER NOT NULL,
                preferences JSON,
                description VARCHAR,
                content TEXT NOT NULL,
                plan_data JSON,
                is_public BOOLEAN DEFAULT FALSE,
                share_code VARCHAR UNIQUE,
                view_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 生成记录表（用于统计每日生成次数）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS generation_records (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                destination VARCHAR NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 创建索引
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_plans_user_id ON plans(user_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_plans_share_code ON plans(share_code)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_users_openid ON users(openid)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_generation_records_user_id ON generation_records(user_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_generation_records_date ON generation_records(generated_at)")
        
        # 添加封面图字段（如果不存在）
        try:
            self.conn.execute("ALTER TABLE plans ADD COLUMN cover_url VARCHAR")
        except:
            pass  # 字段已存在
        
        # 添加开始/结束日期字段（如果不存在）
        try:
            self.conn.execute("ALTER TABLE plans ADD COLUMN start_date VARCHAR")
        except:
            pass
        try:
            self.conn.execute("ALTER TABLE plans ADD COLUMN end_date VARCHAR")
        except:
            pass
        
        # 添加点赞数字段
        try:
            self.conn.execute("ALTER TABLE plans ADD COLUMN like_count INTEGER DEFAULT 0")
        except:
            pass
        
        # 添加会员等级字段（如果不存在）
        try:
            self.conn.execute("ALTER TABLE users ADD COLUMN membership_tier VARCHAR DEFAULT 'regular'")
        except:
            pass
        
        # 将所有现有用户设置为普通用户
        try:
            self.conn.execute("UPDATE users SET membership_tier = 'regular' WHERE membership_tier IS NULL")
        except:
            pass
        
        # 收藏表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                plan_id VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (plan_id) REFERENCES plans(id),
                UNIQUE(user_id, plan_id)
            )
        """)
        
        # 点赞表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                plan_id VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (plan_id) REFERENCES plans(id),
                UNIQUE(user_id, plan_id)
            )
        """)
        
        # 创建索引
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_favorites_plan_id ON favorites(plan_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_likes_user_id ON likes(user_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_likes_plan_id ON likes(plan_id)")
        
        # 执行checkpoint确保数据持久化
        self.conn.execute("CHECKPOINT")
    
    def _cleanup(self):
        """清理数据库连接"""
        if self.conn:
            try:
                # 执行checkpoint确保所有数据写入
                self.conn.execute("CHECKPOINT")
                self.conn.close()
                print("✅ 数据库连接已安全关闭")
            except:
                pass
    
    def checkpoint(self):
        """手动执行checkpoint，将WAL数据写入主文件"""
        try:
            self.conn.execute("CHECKPOINT")
        except Exception as e:
            print(f"Checkpoint失败: {e}")
    
    # ==================== 用户相关 ====================
    
    def create_user(self, openid: str, nickname: str = None, avatar_url: str = None, **kwargs) -> Dict[str, Any]:
        """创建用户"""
        import uuid
        user_id = str(uuid.uuid4())[:8]
        now = datetime.now()
        
        self.conn.execute("""
            INSERT INTO users (id, openid, nickname, avatar_url, gender, city, province, country, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            user_id, openid, nickname, avatar_url,
            kwargs.get('gender', 0),
            kwargs.get('city', ''),
            kwargs.get('province', ''),
            kwargs.get('country', ''),
            now, now
        ])
        
        return self.get_user_by_id(user_id)
    
    def get_user_by_openid(self, openid: str) -> Optional[Dict[str, Any]]:
        """通过 openid 获取用户"""
        result = self.conn.execute(
            "SELECT id, openid, union_id, nickname, avatar_url, gender, city, province, country, membership_tier, created_at, updated_at FROM users WHERE openid = ?", [openid]
        ).fetchone()
        
        if result:
            columns = ['id', 'openid', 'union_id', 'nickname', 'avatar_url', 
                      'gender', 'city', 'province', 'country', 'membership_tier', 
                      'created_at', 'updated_at']
            return dict(zip(columns, result))
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """通过 ID 获取用户"""
        result = self.conn.execute(
            "SELECT id, openid, union_id, nickname, avatar_url, gender, city, province, country, membership_tier, created_at, updated_at FROM users WHERE id = ?", [user_id]
        ).fetchone()
        
        if result:
            columns = ['id', 'openid', 'union_id', 'nickname', 'avatar_url', 
                      'gender', 'city', 'province', 'country', 'membership_tier', 
                      'created_at', 'updated_at']
            return dict(zip(columns, result))
        return None
    
    def update_user(self, user_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """更新用户信息"""
        allowed_fields = ['nickname', 'avatar_url', 'gender', 'city', 'province', 'country', 'membership_tier']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
        
        if not updates:
            return self.get_user_by_id(user_id)
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [datetime.now(), user_id]
        
        self.conn.execute(f"""
            UPDATE users SET {set_clause}, updated_at = ? WHERE id = ?
        """, values)
        
        return self.get_user_by_id(user_id)
    
    def get_or_create_user(self, openid: str, **kwargs) -> Dict[str, Any]:
        """获取或创建用户"""
        user = self.get_user_by_openid(openid)
        if user:
            # 如果有新信息，更新用户
            if kwargs:
                return self.update_user(user['id'], **kwargs)
            return user
        return self.create_user(openid, **kwargs)
    
    # ==================== 攻略相关 ====================
    
    def create_plan(
        self, 
        user_id: str, 
        destination: str, 
        days: int, 
        content: str,
        preferences: List[str] = None,
        description: str = None,
        plan_data: Dict = None,
        is_public: bool = False,
        cover_url: str = None,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """创建攻略"""
        import uuid
        import secrets
        
        plan_id = str(uuid.uuid4())[:8]
        share_code = secrets.token_urlsafe(6) if is_public else None
        now = datetime.now()
        
        self.conn.execute("""
            INSERT INTO plans (id, user_id, destination, days, preferences, description, 
                             content, plan_data, is_public, share_code, cover_url, 
                             start_date, end_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            plan_id, user_id, destination, days,
            json.dumps(preferences or []),
            description,
            content,
            json.dumps(plan_data) if plan_data else None,
            is_public,
            share_code,
            cover_url,
            start_date,
            end_date,
            now, now
        ])
        
        return self.get_plan_by_id(plan_id)
    
    def get_plan_by_id(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """通过 ID 获取攻略"""
        result = self.conn.execute(
            "SELECT * FROM plans WHERE id = ?", [plan_id]
        ).fetchone()
        
        if result:
            return self._parse_plan_row(result)
        return None
    
    def get_plan_by_share_code(self, share_code: str) -> Optional[Dict[str, Any]]:
        """通过分享码获取攻略"""
        result = self.conn.execute(
            "SELECT * FROM plans WHERE share_code = ? AND is_public = TRUE", [share_code]
        ).fetchone()
        
        if result:
            # 增加浏览次数
            self.conn.execute(
                "UPDATE plans SET view_count = view_count + 1 WHERE share_code = ?", 
                [share_code]
            )
            return self._parse_plan_row(result)
        return None
    
    def get_user_plans(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """获取用户的攻略列表"""
        results = self.conn.execute("""
            SELECT * FROM plans WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, [user_id, limit, offset]).fetchall()
        
        return [self._parse_plan_row(row) for row in results]
    
    def get_public_plans(self, category: str = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """获取公开的攻略列表（用于发现页面）"""
        if category and category != '热门':
            # 按偏好分类筛选
            # JSON stored in DuckDB might use unicode escape sequences
            # So we search for the JSON representation of the category
            search_term = json.dumps(category)
            results = self.conn.execute("""
                SELECT * FROM plans WHERE is_public = TRUE 
                AND preferences LIKE ?
                ORDER BY view_count DESC, created_at DESC 
                LIMIT ? OFFSET ?
            """, [f'%{search_term}%', limit, offset]).fetchall()
        else:
            # 热门：按浏览量排序
            results = self.conn.execute("""
                SELECT * FROM plans WHERE is_public = TRUE 
                ORDER BY view_count DESC, created_at DESC 
                LIMIT ? OFFSET ?
            """, [limit, offset]).fetchall()
        
        return [self._parse_plan_row(row) for row in results]
    
    def get_public_plans_count(self) -> int:
        """获取公开攻略总数"""
        result = self.conn.execute(
            "SELECT COUNT(*) FROM plans WHERE is_public = TRUE"
        ).fetchone()
        return result[0] if result else 0
    
    def update_plan(self, plan_id: str, user_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """更新攻略（只能更新自己的）"""
        allowed_fields = ['destination', 'days', 'preferences', 'description', 
                         'content', 'plan_data', 'is_public']
        updates = {}
        
        for k, v in kwargs.items():
            if k in allowed_fields and v is not None:
                if k in ['preferences', 'plan_data']:
                    updates[k] = json.dumps(v)
                else:
                    updates[k] = v
        
        if not updates:
            return self.get_plan_by_id(plan_id)
        
        # 如果设为公开且没有分享码，生成一个
        if kwargs.get('is_public') and not self._has_share_code(plan_id):
            import secrets
            updates['share_code'] = secrets.token_urlsafe(6)
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [datetime.now(), plan_id, user_id]
        
        self.conn.execute(f"""
            UPDATE plans SET {set_clause}, updated_at = ? 
            WHERE id = ? AND user_id = ?
        """, values)
        
        return self.get_plan_by_id(plan_id)
    
    def delete_plan(self, plan_id: str, user_id: str) -> bool:
        """删除攻略（只能删除自己的）"""
        # 先检查攻略是否存在且属于该用户
        existing = self.get_plan_by_id(plan_id)
        if not existing:
            return False
        if existing["user_id"] != user_id:
            return False
        
        # 先删除相关的收藏和点赞记录（外键约束）
        try:
            self.conn.execute("DELETE FROM favorites WHERE plan_id = ?", [plan_id])
            self.conn.execute("DELETE FROM likes WHERE plan_id = ?", [plan_id])
        except Exception as e:
            print(f"删除关联数据失败: {e}")
        
        # 删除攻略
        self.conn.execute(
            "DELETE FROM plans WHERE id = ? AND user_id = ?", 
            [plan_id, user_id]
        )
        
        # 验证删除成功
        deleted = self.get_plan_by_id(plan_id)
        return deleted is None
    
    def _has_share_code(self, plan_id: str) -> bool:
        """检查攻略是否有分享码"""
        result = self.conn.execute(
            "SELECT share_code FROM plans WHERE id = ?", [plan_id]
        ).fetchone()
        return result and result[0] is not None
    
    def _parse_plan_row(self, row) -> Dict[str, Any]:
        """解析攻略行数据"""
        columns = ['id', 'user_id', 'destination', 'days', 'preferences', 'description',
                  'content', 'plan_data', 'is_public', 'share_code', 'view_count', 
                  'created_at', 'updated_at', 'cover_url']
        
        # 处理字段数量不匹配的情况（旧数据可能没有cover_url）
        row_list = list(row)
        while len(row_list) < len(columns):
            row_list.append(None)
        
        plan = dict(zip(columns, row_list))
        
        # 解析 JSON 字段
        if plan['preferences']:
            try:
                plan['preferences'] = json.loads(plan['preferences'])
            except:
                plan['preferences'] = []
        
        if plan['plan_data']:
            try:
                plan['plan_data'] = json.loads(plan['plan_data'])
            except:
                plan['plan_data'] = None
        
        return plan
    
    def update_plan_cover(self, plan_id: str, cover_url: str) -> bool:
        """更新攻略封面图"""
        try:
            self.conn.execute(
                "UPDATE plans SET cover_url = ?, updated_at = ? WHERE id = ?",
                [cover_url, datetime.now(), plan_id]
            )
            return True
        except Exception as e:
            print(f"更新封面图失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        self.conn.close()
    
    # ==================== 收藏相关 ====================
    
    def add_favorite(self, user_id: str, plan_id: str) -> bool:
        """添加收藏"""
        import uuid
        try:
            fav_id = str(uuid.uuid4())[:8]
            self.conn.execute("""
                INSERT INTO favorites (id, user_id, plan_id, created_at)
                VALUES (?, ?, ?, ?)
            """, [fav_id, user_id, plan_id, datetime.now()])
            return True
        except:
            return False
    
    def remove_favorite(self, user_id: str, plan_id: str) -> bool:
        """取消收藏"""
        result = self.conn.execute(
            "DELETE FROM favorites WHERE user_id = ? AND plan_id = ?",
            [user_id, plan_id]
        )
        return result.rowcount > 0
    
    def is_favorited(self, user_id: str, plan_id: str) -> bool:
        """检查是否已收藏"""
        result = self.conn.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND plan_id = ?",
            [user_id, plan_id]
        ).fetchone()
        return result is not None
    
    def get_user_favorites(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """获取用户收藏的攻略"""
        results = self.conn.execute("""
            SELECT p.* FROM plans p
            JOIN favorites f ON p.id = f.plan_id
            WHERE f.user_id = ? AND p.is_public = TRUE
            ORDER BY f.created_at DESC
            LIMIT ? OFFSET ?
        """, [user_id, limit, offset]).fetchall()
        return [self._parse_plan_row(row) for row in results]
    
    def get_user_favorites_count(self, user_id: str) -> int:
        """获取用户收藏数量"""
        result = self.conn.execute(
            "SELECT COUNT(*) FROM favorites WHERE user_id = ?",
            [user_id]
        ).fetchone()
        return result[0] if result else 0
    
    def get_plan_favorite_count(self, plan_id: str) -> int:
        """获取攻略被收藏次数"""
        result = self.conn.execute(
            "SELECT COUNT(*) FROM favorites WHERE plan_id = ?",
            [plan_id]
        ).fetchone()
        return result[0] if result else 0
    
    # ==================== 点赞相关 ====================
    
    def add_like(self, user_id: str, plan_id: str) -> bool:
        """添加点赞"""
        import uuid
        try:
            like_id = str(uuid.uuid4())[:8]
            self.conn.execute("""
                INSERT INTO likes (id, user_id, plan_id, created_at)
                VALUES (?, ?, ?, ?)
            """, [like_id, user_id, plan_id, datetime.now()])
            # 更新攻略点赞数
            self.conn.execute(
                "UPDATE plans SET like_count = like_count + 1 WHERE id = ?",
                [plan_id]
            )
            return True
        except:
            return False
    
    def remove_like(self, user_id: str, plan_id: str) -> bool:
        """取消点赞"""
        result = self.conn.execute(
            "DELETE FROM likes WHERE user_id = ? AND plan_id = ?",
            [user_id, plan_id]
        )
        if result.rowcount > 0:
            # 更新攻略点赞数
            self.conn.execute(
                "UPDATE plans SET like_count = GREATEST(like_count - 1, 0) WHERE id = ?",
                [plan_id]
            )
            return True
        return False
    
    def is_liked(self, user_id: str, plan_id: str) -> bool:
        """检查是否已点赞"""
        result = self.conn.execute(
            "SELECT 1 FROM likes WHERE user_id = ? AND plan_id = ?",
            [user_id, plan_id]
        ).fetchone()
        return result is not None
    
    def get_plan_like_count(self, plan_id: str) -> int:
        """获取攻略点赞数"""
        result = self.conn.execute(
            "SELECT like_count FROM plans WHERE id = ?",
            [plan_id]
        ).fetchone()
        return result[0] if result else 0
    
    # ==================== 生成记录相关 ====================
    
    def record_generation(self, user_id: str, destination: str) -> None:
        """记录用户生成攻略"""
        import uuid
        record_id = str(uuid.uuid4())[:8]
        self.conn.execute("""
            INSERT INTO generation_records (id, user_id, destination)
            VALUES (?, ?, ?)
        """, [record_id, user_id, destination])
    
    def get_today_generation_count(self, user_id: str) -> int:
        """获取用户今日生成次数"""
        from datetime import date
        today = date.today()
        result = self.conn.execute("""
            SELECT COUNT(*) FROM generation_records 
            WHERE user_id = ? AND DATE(generated_at) = ?
        """, [user_id, today]).fetchone()
        return result[0] if result else 0
    
    def get_membership_limits(self, membership_tier: str) -> dict:
        """获取会员等级限制"""
        limits = {
            'regular': {'name': '普通用户', 'daily_limit': 3},
            'member': {'name': '普通会员', 'daily_limit': 7},
            'super': {'name': '超级会员', 'daily_limit': 15}
        }
        return limits.get(membership_tier, limits['regular'])
    
    def check_generation_limit(self, user_id: str) -> dict:
        """检查用户是否可以生成攻略"""
        user = self.get_user_by_id(user_id)
        if not user:
            return {'can_generate': False, 'reason': '用户不存在'}
        
        tier = user.get('membership_tier', 'regular')
        limits = self.get_membership_limits(tier)
        today_count = self.get_today_generation_count(user_id)
        
        can_generate = today_count < limits['daily_limit']
        
        return {
            'can_generate': can_generate,
            'membership_tier': tier,
            'tier_name': limits['name'],
            'daily_limit': limits['daily_limit'],
            'today_count': today_count,
            'remaining': limits['daily_limit'] - today_count if can_generate else 0
        }


# 全局数据库实例
db = Database()
