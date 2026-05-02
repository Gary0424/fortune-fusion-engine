"""
数字命理学计算模块 - 深化版
实现: 生命灵数/命运数/灵魂数/人格数/生日数/星座数 综合分析
"""
from datetime import datetime
from typing import Dict, Any, Optional
from .base import BaseFortuneSystem, CalculationResult


class NumerologySystem(BaseFortuneSystem):
    """数字命理学 - 毕达哥拉斯体系完整实现"""

    # 数字含义
    NUM_TRAITS = {
        1: {"特质":"领导力/独立/创造力","优势":["自信","勇敢","开拓"],"挑战":["自我","固执"],"适合领域":"创业/管理"},
        2: {"特质":"合作/平衡/敏感","优势":["外交","细致","直觉"],"挑战":["优柔寡断","依赖"],"适合领域":"外交/协调/艺术"},
        3: {"特质":"表达/社交/乐观","优势":["魅力","创意","沟通"],"挑战":["浮躁","表面化"],"适合领域":"艺术/表演/销售"},
        4: {"特质":"稳定/务实/组织","优势":["勤劳","可靠","踏实"],"挑战":["死板","苛刻"],"适合领域":"工程/财务/管理"},
        5: {"特质":"自由/变化/冒险","优势":["多才","适应力","热情"],"挑战":["冲动","不稳定"],"适合领域":"旅行/媒体/销售"},
        6: {"特质":"责任/关爱/和谐","优势":["奉献","包容","艺术"],"挑战":["过度操劳","控制"],"适合领域":"教育/医疗/艺术"},
        7: {"特质":"分析/灵性/内省","优势":["智慧","洞察","追求真理"],"挑战":["封闭","孤独"],"适合领域":"科研/哲学/精神"},
        8: {"特质":"成就/权力/物质","优势":["领导力","执行力","商业头脑"],"挑战":["物质主义","压力"],"适合领域":"商业/金融/法律"},
        9: {"特质":"智慧/慈悲/完成","优势":["博爱","理想主义","艺术"],"挑战":["脱离现实","逃避"],"适合领域":"慈善/艺术/人道"},
        11: {"特质":"直觉/灵感/理想(主灵数)","优势":["远见","启发他人","理想主义"],"挑战":["敏感","高压"],"适合领域":"精神/艺术/领导"},
        22: {"特质":"大师/建筑/实践(主灵数)","优势":["实现力","领导力","大格局"],"挑战":["完美主义","自我"],"适合领域":"建筑/政治/商业"},
        33: {"特质":"慈爱/服务/牺牲(主灵数)","优势":["大爱","牺牲精神","启发"],"挑战":["过度牺牲","压力"],"适合领域":"慈善/教育/精神"},
    }

    # 主数字
    MASTER_NUMS = {11, 22, 33}

    def __init__(self):
        super().__init__("数字命理学", 0.03)

    async def calculate(self, birth_datetime, birth_location, gender, query_scene,
                      query_time=None, **kwargs):
        import time as _t
        t0 = _t.time()
        ck = self._get_cache_key(system=self.name, dt=birth_datetime.isoformat(),
                                  scene=query_scene, query=query_time.isoformat() if query_time else "birth")
        if ck in self._cache:
            r = self._cache[ck]; r.cached = True; return r

        # 生日数字
        birth_str = birth_datetime.strftime("%Y%m%d")
        year_str = str(birth_datetime.year)
        month_str = str(birth_datetime.month).zfill(2)
        day_str = str(birth_datetime.day).zfill(2)

        # 生命灵数 (Path Number)
        life_num = self._digital_root(birth_str)

        # 命运数 (Destiny Number) - 名字字母
        destiny_num = self._calc_destiny(birth_datetime, kwargs.get("name",""))

        # 灵魂数 (Soul Number) - 生日之月+日
        soul_num = self._digital_root(month_str + day_str)

        # 人格数 (Personality Number) - 生日之y+月
        personality_num = self._digital_root(year_str[-2:] + month_str)

        # 生日数 (Birthday Number) - 直接日
        birthday_num = birth_datetime.day

        # 成熟数
        mature_num = self._digital_root(str(life_num + destiny_num))

        # 个人年
        personal_year = (datetime.now().year + self._digital_root(
            str(datetime.now().month) + str(datetime.now().day))) % 9 or 9

        # 星座数 (1-12对应白羊-双鱼)
        zodiac_num = birth_datetime.month
        if birth_datetime.month == 3 and birth_datetime.day >= 21: zodiac_num = 1
        elif birth_datetime.month == 4 and birth_datetime.day >= 20: zodiac_num = 2
        elif birth_datetime.month == 5 and birth_datetime.day >= 21: zodiac_num = 3
        elif birth_datetime.month == 6 and birth_datetime.day >= 21: zodiac_num = 4
        elif birth_datetime.month == 7 and birth_datetime.day >= 23: zodiac_num = 5
        elif birth_datetime.month == 8 and birth_datetime.day >= 23: zodiac_num = 6
        elif birth_datetime.month == 9 and birth_datetime.day >= 23: zodiac_num = 7
        elif birth_datetime.month == 10 and birth_datetime.day >= 23: zodiac_num = 8
        elif birth_datetime.month == 11 and birth_datetime.day >= 22: zodiac_num = 9
        elif birth_datetime.month == 12 and birth_datetime.day >= 22: zodiac_num = 10
        elif birth_datetime.month == 1 and birth_datetime.day >= 20: zodiac_num = 11
        elif birth_datetime.month == 2 and birth_datetime.day >= 19: zodiac_num = 12

        # 解读
        life_traits = self.NUM_TRAITS.get(life_num, self.NUM_TRAITS.get(
            self._digital_root(str(life_num)), self.NUM_TRAITS[5]))

        # 评分
        score = self._calc_score(life_num, destiny_num, soul_num, personal_year, query_scene)

        details = {
            "生命灵数": {"数值": life_num, "主灵数": life_num in self.MASTER_NUMS,
                        "特质": life_traits["特质"], "优势": life_traits["优势"],
                        "挑战": life_traits["挑战"], "适合领域": life_traits["适合领域"]},
            "命运数": destiny_num,
            "灵魂数": soul_num,
            "人格数": personality_num,
            "生日数": birthday_num,
            "成熟数": mature_num,
            "个人年": personal_year,
            "星座数": zodiac_num,
        }

        # 数据质量标记
        details["_has_minute"] = birth_datetime.minute != 0
        details["_has_location"] = birth_location is not None
        
        # 数字命理特有确定性评估：生命灵数是否为大师数
        details["_certainty_bonus"] = 0.0
        if life_num in self.MASTER_NUMS: details["_certainty_bonus"] += 0.05
        if soul_num != destiny_num: details["_certainty_bonus"] += 0.03
        if personality_num != life_num: details["_certainty_bonus"] += 0.02
        
        # 计算动态置信度
        confidence = self._calc_confidence(details, query_scene)
        
        result = CalculationResult(system=self.name, score=score,
            confidence=confidence, trend=self._score_to_trend(score),
            risk_level=self._score_to_risk(score),
            details=details, calculation_time_ms=int((_t.time()-t0)*1000))
        self._cache[ck] = result
        return result
    
    def _assess_certainty(self, result_data: Dict) -> float:
        return result_data.get("_certainty_bonus", 0.0)
    
    def _scene_fitness(self, scene: str) -> float:
        if scene == "性格分析": return 0.05
        return 0.0

    def _digital_root(self, s: str) -> int:
        """数字根: 递归求和至单位数"""
        n = sum(int(c) for c in s if c.isdigit())
        while n > 9 and n not in self.MASTER_NUMS:
            n = sum(int(c) for c in str(n))
        return n

    def _calc_destiny(self, dt: datetime, name: str) -> int:
        """命运数: 用生日估算"""
        # 无姓名时用生日推算
        s = str(dt.year) + str(dt.month).zfill(2) + str(dt.day).zfill(2)
        return self._digital_root(s)

    def _calc_score(self, life_num, destiny_num, soul_num, personal_year, scene):
        base = 50.0
        # 主灵数加成
        if life_num in self.MASTER_NUMS: base += 15
        # 命运数与灵数和谐
        if self._digital_root(str(life_num + destiny_num)) in (1,2,3,5,6,8): base += 8
        # 个人年
        if personal_year in (1,5,6,8): base += 8
        elif personal_year in (4,7,9): base -= 5
        sf = {"性格分析":1.1,"终身格局":1.0,"年度趋势":1.05,"具体事件":0.90}.get(scene, 1.0)
        return min(100, max(0, round(base * sf, 2)))
