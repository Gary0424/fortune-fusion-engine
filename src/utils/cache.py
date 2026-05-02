"""
Redis 缓存层 - 多级缓存管理
"""
import json
import time
import hashlib
from typing import Optional, Any, Dict
from dataclasses import dataclass


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class CacheManager:
    """
    多级缓存管理器
    
    L1: 内存缓存 (LRU, 容量1000)
    L2: Redis 缓存 (可选, 容量更大)
    
    当 Redis 不可用时自动降级到纯内存缓存
    """
    
    def __init__(self, max_memory_entries: int = 1000, redis_url: Optional[str] = None):
        self.max_memory_entries = max_memory_entries
        self.redis_url = redis_url
        
        # L1: 内存缓存 (有序字典模拟 LRU)
        self._memory_cache: Dict[str, tuple] = {}  # key -> (value, expire_at)
        self._access_order: list = []  # LRU 顺序
        
        # L2: Redis (延迟初始化)
        self._redis = None
        self._redis_available = False
        
        # 统计
        self.stats = CacheStats()
    
    async def initialize(self):
        """初始化 Redis 连接"""
        if not self.redis_url:
            return
        
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
            )
            # 测试连接
            await self._redis.ping()
            self._redis_available = True
            import sys; sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            print("[OK] Redis cache connected")
        except Exception as e:
            print(f"[WARN] Redis unavailable, fallback to memory cache: {e}")
            self._redis_available = False
    
    async def close(self):
        """关闭 Redis 连接"""
        if self._redis:
            await self._redis.close()
    
    def _generate_key(self, prefix: str, **params) -> str:
        """生成缓存键"""
        key_str = "|".join(f"{k}={v}" for k, v in sorted(params.items()))
        hash_val = hashlib.md5(key_str.encode()).hexdigest()[:12]
        return f"ffe:{prefix}:{hash_val}"
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        # L1 检查
        if key in self._memory_cache:
            value, expire_at = self._memory_cache[key]
            if expire_at and time.time() > expire_at:
                del self._memory_cache[key]
                self._evict_lru(key)
            else:
                self._touch_lru(key)
                self.stats.hits += 1
                return value
        
        # L2 检查
        if self._redis_available:
            try:
                cached = await self._redis.get(key)
                if cached:
                    self.stats.hits += 1
                    # 回填 L1
                    self._set_memory(key, json.loads(cached), ttl=None)
                    return json.loads(cached)
            except Exception:
                self._redis_available = False
        
        self.stats.misses += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存值"""
        # L1 设置
        expire_at = time.time() + ttl if ttl else None
        self._set_memory(key, value, expire_at)
        
        # L2 设置
        if self._redis_available:
            try:
                serialized = json.dumps(value, ensure_ascii=False)
                if ttl:
                    await self._redis.setex(key, ttl, serialized)
                else:
                    await self._redis.set(key, serialized)
            except Exception:
                self._redis_available = False
        
        self.stats.sets += 1
    
    async def delete(self, key: str):
        """删除缓存"""
        self._memory_cache.pop(key, None)
        self._evict_lru(key)
        
        if self._redis_available:
            try:
                await self._redis.delete(key)
            except Exception:
                pass
    
    async def get_or_compute(
        self,
        key: str,
        compute_fn,
        ttl: Optional[int] = None,
    ) -> Any:
        """获取或计算（Cache-Aside 模式）"""
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        result = await compute_fn()
        await self.set(key, result, ttl=ttl)
        return result
    
    def _set_memory(self, key: str, value: Any, expire_at: Optional[float] = None):
        """设置内存缓存"""
        # LRU 驱逐
        while len(self._memory_cache) >= self.max_memory_entries:
            self._evict_oldest()
        
        self._memory_cache[key] = (value, expire_at)
        if key not in self._access_order:
            self._access_order.append(key)
    
    def _touch_lru(self, key: str):
        """更新 LRU 访问顺序"""
        if key in self._access_order:
            self._access_order.remove(key)
            self._access_order.append(key)
    
    def _evict_lru(self, key: str):
        """从 LRU 列表移除"""
        if key in self._access_order:
            self._access_order.remove(key)
    
    def _evict_oldest(self):
        """驱逐最久未访问的条目"""
        if self._access_order:
            oldest = self._access_order.pop(0)
            self._memory_cache.pop(oldest, None)
            self.stats.evictions += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "sets": self.stats.sets,
            "evictions": self.stats.evictions,
            "hit_rate": round(self.stats.hit_rate, 4),
            "memory_entries": len(self._memory_cache),
            "max_memory_entries": self.max_memory_entries,
            "redis_available": self._redis_available,
        }


# 全局缓存实例
cache_manager = CacheManager()
