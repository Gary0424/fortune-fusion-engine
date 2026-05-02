"""
七政四余计算模块 - 深化版
实现: 七政(日月五星)推算/四余星(罗睺计都紫气月孛)/十二宫分布/星曜吉凶
"""
import math
from datetime import datetime
from typing import Dict, Any, Optional, List
from .base import BaseFortuneSystem, CalculationResult


class QiZhengSystem(BaseFortuneSystem):
    """七政四余 - 中西合璧天文体系"""

    TIAN_GAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
    DI_ZHI = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]

    # 七政 (日、月、水、金、火、木、土)
    QI_ZHENG = ["太阳","太阴","水星","金星","火星","木星","土星"]

    # 四余 (隐曜)
    SI_YU = ["罗睺","计都","紫气","月孛"]

    # 十二宫
    SHI_ER_GONG = ["亥","戌","酉","申","未","午","巳","辰","卯","寅","丑","子"]

    # 七政喜忌宫 (以卯酉为太阳升降线)
    # 太阳喜辰戌, 月亮喜未申, 金星喜辰酉, 火星喜巳午, 木星喜寅亥, 土星喜子丑
    SUN_LIKE = ["辰","戌"]
    MOON_LIKE = ["未","申"]
    JIN_LIKE = ["辰","酉"]
    HUO_LIKE = ["巳","午"]
    MU_LIKE = ["寅","亥"]
    TU_LIKE = ["子","丑"]

    # 宫主星 (各宫由某星曜主管)
    GONG_ZHUSHI = {
        "亥":"木星","戌":"火星","酉":"金星","申":"水星",
        "未":"太阳","午":"太阳","巳":"水星","辰":"土星",
        "卯":"木星","寅":"水星","丑":"土星","子":"月亮",
    }

    # 星曜吉凶
    XINGQING_JX = {
        "太阳":"吉","太阴":"吉","金星":"吉","木星":"吉",
        "水星":"中","土星":"中","火星":"凶",
        "罗睺":"凶","计都":"凶","紫气":"中","月孛":"凶",
    }

    # 二十八宿度数
    XIU_NAMES = [
        "角","亢","氐","房","心","尾","箕","斗","牛","女",
        "虚","危","室","壁","奎","娄","胃","昴","毕","觜",
        "参","井","鬼","柳","星","张","翼","轸"
    ]
    XIU_ZHI = [
        "辰","卯","寅","子","卯","寅","丑","丑","子","亥",
        "亥","亥","戌","戌","酉","酉","申","酉","未","申",
        "申","未","未","午","午","午","巳","巳"
    ]

    def __init__(self):
        super().__init__("七政四余", 0.06)

    async def calculate(self, birth_datetime, birth_location, gender, query_scene,
                       query_time=None, **kwargs):
        import time as _t
        t0 = _t.time()
        ck = self._get_cache_key(system=self.name, dt=birth_datetime.isoformat(),
                                  scene=query_scene, query=query_time.isoformat() if query_time else "birth")
        if ck in self._cache:
            r = self._cache[ck]; r.cached = True; return r

        # 1. 日月年柱
        year_gan = self.TIAN_GAN[(birth_datetime.year - 4) % 10]
        day_gan = self.TIAN_GAN[(birth_datetime - datetime(2000,1,7)).days % 10]
        month_zhi = self.DI_ZHI[(birth_datetime.month + 1) % 12]

        # 2. 七政分布 (简化天文算法)
        qi_zheng = self._calc_qi_zheng(birth_datetime)

        # 3. 四余星分布
        si_yu = self._calc_si_yu(birth_datetime)

        # 4. 十二宫分布
        gong_dist = self._calc_gong_distribution(birth_datetime, qi_zheng)

        # 5. 躔宿度
        chan_xiu = self._calc_chan_xiu(birth_datetime)

        # 6. 星曜吉凶分析
        jixiong = self._analyze_jixiong(qi_zheng, si_yu, gong_dist)

        # 7. 评分
        score = self._calc_score(qi_zheng, si_yu, jixiong, query_scene)

        details = {
            "年月日柱":f"{year_gan}年 {month_zhi}月 {day_gan}日",
            "七政分布":qi_zheng,
            "四余分布":si_yu,
            "十二宫":gong_dist,
            "躔宿":chan_xiu,
            "星曜吉凶":jixiong,
        }

        # 数据质量标记
        details["_has_minute"] = birth_datetime.minute != 0
        details["_has_location"] = birth_location is not None
        
        # 七政四余特有确定性评估：星曜分布完整度
        details["_certainty_bonus"] = 0.0
        qi_count = len([p for p in qi_zheng.values() if p.get("宫")])
        if qi_count >= 7: details["_certainty_bonus"] += 0.06
        si_count = len([p for p in si_yu.values() if p.get("宫")])
        if si_count >= 4: details["_certainty_bonus"] += 0.04
        
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
        if scene == "终身格局": return 0.05
        return 0.0

    def _julian_day(self, dt: datetime) -> float:
        Y, M = dt.year, dt.month
        if M <= 2: Y -= 1; M += 12
        A = int(Y/100); B = 2 - A + int(A/4)
        return int(365.25*(Y+4716)) + int(30.6001*(M+1)) + dt.day + B - 1524.5

    def _mean_longitude(self, period_days: float, base_jd: float, base_deg: float, dt: datetime) -> float:
        """平均黄经"""
        jd = self._julian_day(dt)
        return (base_deg + (jd - base_jd) * 360.0 / period_days) % 360.0

    # ===== 七政推算 =====
    def _calc_qi_zheng(self, dt: datetime) -> Dict[str, Dict]:
        """推算七政各星曜所在宫"""
        jd = self._julian_day(dt)
        base_jd = 2451545.0  # J2000.0

        # 太阳 (黄经, 直接由日期决定)
        # 春分点0度, 每天约走1度
        sun_deg = self._mean_longitude(365.25, base_jd, 280.0, dt)
        sun_gong = self._deg_to_gong(sun_deg)

        # 月亮 (约27.3天走360度)
        moon_deg = self._mean_longitude(27.32, base_jd, 100.0, dt)
        moon_gong = self._deg_to_gong(moon_deg)

        # 水星 (88天)
        mercury_deg = self._mean_longitude(87.97, base_jd, 310.0, dt)
        mercury_gong = self._deg_to_gong(mercury_deg)

        # 金星 (225天)
        venus_deg = self._mean_longitude(224.7, base_jd, 30.0, dt)
        venus_gong = self._deg_to_gong(venus_deg)

        # 火星 (687天)
        mars_deg = self._mean_longitude(686.98, base_jd, 50.0, dt)
        mars_gong = self._deg_to_gong(mars_deg)

        # 木星 (4333天 ~12年)
        jupiter_deg = self._mean_longitude(4333.0, base_jd, 120.0, dt)
        jupiter_gong = self._deg_to_gong(jupiter_deg)

        # 土星 (10759天 ~29年)
        saturn_deg = self._mean_longitude(10759.0, base_jd, 200.0, dt)
        saturn_gong = self._deg_to_gong(saturn_deg)

        result = {
            "太阳":{"黄经":round(sun_deg,1),"宫":sun_gong},
            "太阴":{"黄经":round(moon_deg,1),"宫":moon_gong},
            "水星":{"黄经":round(mercury_deg,1),"宫":mercury_gong},
            "金星":{"黄经":round(venus_deg,1),"宫":venus_gong},
            "火星":{"黄经":round(mars_deg,1),"宫":mars_gong},
            "木星":{"黄经":round(jupiter_deg,1),"宫":jupiter_gong},
            "土星":{"黄经":round(saturn_deg,1),"宫":saturn_gong},
        }
        return result

    def _deg_to_gong(self, deg: float) -> str:
        """黄经度数→十二宫地支"""
        idx = int(deg / 30) % 12
        return self.DI_ZHI[idx]

    # ===== 四余推算 =====
    def _calc_si_yu(self, dt: datetime) -> Dict[str, Dict]:
        """
        四余: 罗睺(升交点), 计都(降交点), 紫气(月孛之余),
        月孛(远地点)
        简化: 随月亮运动，约18.6年一圈
        """
        jd = self._julian_day(dt)
        # 罗睺: 约18.6年(6798天)一圈
        luo_deg = (100.0 + (jd - 2451545.0) * 360.0 / 6798.0) % 360.0
        # 计都: 罗睺对宫
        jidu_deg = (luo_deg + 180.0) % 360.0
        # 紫气: 约14个月一圈
        ziqi_deg = (100.0 + (jd - 2451545.0) * 360.0 / 435.0) % 360.0
        # 月孛: 约9年一圈
        yuebo_deg = (100.0 + (jd - 2451545.0) * 360.0 / 3285.0) % 360.0

        return {
            "罗睺":{"黄经":round(luo_deg,1),"宫":self._deg_to_gong(luo_deg)},
            "计都":{"黄经":round(jidu_deg,1),"宫":self._deg_to_gong(jidu_deg)},
            "紫气":{"黄经":round(ziqi_deg,1),"宫":self._deg_to_gong(ziqi_deg)},
            "月孛":{"黄经":round(yuebo_deg,1),"宫":self._deg_to_gong(yuebo_deg)},
        }

    # ===== 十二宫 =====
    def _calc_gong_distribution(self, dt: datetime, qi_zheng: Dict) -> Dict[str, List[str]]:
        """十二宫分布各星曜"""
        result = {zhi: [] for zhi in self.DI_ZHI}
        # 所有星曜
        all_stars = {}
        all_stars.update(qi_zheng)
        all_stars.update(self._calc_si_yu(dt))
        for star, info in all_stars.items():
            gong = info["宫"]
            if gong in result:
                result[gong].append(star)
        return result

    # ===== 躔宿度 =====
    def _calc_chan_xiu(self, dt: datetime) -> Dict:
        """躔宿度: 太阳所在宿度"""
        sun_deg = self._mean_longitude(365.25, 2451545.0, 280.0, dt)
        xiu_idx = int(sun_deg / 360 * 28) % 28
        xiu_deg = (sun_deg % 12.86)  # 每宿约12.86度
        return {
            "当前宿":self.XIU_NAMES[xiu_idx],
            "所在宫":self.XIU_ZHI[xiu_idx],
            "宿度":round(xiu_deg, 1),
        }

    # ===== 星曜吉凶 =====
    def _analyze_jixiong(self, qi_zheng: Dict, si_yu: Dict, gong_dist: Dict) -> Dict:
        result = {}
        all_stars = {}
        all_stars.update(qi_zheng)
        all_stars.update(si_yu)

        for star, info in all_stars.items():
            gong = info["宫"]
            jx = self.XINGQING_JX.get(star, "中")
            # 喜忌
            bonus = 0
            if star == "太阳" and gong in self.SUN_LIKE: bonus += 10
            elif star == "太阴" and gong in self.MOON_LIKE: bonus += 10
            elif star == "金星" and gong in self.JIN_LIKE: bonus += 8
            elif star == "火星" and gong in self.HUO_LIKE: bonus += 5
            elif star == "木星" and gong in self.MU_LIKE: bonus += 8
            elif star == "土星" and gong in self.TU_LIKE: bonus += 5

            result[star] = {"宫":gong,"吉凶":jx,"加成":bonus}
        return result

    # ===== 评分 =====
    def _calc_score(self, qi_zheng: Dict, si_yu: Dict, jixiong: Dict, scene: str) -> float:
        base = 50.0
        jia = sum(v.get("加成", 0) for v in jixiong.values())
        # 罗睺计都在命宫/官禄宫减分
        for star in ["罗睺","计都"]:
            if star in si_yu:
                gong = si_yu[star]["宫"]
                if gong in ["亥","卯","未"]: base -= 8  # 命宫三合
        # 日月金木同宫加分
        tong_gong = {}
        for star, info in qi_zheng.items():
            g = info["宫"]
            if g not in tong_gong: tong_gong[g] = []
            tong_gong[g].append(star)
        for gong, stars in tong_gong.items():
            if any(s in stars for s in ["太阳","太阴","金星","木星"]) and len(stars) >= 2:
                base += 12

        sf = {"终身格局":1.0,"年度趋势":0.95,"具体事件":0.90}.get(scene, 0.95)
        return min(100, max(0, round((base + jia * 0.5) * sf, 2)))
