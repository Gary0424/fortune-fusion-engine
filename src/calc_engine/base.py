"""
命理体系基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class CalculationResult:
    """计算结果标准格式"""
    system: str                          # 体系名称
    score: float                         # 0-100 吉凶评分
    confidence: float                    # 0-1 置信度
    trend: str                           # positive/neutral/negative
    risk_level: str                      # none/low/medium/high/critical
    details: Dict[str, Any]              # 体系特有详细数据
    calculation_time_ms: int             # 计算耗时
    cached: bool = False                 # 是否来自缓存
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "system": self.system,
            "score": self.score,
            "confidence": self.confidence,
            "trend": self.trend,
            "risk_level": self.risk_level,
            "details": self.details,
            "calculation_time_ms": self.calculation_time_ms,
            "cached": self.cached,
        }


class BaseFortuneSystem(ABC):
    """命理体系基类"""
    
    def __init__(self, name: str, weight: float):
        self.name = name
        self.weight = weight
        self._cache = {}
        
    @abstractmethod
    async def calculate(
        self,
        birth_datetime: datetime,
        birth_location: Dict[str, float],
        gender: str,
        query_scene: str,
        query_time: Optional[datetime] = None,
        **kwargs
    ) -> CalculationResult:
        """
        执行命理计算
        
        Args:
            birth_datetime: 出生时间
            birth_location: 出生地点 {latitude, longitude}
            gender: 性别 (male/female)
            query_scene: 查询场景 (终身格局/年度趋势/具体事件/...)
            query_time: 查询时间（用于动态趋势计算）
            **kwargs: 其他参数
        
        Returns:
            CalculationResult: 标准化计算结果
        """
        pass
    
    def _get_cache_key(self, **params) -> str:
        """生成缓存键"""
        import hashlib
        key_str = "|".join(f"{k}={v}" for k, v in sorted(params.items()))
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _calc_confidence(self, result_data: Dict[str, Any], scene: str) -> float:
        """
        通用置信度计算框架
        子类可覆盖此方法实现体系特定的置信度逻辑
        
        框架因子:
        - 数据完整度 (0-0.10): 时/分/经纬度
        - 计算确定性 (0-0.10): 子类根据结果特征计算
        - 场景适配度 (-0.05~+0.05): 场景与体系匹配程度
        """
        base = 0.80
        
        # 1. 数据完整度 (0-0.10)
        data_score = 0.0
        if result_data.get('_has_minute'): data_score += 0.03
        if result_data.get('_has_second'): data_score += 0.02
        if result_data.get('_has_location'): data_score += 0.03
        base += data_score
        
        # 2. 计算确定性 (子类可覆盖)
        certainty = self._assess_certainty(result_data)
        base += certainty
        
        # 3. 场景适配度 (-0.05 ~ +0.05)
        scene_fit = self._scene_fitness(scene)
        base += scene_fit
        
        return min(0.95, max(0.50, round(base, 2)))
    
    def _assess_certainty(self, result_data: Dict[str, Any]) -> float:
        """子类覆盖：计算确定性因子 (0-0.10)"""
        return 0.0
    
    def _scene_fitness(self, scene: str) -> float:
        """子类覆盖：场景适配度 (-0.05 ~ +0.05)"""
        return 0.0
    
    def _score_to_trend(self, score: float) -> str:
        """分数转趋势"""
        if score >= 70:
            return "positive"
        elif score >= 50:
            return "neutral"
        else:
            return "negative"
    
    def _score_to_risk(self, score: float) -> str:
        """分数转风险等级"""
        if score >= 90:
            return "none"
        elif score >= 70:
            return "low"
        elif score >= 50:
            return "medium"
        elif score >= 30:
            return "high"
        else:
            return "critical"
