"""
融合决策引擎核心实现
"""
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

from .weights import SYSTEM_WEIGHTS, SCENE_ADJUSTMENTS, RISK_LEVELS, RISK_SCORES


@dataclass
class FusionResult:
    """融合结果标准格式"""
    score: float                          # 综合吉凶评分 0-100
    uncertainty: float                    # 不确定性（标准差）
    trend: str                            # 综合趋势
    risk_level: str                       # 综合风险等级
    reliability: str                      # 结果可靠性 high/medium/low
    
    # 详细分析
    consensus: Dict[str, Any]             # 共识性结论
    conflicts: Optional[List[Dict]]       # 冲突点
    contributing_systems: List[Dict]      # 各体系贡献度
    
    # 元数据
    calculation_time_ms: int
    scene: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "uncertainty": self.uncertainty,
            "trend": self.trend,
            "risk_level": self.risk_level,
            "reliability": self.reliability,
            "consensus": self.consensus,
            "conflicts": self.conflicts,
            "contributing_systems": self.contributing_systems,
            "calculation_time_ms": self.calculation_time_ms,
            "scene": self.scene,
            "timestamp": self.timestamp.isoformat(),
        }


class FusionEngine:
    """
    多源命理融合引擎
    支持动态权重、冲突消解、不确定性量化
    """
    
    def __init__(self):
        self.system_weights = SYSTEM_WEIGHTS.copy()
        self.scene_adjustments = SCENE_ADJUSTMENTS
        self.historical_accuracy = {}  # 各体系历史准确率
        self.user_calibrations = {}    # 用户个性化校准
        
    def fuse(
        self,
        scene: str,
        results: List[Any],  # List[CalculationResult]
        user_id: Optional[str] = None,
    ) -> FusionResult:
        """
        执行多源融合计算
        
        Args:
            scene: 预测场景
            results: 各体系计算结果列表
            user_id: 用户ID（用于个性化校准）
        
        Returns:
            FusionResult: 融合后的综合结果
        """
        import time
        start_time = time.time()
        
        # 1. 数据标准化
        normalized = self._normalize_results(results)
        
        # 2. 获取用户校准数据
        user_calibration = self._get_user_calibration(user_id)
        
        # 3. 计算动态权重
        dynamic_weights = self._calculate_dynamic_weights(
            scene, normalized, user_calibration
        )
        
        # 4. 加权得分计算
        weighted_scores = []
        for result in normalized:
            w = dynamic_weights.get(result.system, 0.05)
            weighted_scores.append(result.score * w)
        
        # 5. 不确定性量化
        score_array = np.array([r.score for r in normalized])
        uncertainty = np.std(score_array)
        
        # 6. 综合得分
        total_weight = sum(dynamic_weights.values())
        final_score = sum(weighted_scores) / total_weight if total_weight > 0 else 50.0
        
        # 7. 冲突检测与共识提取
        conflicts = self._detect_conflicts(normalized)
        consensus = self._extract_consensus(normalized, dynamic_weights)
        
        # 8. 综合风险等级
        final_risk = self._aggregate_risk(normalized, dynamic_weights)
        
        # 9. 可靠性评估
        reliability = self._calculate_reliability(normalized, uncertainty)
        
        # 10. 构建贡献度列表
        contributing = [
            {
                "system": r.system,
                "weight": round(dynamic_weights.get(r.system, 0), 3),
                "score": r.score,
                "confidence": r.confidence,
            }
            for r in normalized
        ]
        
        calculation_time = int((time.time() - start_time) * 1000)
        
        return FusionResult(
            score=round(final_score, 2),
            uncertainty=round(uncertainty, 2),
            trend=self._score_to_trend(final_score),
            risk_level=final_risk,
            reliability=reliability,
            consensus=consensus,
            conflicts=conflicts if conflicts else None,
            contributing_systems=contributing,
            calculation_time_ms=calculation_time,
            scene=scene,
        )
    
    def _normalize_results(self, results: List[Any]) -> List[Any]:
        """标准化结果（去重、过滤无效结果）"""
        valid_results = []
        seen_systems = set()
        
        for r in results:
            if r.system in seen_systems:
                continue
            if r.score < 0 or r.score > 100:
                continue
            valid_results.append(r)
            seen_systems.add(r.system)
        
        return valid_results
    
    def _get_user_calibration(self, user_id: Optional[str]) -> Dict:
        """获取用户个性化校准数据"""
        if not user_id:
            return {}
        return self.user_calibrations.get(user_id, {})
    
    def _calculate_dynamic_weights(
        self,
        scene: str,
        results: List[Any],
        user_calibration: Dict
    ) -> Dict[str, float]:
        """
        计算动态权重
        动态权重 = 基础权重 × 场景适配 × 历史准确率 × 置信度 × 用户校准
        """
        weights = {}
        scene_adj = self.scene_adjustments.get(scene, {})
        
        for result in results:
            system = result.system
            
            # 基础权重
            base = self.system_weights.get(system, 0.05)
            
            # 场景适配
            adj = scene_adj.get(system, 1.0)
            
            # 历史准确率（默认0.8）
            accuracy = self.historical_accuracy.get(system, 0.8)
            
            # 置信度
            confidence = result.confidence
            
            # 用户校准
            user_adj = user_calibration.get("weights", {}).get(system, 1.0)
            
            # 计算动态权重
            weights[system] = base * adj * accuracy * confidence * user_adj
        
        return weights
    
    def _detect_conflicts(self, results: List[Any]) -> List[Dict]:
        """
        检测体系间冲突
        分差 >= 50 视为严重冲突
        """
        conflicts = []
        scores = [(r.system, r.score) for r in results]
        
        for i, (s1, score1) in enumerate(scores):
            for s2, score2 in scores[i+1:]:
                diff = abs(score1 - score2)
                if diff >= 50:
                    conflicts.append({
                        "systems": [s1, s2],
                        "scores": [score1, score2],
                        "diff": round(diff, 2),
                        "severity": "high" if diff >= 70 else "medium",
                        "resolution": "consensus_priority" if diff < 70 else "manual_review"
                    })
        
        return conflicts
    
    def _extract_consensus(
        self,
        results: List[Any],
        weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """提取共识性结论"""
        
        # 趋势共识
        trends = [r.trend for r in results]
        trend_counts = {}
        for t in trends:
            trend_counts[t] = trend_counts.get(t, 0) + 1
        dominant_trend = max(trend_counts, key=trend_counts.get)
        trend_consensus = trend_counts[dominant_trend] / len(trends)
        
        # 风险共识
        risks = [r.risk_level for r in results]
        risk_scores = [RISK_SCORES.get(r, 2) for r in risks]
        avg_risk_score = sum(risk_scores) / len(risk_scores)
        
        # 高权重体系共识
        high_weight_systems = [
            r.system for r in results
            if weights.get(r.system, 0) >= 0.08
        ]
        
        return {
            "dominant_trend": dominant_trend,
            "trend_consensus_ratio": round(trend_consensus, 2),
            "average_risk_score": round(avg_risk_score, 2),
            "high_weight_systems": high_weight_systems,
            "consensus_systems_count": len(results),
        }
    
    def _aggregate_risk(
        self,
        results: List[Any],
        weights: Dict[str, float]
    ) -> str:
        """综合风险等级"""
        risk_scores = []
        for r in results:
            w = weights.get(r.system, 0.05)
            risk_score = RISK_SCORES.get(r.risk_level, 2)
            risk_scores.append(risk_score * w)
        
        total_weight = sum(weights.values())
        avg_risk = sum(risk_scores) / total_weight if total_weight > 0 else 2
        
        # 映射回风险等级
        if avg_risk < 0.5:
            return "none"
        elif avg_risk < 1.5:
            return "low"
        elif avg_risk < 2.5:
            return "medium"
        elif avg_risk < 3.5:
            return "high"
        else:
            return "critical"
    
    def _calculate_reliability(
        self,
        results: List[Any],
        uncertainty: float
    ) -> str:
        """计算结果可靠性"""
        # 高置信度体系占比
        high_conf_count = sum(1 for r in results if r.confidence >= 0.8)
        high_conf_ratio = high_conf_count / len(results) if results else 0
        
        # 可靠性判定
        if uncertainty < 10 and high_conf_ratio >= 0.6:
            return "high"
        elif uncertainty < 20 and high_conf_ratio >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _score_to_trend(self, score: float) -> str:
        """分数转趋势"""
        if score >= 70:
            return "positive"
        elif score >= 50:
            return "neutral"
        else:
            return "negative"
    
    def update_historical_accuracy(self, system: str, accuracy: float):
        """更新体系历史准确率"""
        self.historical_accuracy[system] = accuracy
    
    def update_user_calibration(self, user_id: str, calibration: Dict):
        """更新用户个性化校准"""
        self.user_calibrations[user_id] = calibration
