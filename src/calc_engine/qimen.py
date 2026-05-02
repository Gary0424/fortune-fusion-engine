"""
奇门遁甲计算模块 - 深化版
实现: 阴阳遁定局/九宫排盘/九星八门八神/天盘地盘/格局判断
"""
import math
from datetime import datetime
from typing import Dict, Any, Optional, List
from .base import BaseFortuneSystem, CalculationResult


class QiMenSystem(BaseFortuneSystem):
    """奇门遁甲 - 时家奇门完整排盘"""

    GONG_NAME = {1:"坎一宫",2:"坤二宫",3:"震三宫",4:"巽四宫",5:"中五宫",
                 6:"乾六宫",7:"兑七宫",8:"艮八宫",9:"离九宫"}

    # 八门
    BA_MEN = ["休门","生门","伤门","杜门","景门","死门","惊门","开门"]
    MEN_ORIGIN = {"休门":1,"生门":8,"伤门":3,"杜门":4,"景门":9,"死门":2,"惊门":7,"开门":6}

    # 九星
    JIU_XING = ["天蓬","天任","天冲","天辅","天英","天芮","天柱","天心","天禽"]
    XING_ORIGIN = {"天蓬":1,"天任":8,"天冲":3,"天辅":4,"天英":9,"天芮":2,"天柱":7,"天心":6,"天禽":5}

    # 八神
    BA_SHEN = ["值符","腾蛇","太阴","六合","白虎","玄武","九地","九天"]

    # 三奇六仪
    SAN_QI = ["乙","丙","丁"]
    LIU_YI = ["戊","己","庚","辛","壬","癸"]
    SAN_QI_LIU_YI = ["戊","己","庚","辛","壬","癸","丁","丙","乙"]

    # 门星吉凶
    MEN_JX = {"休门":"吉","生门":"吉","开门":"吉","伤门":"凶","杜门":"中",
              "景门":"中","死门":"凶","惊门":"凶"}
    XING_JX = {"天蓬":"凶","天任":"吉","天冲":"吉","天辅":"吉","天英":"中",
               "天芮":"凶","天柱":"凶","天心":"吉","天禽":"中"}

    def __init__(self):
        super().__init__("奇门遁甲", 0.08)

    async def calculate(self, birth_datetime, birth_location, gender, query_scene,
                        query_time=None, **kwargs):
        import time as _t
        t0 = _t.time()
        ck = self._get_cache_key(system=self.name, dt=birth_datetime.isoformat(),
                                  scene=query_scene, query=query_time.isoformat() if query_time else "birth")
        if ck in self._cache:
            r = self._cache[ck]; r.cached = True; return r

        qt = query_time or datetime.now()

        # 定局
        ju_type, ju_num = self._ding_ju(qt)

        # 排三奇六仪地盘
        di_pan = self._pai_di_pan(ju_type, ju_num)

        # 排九星
        xing_pan = self._pai_xing(ju_type, ju_num, qt)

        # 排八门
        men_pan = self._pai_men(ju_type, ju_num, qt)

        # 排八神
        shen_pan = self._pai_shen(ju_type, xing_pan)

        # 值符值使
        zhi_fu = self.JIU_XING[(ju_num - 1) % 9]
        zhi_shi = self.BA_MEN[(ju_num - 1) % 8]

        # 格局判断
        geju = self._judge_geju(men_pan, xing_pan)

        # 评分
        score = self._calc_score(geju, men_pan, xing_pan, query_scene)

        details = {
            "起局时间": qt.strftime("%Y-%m-%d %H:%M"),
            "遁型": ju_type, "局数": ju_num,
            "值符星": zhi_fu, "值使门": zhi_shi,
            "地盘": di_pan,
            "九星": xing_pan,
            "八门": men_pan,
            "八神": shen_pan,
            "格局": geju,
        }

        # 数据质量标记
        details["_has_minute"] = birth_datetime.minute != 0
        details["_has_location"] = birth_location is not None
        
        # 奇门特有确定性评估：格局质量和三盘完整度
        geju_score = sum(1 for g in geju if g.get("吉凶") in ("吉","大吉")) if geju else 0
        details["_certainty_bonus"] = min(0.08, geju_score * 0.02)
        details["_certainty_bonus"] += 0.04 if zhi_fu and zhi_shi else 0.0
        
        # 计算动态置信度
        confidence = self._calc_confidence(details, query_scene)
        
        result = CalculationResult(system=self.name, score=score,
            confidence=confidence, trend=self._score_to_trend(score),
            risk_level=self._risk_from_geju(geju),
            details=details, calculation_time_ms=int((_t.time()-t0)*1000))
        self._cache[ck] = result
        return result
    
    def _assess_certainty(self, result_data: Dict) -> float:
        return result_data.get("_certainty_bonus", 0.0)
    
    def _scene_fitness(self, scene: str) -> float:
        if scene == "具体事件": return 0.05
        elif scene == "年度趋势": return 0.03
        return 0.0

    def _ding_ju(self, dt):
        """定阴阳遁和局数"""
        # 冬至后阳遁(11月16-1月15), 夏至后阴遁(5月16-11月15)
        m, d = dt.month, dt.day
        is_yang = (m == 12 or m == 1) or (m == 11 and d >= 16) or (m == 5 and d < 16)
        ju_type = "阳遁" if is_yang else "阴遁"
        # 局数 = (年+月+日+时) % 9 + 1
        ju_num = (dt.year + dt.month + dt.day + dt.hour) % 9 + 1
        return ju_type, ju_num

    def _pai_di_pan(self, ju_type, ju_num):
        """地盘: 三奇六仪排布"""
        # 阳遁顺排(1-9), 阴遁逆排(9-1)
        result = {}
        qi_yi = self.SAN_QI_LIU_YI
        # 戊起宫
        start = ju_num
        for i, qy in enumerate(qi_yi):
            if ju_type == "阳遁":
                gong = ((start - 1 + i) % 9) + 1
            else:
                gong = ((start - 1 - i) % 9) + 1
            if gong == 5: gong = 2  # 中五寄坤二
            result[gong] = qy
        return result

    def _pai_xing(self, ju_type, ju_num, dt):
        """九星排布: 蓬任冲辅英芮柱心禽"""
        result = {}
        # 时干
        TIAN_GAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
        base = datetime(2000,1,7)
        d = (dt.date() - base.date()).days
        shi_gan = TIAN_GAN[(d * 12 + dt.hour // 2) % 10]

        # 找时干在六仪中的位置
        liu_yi = self.LIU_YI  # 戊己庚辛壬癸
        shi_gan_idx = liu_yi.index(shi_gan) if shi_gan in liu_yi else 0
        start_gong = ju_num
        for i, xing in enumerate(self.JIU_XING):
            if ju_type == "阳遁":
                gong = ((start_gong - 1 + i - shi_gan_idx) % 9) + 1
            else:
                gong = ((start_gong - 1 - i + shi_gan_idx) % 9) + 1
            if gong == 5: gong = 2
            result[gong] = xing
        return result

    def _pai_men(self, ju_type, ju_num, dt):
        """八门排布: 值使随时干"""
        result = {}
        # 时支
        DI_ZHI = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
        zhi_idx = (dt.hour // 2 + 1) % 12 or 12

        # 值使门从生门开始, 随宫数转动
        start_idx = self.BA_MEN.index("生门")
        gong_order = [1,8,3,4,9,2,7,6]  # 坎艮震巽中乾兑

        # 时支落宫
        shi_gong = (zhi_idx % 9) or 1
        if shi_gong == 5: shi_gong = 2

        # 值使=值使门, 从时支宫出发
        for i, men in enumerate(self.BA_MEN):
            if ju_type == "阳遁":
                gong = ((shi_gong - 1 + i) % 9) + 1
            else:
                gong = ((shi_gong - 1 - i) % 9) + 1
            if gong == 5: gong = 2
            result[gong] = men
        return result

    def _pai_shen(self, ju_type, xing_pan):
        """八神排布"""
        result = {}
        # 找值符星所在宫
        zhi_fu_gong = 1
        for gong, xing in xing_pan.items():
            if xing == "天心":
                zhi_fu_gong = gong
                break

        for i, shen in enumerate(self.BA_SHEN):
            if ju_type == "阳遁":
                gong = ((zhi_fu_gong - 1 + i) % 9) + 1
            else:
                gong = ((zhi_fu_gong - 1 - i) % 9) + 1
            if gong == 5: gong = 2
            result[gong] = shen
        return result

    def _judge_geju(self, men_pan, xing_pan):
        geju = []
        for gong in [1,2,3,4,6,7,8,9]:
            men = men_pan.get(gong, "")
            xing = xing_pan.get(gong, "")
            mjx = self.MEN_JX.get(men, "中")
            xjx = self.XING_JX.get(xing, "中")
            if mjx == "吉" and xjx == "吉": jx = "大吉"
            elif mjx == "凶" and xjx == "凶": jx = "大凶"
            elif mjx == "凶" or xjx == "凶": jx = "凶"
            elif mjx == "吉" and xjx == "中": jx = "中吉"
            else: jx = "平"
            geju.append({"宫":self.GONG_NAME[gong],"门":men,"星":xing,"吉凶":jx})
        return geju

    def _calc_score(self, geju, men_pan, xing_pan, scene):
        best = [g for g in geju if g["吉凶"] == "大吉"]
        good = [g for g in geju if g["吉凶"] in ("中吉","吉")]
        bad = [g for g in geju if g["吉凶"] in ("凶","大凶")]
        base = 50
        if best: base += 25
        elif good: base += 10
        if bad: base -= 10
        # 值符宫加成
        zf = [g for g in geju if g["星"] in ("天心","天任")]
        if zf and zf[0]["吉凶"] in ("大吉","中吉","吉"): base += 8
        sf = {"具体事件":1.1,"年度趋势":1.0,"终身格局":0.95}.get(scene, 1.0)
        return min(100, max(0, round(base * sf, 2)))

    def _risk_from_geju(self, geju):
        if any(g["吉凶"] == "大凶" for g in geju): return "high"
        if any(g["吉凶"] == "凶" for g in geju): return "medium"
        return "low"