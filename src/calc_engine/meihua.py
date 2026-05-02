"""
梅花易数计算模块 - 深化版
实现: 时间起卦/数字起卦/体用分析/五行生克/互卦变卦/断卦逻辑
"""
import math
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from .base import BaseFortuneSystem, CalculationResult


class MeiHuaSystem(BaseFortuneSystem):
    """梅花易数 - 邵康节法完整实现"""

    # 先天八卦数
    XIAN_TIAN = {"乾":1,"兑":2,"离":3,"震":4,"巽":5,"坎":6,"艮":7,"坤":8}
    XIAN_TIAN_REV = {1:"乾",2:"兑",3:"离",4:"震",5:"巽",6:"坎",7:"艮",8:"坤"}

    # 八卦五行
    GUA_WUXING = {"乾":"金","兑":"金","离":"火","震":"木","巽":"木","坎":"水","艮":"土","坤":"土"}

    # 八卦象意
    GUA_XIANG = {
        "乾":"天/父/刚健","坤":"地/母/柔顺","震":"雷/长男/奋发","巽":"风/长女/入",
        "坎":"水/中男/险陷","离":"火/中女/光明","艮":"山/少男/静止","兑":"泽/少女/喜悦"
    }

    # 六十四卦表 (上卦行, 下卦列)
    LIUSHISI_GUA = {
        ("乾","乾"):"乾为天",("坤","坤"):"坤为地",("坎","坎"):"坎为水",("离","离"):"离为火",
        ("震","震"):"震为雷",("巽","巽"):"巽为风",("艮","艮"):"艮为山",("兑","兑"):"兑为泽",
        ("乾","坎"):"天水讼",("坎","乾"):"水天需",("乾","震"):"天雷无妄",("震","乾"):"雷天大壮",
        ("乾","巽"):"天风姤",("巽","乾"):"风天小畜",("乾","艮"):"天山遁",("艮","乾"):"山天大畜",
        ("乾","兑"):"天泽履",("兑","乾"):"泽天夬",("乾","离"):"天火同人",("离","乾"):"火天大有",
        ("乾","坤"):"天地否",("坤","乾"):"地天泰",("坤","坎"):"地水师",("坎","坤"):"水地比",
        ("坤","震"):"地雷复",("震","坤"):"雷地豫",("坤","巽"):"地风升",("巽","坤"):"风地观",
        ("坤","艮"):"地山谦",("艮","坤"):"山地剥",("坤","兑"):"地泽临",("兑","坤"):"泽地萃",
        ("坤","离"):"地火明夷",("离","坤"):"火地晋",("坎","震"):"水雷屯",("震","坎"):"雷水解",
        ("坎","巽"):"水风井",("巽","坎"):"风水涣",("坎","艮"):"水山蹇",("艮","坎"):"山水蒙",
        ("坎","兑"):"水泽节",("兑","坎"):"泽水困",("坎","离"):"水火既济",("离","坎"):"火水未济",
        ("离","震"):"火雷噬嗑",("震","离"):"雷火丰",("离","巽"):"火风鼎",("巽","离"):"风火家人",
        ("离","艮"):"火山旅",("艮","离"):"山火贲",("离","兑"):"火泽睽",("兑","离"):"泽火革",
        ("震","巽"):"雷风恒",("巽","震"):"风雷益",("震","艮"):"雷山小过",("艮","震"):"山雷颐",
        ("震","兑"):"雷泽归妹",("兑","震"):"泽雷随",("巽","艮"):"风山渐",("艮","巽"):"山风蛊",
        ("巽","兑"):"风泽中孚",("兑","巽"):"泽风大过",("艮","兑"):"山泽损",("兑","艮"):"泽山咸",
    }

    # 八卦互卦表 (二三四爻为下互卦, 三四五爻为上互卦)
    # 用数字表示
    HU_GUA = {
        "乾":("乾","乾"),"坤":("坤","坤"),"震":("艮","坎"),
        "巽":("兑","离"),"坎":("震","艮"),"离":("兑","巽"),
        "艮":("坤","震"),"兑":("乾","巽"),
    }

    # 五行生克
    WX_SHENG = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    WX_KE = {"木":"土","土":"水","水":"火","火":"金","金":"木"}
    WX_BEI_SHENG = {"木":"水","火":"木","土":"火","金":"土","水":"金"}
    WX_BEI_KE = {"木":"金","土":"木","水":"土","火":"水","金":"火"}

    # 断卦吉凶表: 体用五行关系 → 吉凶
    TI_YONG_JUDGE = {
        "体生用": {"吉凶":"凶","说明":"体卦泄气，费力不讨好，事难成"},
        "体克用": {"吉凶":"吉","说明":"体卦克用，我有控制力，事可成但费力"},
        "用生体": {"吉凶":"大吉","说明":"用卦生体，有贵人相助，事易成"},
        "用克体": {"吉凶":"大凶","说明":"用卦克体，受制于外，诸事不顺"},
        "体用比和": {"吉凶":"吉","说明":"体用同五行，势均力敌，平稳顺利"},
    }

    def __init__(self):
        super().__init__("梅花易数", 0.02)

    async def calculate(self, birth_datetime, birth_location, gender, query_scene,
                        query_time=None, **kwargs):
        import time as _t
        t0 = _t.time()

        ck = self._get_cache_key(system=self.name, dt=birth_datetime.isoformat(),
                                  scene=query_scene, query=query_time.isoformat() if query_time else "birth")
        if ck in self._cache:
            r = self._cache[ck]; r.cached = True; return r

        qt = query_time or datetime.now()

        # 1. 时间起卦
        gua_info = self._time_qigua(qt)

        # 2. 体用分析
        ti_yong = self._ti_yong_analysis(gua_info)

        # 3. 互卦
        hu_gua = self._calculate_hu_gua(gua_info["上卦"], gua_info["下卦"])

        # 4. 变卦 (动爻变)
        bian_gua = self._calculate_bian_gua(gua_info)

        # 5. 五行综合断卦
        judgment = self._comprehensive_judge(gua_info, ti_yong, hu_gua, bian_gua, query_scene)

        # 6. 评分
        score = self._calculate_score(judgment, query_scene)

        details = {
            "起卦时间": qt.strftime("%Y-%m-%d %H:%M"),
            "上卦": gua_info["上卦"], "下卦": gua_info["下卦"],
            "本卦": gua_info["gua_name"], "动爻": gua_info["dong_yao"],
            "体卦": ti_yong["体卦"], "用卦": ti_yong["用卦"],
            "体用关系": ti_yong["关系"], "体用吉凶": ti_yong["吉凶"],
            "体卦五行": ti_yong["体五行"], "用卦五行": ti_yong["用五行"],
            "互卦": hu_gua["name"], "互卦上": hu_gua["上"], "互卦下": hu_gua["下"],
            "变卦": bian_gua["name"], "变卦上": bian_gua["上"], "变卦下": bian_gua["下"],
            "断卦": judgment,
        }

        # 数据质量标记
        details["_has_minute"] = birth_datetime.minute != 0
        details["_has_second"] = birth_datetime.second != 0
        details["_has_location"] = birth_location is not None
        
        # 梅花特有确定性评估
        dong_yao = gua_info.get("dong_yao", 0)
        if dong_yao == 1: details["_certainty_bonus"] = 0.08
        elif dong_yao == 2: details["_certainty_bonus"] = 0.04
        elif dong_yao >= 4: details["_certainty_bonus"] = -0.06
        else: details["_certainty_bonus"] = 0.0
        
        if ti_yong["关系"] in ("用生体", "体克用"): details["_certainty_bonus"] = details.get("_certainty_bonus", 0) + 0.04
        
        # 计算动态置信度
        confidence = self._calc_confidence(details, query_scene)
        
        result = CalculationResult(system=self.name, score=score,
            confidence=confidence, trend=self._score_to_trend(score),
            risk_level=self._risk_from_judgment(judgment),
            details=details, calculation_time_ms=int((_t.time()-t0)*1000))
        self._cache[ck] = result
        return result
    
    def _assess_certainty(self, result_data: Dict) -> float:
        return result_data.get("_certainty_bonus", 0.0)
    
    def _scene_fitness(self, scene: str) -> float:
        if scene == "具体事件": return 0.05
        elif scene == "月度趋势": return 0.03
        return 0.0

    # ===== 时间起卦 =====
    def _time_qigua(self, dt: datetime) -> Dict:
        """以年月日时数起卦 (邵康节法)"""
        y = dt.year; m = dt.month; d = dt.day; h = dt.hour
        # 地支序数 (子=1)
        zhi_num = {23:1,0:1,1:1,2:2,3:3,4:4,5:5,6:6,7:7,8:8,9:9,10:10,
                   11:11,12:12,13:1,14:2,15:3,16:4,17:5,18:6,19:7,20:8,21:9,22:10}
        shi = zhi_num.get(h, (h // 2 + 1) % 12 or 12)

        # 上卦 = (年+月+日) % 8
        upper_num = (y + m + d) % 8
        if upper_num == 0: upper_num = 8
        upper = self.XIAN_TIAN_REV[upper_num]

        # 下卦 = (年+月+日+时) % 8
        lower_num = (y + m + d + shi) % 8
        if lower_num == 0: lower_num = 8
        lower = self.XIAN_TIAN_REV[lower_num]

        # 动爻 = (年+月+日+时) % 6
        dong_yao = (y + m + d + shi) % 6
        if dong_yao == 0: dong_yao = 6

        # 卦名
        gua_name = self.LIUSHISI_GUA.get((upper, lower), f"{upper}{lower}卦")

        return {"上卦":upper, "下卦":lower, "上卦数":upper_num, "下卦数":lower_num,
                "dong_yao":dong_yao, "gua_name":gua_name}

    # ===== 体用分析 =====
    def _ti_yong_analysis(self, gua_info: Dict) -> Dict:
        """动爻所在卦为用卦，另一卦为体卦"""
        dy = gua_info["dong_yao"]
        # 1-3爻为下卦，4-6爻为上卦
        if dy <= 3:
            yong = gua_info["下卦"]
            ti = gua_info["上卦"]
        else:
            yong = gua_info["上卦"]
            ti = gua_info["下卦"]

        ti_wx = self.GUA_WUXING[ti]
        yong_wx = self.GUA_WUXING[yong]

        # 判断五行关系
        if ti_wx == yong_wx:
            rel = "体用比和"
        elif self.WX_SHENG[ti_wx] == yong_wx:
            rel = "体生用"
        elif self.WX_KE[ti_wx] == yong_wx:
            rel = "体克用"
        elif self.WX_BEI_SHENG[ti_wx] == yong_wx:
            rel = "用生体"
        elif self.WX_BEI_KE[ti_wx] == yong_wx:
            rel = "用克体"
        else:
            rel = "体用比和"

        judge = self.TI_YONG_JUDGE.get(rel, {"吉凶":"平","说明":"中性"})

        return {"体卦":ti, "用卦":yong, "体五行":ti_wx, "用五行":yong_wx,
                "关系":rel, "吉凶":judge["吉凶"], "说明":judge["说明"]}

    # ===== 互卦 =====
    def _calculate_hu_gua(self, upper: str, lower: str) -> Dict:
        """互卦: 去初爻和上爻，取2-4爻为下互，3-5爻为上互"""
        hu_upper, hu_lower = self.HU_GUA.get(upper, (upper, lower))
        name = self.LIUSHISI_GUA.get((hu_upper, hu_lower), f"{hu_upper}{hu_lower}卦")
        return {"上":hu_upper, "下":hu_lower, "name":name}

    # ===== 变卦 =====
    def _calculate_bian_gua(self, gua_info: Dict) -> Dict:
        """变卦: 动爻变(阳变阴，阴变阴变阳)"""
        dy = gua_info["dong_yao"]
        upper = gua_info["上卦"]
        lower = gua_info["下卦"]

        # 简化: 动爻所在卦变为其对卦
        # 乾坤互变、震巽互变、坎离互变、艮兑互变
        Dui_GUA = {"乾":"坤","坤":"乾","震":"巽","巽":"震","坎":"离","离":"坎","艮":"兑","兑":"艮"}

        if dy <= 3:
            new_lower = Dui_GUA[lower]
            new_upper = upper
        else:
            new_upper = Dui_GUA[upper]
            new_lower = lower

        name = self.LIUSHISI_GUA.get((new_upper, new_lower), f"{new_upper}{new_lower}卦")
        return {"上":new_upper, "下":new_lower, "name":name}

    # ===== 综合断卦 =====
    def _comprehensive_judge(self, gua, ti_yong, hu_gua, bian_gua, scene) -> Dict:
        """综合四卦五行关系断卦"""
        ti_wx = ti_yong["体五行"]
        result = {"体用":ti_yong["吉凶"], "分析":[]}

        # 互卦与体卦关系
        hu_wx = self.GUA_WUXING[hu_gua["上"]]
        if self.WX_BEI_SHENG[ti_wx] == hu_wx:
            result["分析"].append(f"互卦({hu_gua['name']})生体，中途有助力")
        elif self.WX_BEI_KE[ti_wx] == hu_wx:
            result["分析"].append(f"互卦({hu_gua['name']})克体，中途有阻碍")

        # 变卦与体卦关系
        bian_wx = self.GUA_WUXING[bian_gua["上"]]
        if self.WX_BEI_SHENG[ti_wx] == bian_wx:
            result["分析"].append(f"变卦({bian_gua['name']})生体，结果有利")
        elif self.WX_BEI_KE[ti_wx] == bian_wx:
            result["分析"].append(f"变卦({bian_gua['name']})克体，结局不利")
        elif bian_wx == ti_wx:
            result["分析"].append(f"变卦({bian_gua['name']})与体比和，结局平稳")

        # 综合吉凶
        good = sum(1 for a in result["分析"] if "生体" in a or "有利" in a or "助力" in a)
        bad = sum(1 for a in result["分析"] if "克体" in a or "不利" in a or "阻碍" in a)

        if ti_yong["吉凶"] in ("大吉","吉") and good >= bad:
            result["综合"] = "吉"
        elif ti_yong["吉凶"] in ("大凶","凶") and bad >= good:
            result["综合"] = "凶"
        else:
            result["综合"] = "平"

        return result

    def _calculate_score(self, judgment, scene) -> float:
        base = {"大吉":88,"吉":75,"平":60,"凶":45,"大凶":32}.get(judgment.get("综合","平"), 60)
        good_count = sum(1 for a in judgment.get("分析",[]) if "生体" in a or "有利" in a)
        bad_count = sum(1 for a in judgment.get("分析",[]) if "克体" in a or "不利" in a)
        adjust = (good_count - bad_count) * 4
        sf = {"终身格局":0.95,"年度趋势":1.0,"具体事件":1.05,"性格分析":0.9}.get(scene, 0.95)
        return min(100, max(0, round((base + adjust) * sf, 2)))

    def _risk_from_judgment(self, judgment):
        comp = judgment.get("综合","平")
        if comp in ("大凶","凶"): return "high"
        if comp == "平": return "medium"
        return "low"
