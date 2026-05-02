"""
大六壬计算模块 - 深化版
实现: 四课三传/贼克法/比用法/涉害法/十二神将/地盘排布
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from .base import BaseFortuneSystem, CalculationResult


class LiuRenSystem(BaseFortuneSystem):
    """大六壬 - 天地盘式占法"""

    TIAN_GAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
    DI_ZHI = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
    ZHI_IDX = {z:i for i,z in enumerate(DI_ZHI)}

    # 地盘 (固定)
    DI_PAN = ["亥","戌","酉","申","午","巳","辰","卯","丑","子","亥","寅"]

    # 十二天将 (贵登天门顺序)
    TIAN_JIANG = ["贵","腾","朱","六","勾","青","空","白","常","玄","阴","后"]

    # 天将吉凶
    JIANG_JX = {
        "贵":"吉","腾":"吉","朱":"凶","六":"中","勾":"凶",
        "青":"吉","空":"中","白":"凶","常":"中","玄":"凶","阴":"吉","后":"中"
    }

    # 六壬四课 (地支序列)
    GONG_ZHI = ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"]

    # 五行生克
    WX_SHENG = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    WX_KE = {"木":"土","土":"水","水":"火","火":"金","金":"木"}
    WX = {"子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火",
          "午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}

    def __init__(self):
        super().__init__("大六壬", 0.07)

    async def calculate(self, birth_datetime, birth_location, gender, query_scene,
                      query_time=None, **kwargs):
        import time as _t
        t0 = _t.time()
        ck = self._get_cache_key(system=self.name, dt=birth_datetime.isoformat(),
                                  scene=query_scene, query=query_time.isoformat() if query_time else "birth")
        if ck in self._cache:
            r = self._cache[ck]; r.cached = True; return r

        qt = query_time or datetime.now()

        # 1. 起四课
        sike = self._qi_sike(qt)

        # 2. 定三传
        sanchuan = self._ding_sanchuan(sike)

        # 3. 天将分布
        tianjiang = self._pai_tianjiang(qt)

        # 4. 课体分析
        keti = self._analyze_keti(sike, sanchuan)

        # 5. 神将吉凶
        shenjiang = self._analyze_shenjiang(sanchuan, tianjiang)

        # 6. 评分
        score = self._calc_score(keti, shenjiang, query_scene)

        details = {
            "起课时间": qt.strftime("%Y-%m-%d %H:%M"),
            "四课": sike,
            "三传": sanchuan,
            "天将": tianjiang,
            "课体": keti,
            "神将分析": shenjiang,
        }

        # 数据质量标记
        details["_has_minute"] = birth_datetime.minute != 0
        details["_has_location"] = birth_location is not None
        
        # 大六壬特有确定性评估：课体完整度
        details["_certainty_bonus"] = 0.0
        if len(sike) == 4: details["_certainty_bonus"] += 0.04
        if sanchuan and len(sanchuan) == 3: details["_certainty_bonus"] += 0.04
        if tianjiang and len(tianjiang) >= 12: details["_certainty_bonus"] += 0.03
        
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
        if scene == "具体事件": return 0.05
        elif scene == "月度趋势": return 0.03
        return 0.0

    def _qi_sike(self, dt: datetime) -> Dict[str, Any]:
        """起四课"""
        TIAN_GAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
        DI_ZHI = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
        ZHI_IDX = {z:i for i,z in enumerate(DI_ZHI)}

        # 日干支
        days = (dt - datetime(2000,1,7)).days
        ri_gan = TIAN_GAN[days % 10]
        ri_zhi = DI_ZHI[days % 12]

        # 时支
        shi_zhi = DI_ZHI[(dt.hour // 2 + 1) % 12 or 12 - 1]

        # 地盘 (以亥为正月逆布)
        di_pan = {DI_ZHI[i]: self.DI_PAN[i] for i in range(12)}

        # 四课
        ri_zhi_idx = ZHI_IDX[ri_zhi]
        # 上克下
        ke_zhi = None
        for i in range(1, 12):
            check_idx = (ri_zhi_idx + i) % 12
            check_zhi = DI_ZHI[check_idx]
            check_wx = self.WX[check_zhi]
            ri_wx = self.WX[ri_zhi]
            if self.WX_KE.get(ri_wx) == check_wx:
                ke_zhi = check_zhi
                break
            elif self.WX_SHENG.get(check_wx) == ri_wx:
                ke_zhi = check_zhi
                break

        # 四课排列
        sike_list = [
            {"课":"第一课","发用":ri_gan,"下临":di_pan[ri_zhi],"五行":self.WX[di_pan[ri_zhi]]},
            {"课":"第二课","发用":ri_gan,"下临":di_pan.get(ke_zhi or ri_zhi, ri_zhi),"五行":self.WX.get(di_pan.get(ke_zhi or ri_zhi, ri_zhi),"水")},
            {"课":"第三课","发用":ri_gan,"下临":ri_zhi,"五行":self.WX[ri_zhi]},
            {"课":"第四课","发用":ri_gan,"下临":ke_zhi or ri_zhi,"五行":self.WX.get(ke_zhi,"水")},
        ]
        return {
            "日干":ri_gan,"日支":ri_zhi,"时支":shi_zhi,
            "地盘":di_pan,"四课列表":sike_list,
            "贼克":ke_zhi or "无克"
        }

    def _ding_sanchuan(self, sike: Dict) -> List[Dict]:
        """定三传"""
        ke = sike.get("贼克", "无克")
        ri_zhi = sike["日支"]
        ri_zhi_idx = self.ZHI_IDX[ri_zhi]
        DI_ZHI = self.DI_ZHI

        if ke and ke != "无克":
            # 贼克法: 初传=发用, 中传=初传所加, 末传=中传所加
            ke_idx = self.ZHI_IDX.get(ke, 0)
            chuan_idx = ke_idx
            # 初传
            chu = ke
            # 中传
            zhong = DI_ZHI[(chuan_idx + ke_idx - ri_zhi_idx + 12) % 12]
            # 末传
            mo = DI_ZHI[(self.ZHI_IDX[zhong] + ke_idx - ri_zhi_idx + 12) % 12]
        else:
            # 无克用比用法
            chu = DI_ZHI[(ri_zhi_idx + 1) % 12]
            zhong = DI_ZHI[(ri_zhi_idx + 2) % 12]
            mo = DI_ZHI[(ri_zhi_idx + 3) % 12]

        return [
            {"传":"初传","地支":chu,"五行":self.WX.get(chu,"土"),"天将":self.TIAN_JIANG[self.ZHI_IDX.get(chu,0)%12]},
            {"传":"中传","地支":zhong,"五行":self.WX.get(zhong,"土"),"天将":self.TIAN_JIANG[self.ZHI_IDX.get(zhong,0)%12]},
            {"传":"末传","地支":mo,"五行":self.WX.get(mo,"土"),"天将":self.TIAN_JIANG[self.ZHI_IDX.get(mo,0)%12]},
        ]

    def _pai_tianjiang(self, dt: datetime) -> Dict[str, str]:
        """排天将"""
        # 贵登天门: 子丑起贵, 阳贵/阴贵
        DI_ZHI = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
        days = (dt - datetime(2000,1,7)).days
        ri_zhi = DI_ZHI[days % 12]

        # 阳贵起亥, 阴贵起未
        zhi_idx = self.ZHI_IDX.get(ri_zhi, 0)
        # 阳贵顺行, 阴贵逆行
        yang_gui = True
        start = 11 if yang_gui else 7  # 亥=11 or 未=7

        result = {}
        for i, zhi in enumerate(DI_ZHI):
            if yang_gui:
                gong = (start + i) % 12
            else:
                gong = (start - i) % 12
            result[zhi] = self.TIAN_JIANG[gong]
        return result

    def _analyze_keti(self, sike: Dict, sanchuan: List) -> Dict:
        """课体分析"""
        ke = sike.get("贼克", "")
        ri_zhi = sike["日支"]
        ri_zhi_idx = self.ZHI_IDX[ri_zhi]

        # 贼克判断
        if ke and ke != "无克":
            ke_idx = self.ZHI_IDX.get(ke, 0)
            offset = (ke_idx - ri_zhi_idx + 12) % 12
            if offset in (1, 5, 9):
                keti_name = "知一课"
            elif offset in (2, 6, 10):
                keti_name = "比用课"
            elif offset in (3, 7, 11):
                keti_name = "涉害课"
            else:
                keti_name = "遥克课"
        else:
            keti_name = "八专课"

        # 三传生克
        chu_zhi = sanchuan[0]["地支"]
        chu_wx = self.WX.get(chu_zhi, "土")
        ri_wx = self.WX.get(ri_zhi, "土")

        if self.WX_SHENG.get(chu_wx) == ri_wx:
            relation = "生"
        elif self.WX_KE.get(chu_wx) == ri_wx:
            relation = "克"
        elif chu_wx == ri_wx:
            relation = "比和"
        else:
            relation = "耗"

        return {
            "课名":keti_name,
            "初传日主":f"{chu_zhi}({chu_wx}){relation}日主",
            "吉凶定性":"吉课" if relation in ("生","比和") else "凶课"
        }

    def _analyze_shenjiang(self, sanchuan: List, tianjiang: Dict) -> Dict:
        """神将吉凶分析"""
        result = []
        for chuan in sanchuan:
            zhi = chuan["地支"]
            jiang = tianjiang.get(zhi, "")
            jx = self.JIANG_JX.get(jiang, "中")
            chuan_wx = chuan["五行"]
            result.append({
                "传":chuan["传"],
                "地支":zhi,"五行":chuan_wx,
                "天将":jiang,"将神吉凶":jx
            })
        return result

    def _calc_score(self, keti: Dict, shenjiang: List, scene: str) -> float:
        base = 50.0
        if "吉课" in keti.get("吉凶定性",""): base += 15
        else: base -= 10
        for sj in shenjiang:
            if sj.get("将神吉凶") == "吉": base += 8
            elif sj.get("将神吉凶") == "凶": base -= 6
        sf = {"具体事件":1.1,"年度趋势":1.0,"终身格局":0.95}.get(scene, 1.0)
        return min(100, max(0, round(base * sf, 2)))
