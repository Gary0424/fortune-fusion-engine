"""
西方占星计算模块 - 深化版
实现: 十大行星落宫/十二星座/四元素/上升下降/相位分析
"""
import math
from datetime import datetime
from typing import Dict, Any, Optional, List
from .base import BaseFortuneSystem, CalculationResult


class AstrologySystem(BaseFortuneSystem):
    """西方占星 - 完整星盘排盘"""

    # 十二星座
    ZODIAC = [
        ("白羊座", 3, 21, "火"), ("金牛座", 4, 20, "土"),
        ("双子座", 5, 21, "风"), ("癌症座", 6, 21, "水"),
        ("狮子座", 7, 23, "火"), ("处女座", 8, 23, "土"),
        ("天秤座", 9, 23, "风"), ("天蝎座", 10, 23, "水"),
        ("射手座", 11, 22, "火"), ("摩羯座", 12, 22, "土"),
        ("水瓶座", 1, 20, "风"), ("双鱼座", 2, 19, "水"),
    ]

    # 十大行星 (含日月)
    PLANETS = ["太阳","月亮","水星","金星","火星","木星","土星","天王星","海王星","冥王星"]

    # 行星周期 (天) - 用于简化位置估算
    PLANET_PERIODS = {
        "太阳": 365.25, "月亮": 27.32, "水星": 87.97, "金星": 224.7,
        "火星": 686.98, "木星": 4333, "土星": 10759, "天王星": 30687,
        "海王星": 60190, "冥王星": 90560,
    }

    # 行星庙旺陷
    RULINGS = {
        "太阳":{"庙":"狮子座","旺":"白羊座","得":"双子座/水瓶座","陷":"水瓶座","失":"天秤座"},
        "月亮":{"庙":"巨蟹座","旺":"金牛座","得":"天蝎座/双鱼座","陷":"魔蝎座","失":"天蝎座"},
        "水星":{"庙":"双子座/处女座","旺":"水瓶座","得":"处女座","陷":"双鱼座/射手座"},
        "金星":{"庙":"金牛座/天秤座","旺":"双鱼座","得":"白羊座","陷":"天蝎座/处女座"},
        "火星":{"庙":"白羊座/天蝎座","旺":"摩羯座","得":"巨蟹座","陷":"天秤座/金牛座"},
        "木星":{"庙":"射手座/双鱼座","旺":"巨蟹座","得":"双鱼座","陷":"双子座/处女座"},
        "土星":{"庙":"摩羯座/天秤座","旺":"天蝎座","得":"天秤座","陷":"白羊座/巨蟹座"},
        "天王星":{"庙":"水瓶座","旺":"天蝎座","得":"双子座","陷":"狮子座/金牛座"},
        "海王星":{"庙":"双鱼座","旺":"天蝎座","得":"巨蟹座","陷":"处女座/双子座"},
        "冥王星":{"庙":"天蝎座","旺":"白羊座/天蝎座","得":"射手座/水瓶座","陷":"金牛座/天秤座"},
    }

    # 元素特质
    ELEMENT_TRAITS = {
        "火":{"特质":["行动力","热情","冲动","领导力"],"适合":[1.0,1.2,0.8,1.1]},
        "土":{"特质":["务实","稳定","物质","耐心"],"适合":[0.9,1.1,1.3,1.0]},
        "风":{"特质":["思维","沟通","自由","社交"],"适合":[1.0,1.3,0.9,1.2]},
        "水":{"特质":["情感","直觉","敏感","灵性"],"适合":[0.8,0.9,1.2,1.3]},
    }

    # 相位容许度 (度)
    ASPECT_ORBS = {"合":10,"六分":6,"四分":8,"三分":8,"二分":8,"对分":10}
    ASPECT_SCORES = {"合":8,"六分":5,"四分":-4,"三分":6,"二分":-6,"对分":-8}

    def __init__(self):
        super().__init__("西方占星", 0.07)

    async def calculate(self, birth_datetime, birth_location, gender, query_scene,
                       query_time=None, **kwargs):
        import time as _t
        t0 = _t.time()
        ck = self._get_cache_key(system=self.name, dt=birth_datetime.isoformat(),
                                  scene=query_scene, query=query_time.isoformat() if query_time else "birth")
        if ck in self._cache:
            r = self._cache[ck]; r.cached = True; return r

        # 1. 太阳星座
        sun_sign = self._get_sun_sign(birth_datetime)

        # 2. 月亮星座 (简化估算)
        moon_sign = self._get_moon_sign(birth_datetime)

        # 3. 上升星座 (ASC) - 需要精确计算
        asc_sign = self._get_asc_sign(birth_datetime, birth_location)

        # 4. 行星落宫
        planet_positions = self._get_planet_positions(birth_datetime)

        # 5. 元素分布
        element_dist = self._get_element_distribution(planet_positions)

        # 6. 相位分析
        aspects = self._analyze_aspects(planet_positions)

        # 7. 综合评分
        score = self._calc_score(sun_sign, planet_positions, aspects, element_dist, query_scene)

        details = {
            "太阳星座":sun_sign,
            "月亮星座":moon_sign,
            "上升星座":asc_sign,
            "行星分布":planet_positions,
            "元素分布":element_dist,
            "主要相位":aspects,
        }

        # 数据质量标记
        details["_has_minute"] = birth_datetime.minute != 0
        details["_has_location"] = birth_location is not None
        
        # 西方占星特有确定性评估：行星数量和相位
        planet_count = len([p for p in planet_positions.values() if p.get("星座")])
        aspect_count = len(aspects) if aspects else 0
        details["_certainty_bonus"] = 0.0
        if planet_count >= 8: details["_certainty_bonus"] += 0.05
        if aspect_count >= 5: details["_certainty_bonus"] += 0.03
        if len(element_dist) >= 4: details["_certainty_bonus"] += 0.02
        
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

    # ===== 太阳星座 =====
    def _get_sun_sign(self, dt: datetime) -> Dict[str, Any]:
        month, day = dt.month, dt.day
        for name, m, d, element in self.ZODIAC:
            if (month < m) or (month == m and day >= d):
                last = (m, d)
            elif month == 1 and m == 12:
                last = (12, 31)
        # Find current
        for name, m, d, element in self.ZODIAC:
            if month > m: continue
            if month == m and day >= d:
                return {"星座":name,"元素":element,"度数":self._estimate_sun_deg(dt)}
            if month == m and day < d:
                prev = self.ZODIAC[(self.ZODIAC.index((name,m,d,element))-1)%12]
                return {"星座":prev[0],"元素":prev[3],"度数":0}

    def _estimate_sun_deg(self, dt: datetime) -> int:
        """估算太阳在星座内的度数 (0-29)"""
        month, day = dt.month, dt.day
        for i, (name, m, d, _) in enumerate(self.ZODIAC):
            if month == m and day >= d:
                if month < 12:
                    next_d = self.ZODIAC[(i+1)%12]
                    days_in = (dt - datetime(dt.year, m, d)).days
                    total = (datetime(dt.year, next_d[1], next_d[2]) - datetime(dt.year, m, d)).days
                    return int(days_in / max(total, 1) * 29)
                else:
                    return int(day - d)
        return 15

    # ===== 月亮星座 =====
    def _get_moon_sign(self, dt: datetime) -> str:
        """月亮周期 ~27.3天一宫, 简化估算"""
        # 月亮每天约走13度, 27.3天走完全部12宫
        days_from_epoch = (dt - datetime(2000, 1, 1)).days
        # 月亮相位基准: 2000-01-06 月亮在白羊座0度附近
        moon_deg = (days_from_epoch * 13.2) % 360
        sign_deg = moon_deg / 30
        idx = int(sign_deg) % 12
        return {"星座":self.ZODIAC[idx][0],"元素":self.ZODIAC[idx][3]}

    # ===== 上升星座 =====
    def _get_asc_sign(self, dt: datetime, loc: Dict) -> Dict:
        """上升星座 = 出生时刻地平线升起的星座, 简化估算"""
        lng = loc.get("longitude", 120.0)
        # 粗略: 时区 + 经度修正
        jd = self._julian_day(dt)
        # GMST (格林威治恒星时)
        T = (jd - 2451545.0) / 36525.0
        GMST = 280.46061837 + 360.98564736629*(jd-2451545.0) + T*T*(0.000387933-T/38710000.0)
        GMST = GMST % 360.0
        # 地方恒星时
        LST = (GMST + lng) % 360.0
        # ASC = LST, 转换星座
        asc_deg = LST % 360.0
        sign_idx = int(asc_deg / 30) % 12
        sign_deg = asc_deg % 30
        return {"星座":self.ZODIAC[sign_idx][0],"度数":int(sign_deg),"元素":self.ZODIAC[sign_idx][3]}

    def _julian_day(self, dt: datetime) -> float:
        """儒略日"""
        Y, M = dt.year, dt.month
        if M <= 2: Y -= 1; M += 12
        A = int(Y/100); B = 2 - A + int(A/4)
        return int(365.25*(Y+4716)) + int(30.6001*(M+1)) + dt.day + B - 1524.5 + dt.hour/24.0

    # ===== 行星位置 =====
    def _get_planet_positions(self, dt: datetime) -> Dict[str, Dict]:
        """估算各行星星座位置"""
        jd = self._julian_day(dt)
        positions = {}
        for planet, period in self.PLANET_PERIODS.items():
            # 以2000-01-01为基准, 各行星位置
            base_deg = {
                "太阳":280.0,"月亮":100.0,"水星":310.0,"金星":30.0,"火星":50.0,
                "木星":120.0,"土星":200.0,"天王星":15.0,"海王星":320.0,"冥王星":200.0,
            }.get(planet, 0)
            deg = (base_deg + (jd - 2451545.0) * 360.0 / period) % 360.0
            sign_idx = int(deg / 30) % 12
            sign_deg = deg % 30
            positions[planet] = {
                "星座":self.ZODIAC[sign_idx][0],
                "度数":int(sign_deg),
                "元素":self.ZODIAC[sign_idx][3],
            }
        return positions

    # ===== 元素分布 =====
    def _get_element_distribution(self, positions: Dict) -> Dict[str, int]:
        counts = {"火":0,"土":0,"风":0,"水":0}
        for p, info in positions.items():
            if p in ("太阳","月亮"): counts[info["元素"]] += 2
            else: counts[info["元素"]] += 1
        total = sum(counts.values())
        return {k:{"数量":v,"占比":round(v/max(total,1)*100,1)} for k,v in counts.items()}

    # ===== 相位 =====
    def _analyze_aspects(self, positions: Dict) -> List[Dict]:
        """分析主要相位"""
        aspects = []
        planets = list(positions.keys())
        ZODIAC_NAMES = [z[0] for z in self.ZODIAC]
        for i in range(len(planets)):
            for j in range(i+1, len(planets)):
                p1, p2 = planets[i], planets[j]
                # 用黄经计算相位
                deg1 = (positions[p1].get("度数",15) + ZODIAC_NAMES.index(positions[p1].get("星座","白羊座"))*30) % 360
                deg2 = (positions[p2].get("度数",15) + ZODIAC_NAMES.index(positions[p2].get("星座","白羊座"))*30) % 360
                diff = abs(deg1 - deg2)
                if diff > 180: diff = 360 - diff

                aspect = None
                if diff <= 10: aspect = "合"
                elif abs(diff - 60) <= 6: aspect = "六分"
                elif abs(diff - 90) <= 8: aspect = "四分"
                elif abs(diff - 120) <= 8: aspect = "三分"
                elif abs(diff - 180) <= 10: aspect = "对分"
                if aspect:
                    score = self.ASPECT_SCORES.get(aspect, 0)
                    aspects.append({
                        "行星1":p1,"行星2":p2,"相位":aspect,
                        "度数差":round(diff,1),"得分":score,
                        "意义":self._aspect_meaning(aspect, p1, p2)
                    })
        return aspects[:10]  # 只返回最重要的10个

    def _aspect_meaning(self, aspect, p1, p2) -> str:
        meanings = {
            "合":"两颗星能量融合, 影响强烈",
            "六分":"和谐相位, 轻松发挥天赋",
            "四分":"挑战相位, 带来成长压力",
            "三分":"自然和谐, 天赋容易发挥",
            "对分":"对冲相位, 带来张力与觉醒",
        }
        return meanings.get(aspect, "")

    # ===== 评分 =====
    def _calc_score(self, sun_sign, planet_positions, aspects, element_dist, scene):
        base = 50.0

        # 太阳庙旺加成
        sun_gong = sun_sign.get("星座","")
        ruling = self.RULINGS.get("太阳",{}).get("庙","")
        if sun_gong == ruling: base += 15
        elif sun_gong in self.RULINGS.get("太阳",{}).get("得",""): base += 8
        elif sun_gong in self.RULINGS.get("太阳",{}).get("陷",""): base -= 15

        # 相位加成
        aspect_total = sum(a["得分"] for a in aspects)
        base += aspect_total * 0.5

        # 元素平衡
        vals = [v["数量"] for v in element_dist.values()]
        if max(vals) <= 3 and min(vals) >= 1: base += 8  # 平衡

        sf = {"终身格局":1.0,"性格分析":1.05,"年度趋势":0.95,"具体事件":0.85}.get(scene, 0.95)
        return min(100, max(0, round(base * sf, 2)))
