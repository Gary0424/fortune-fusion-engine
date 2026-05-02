"""
六爻纳甲计算模块 - 深化版
实现: 时间起卦/纳甲配卦/六亲配置/世应定位/用神选取/日月建分析
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from .base import BaseFortuneSystem, CalculationResult


class LiuYaoSystem(BaseFortuneSystem):
    """六爻纳甲 - 完整排盘断卦"""

    # 八卦
    BA_GUA = ["乾","兑","离","震","巽","坎","艮","坤"]

    # 先天数
    XIAN_TIAN = {"乾":1,"兑":2,"离":3,"震":4,"巽":5,"坎":6,"艮":7,"坤":8}
    XIAN_TIAN_REV = {1:"乾",2:"兑",3:"离",4:"震",5:"巽",6:"坎",7:"艮",8:"坤"}

    # 八卦五行
    GUA_WX = {"乾":"金","兑":"金","离":"火","震":"木","巽":"木","坎":"水","艮":"土","坤":"土"}

    # 对卦(变卦用)
    DUI_GUA = {"乾":"坤","坤":"乾","震":"巽","巽":"震","坎":"离","离":"坎","艮":"兑","兑":"艮"}

    # 纳甲表: 八卦 → 六爻天干地支 (从初爻到上爻)
    # 乾纳甲壬, 坤纳乙癸, 震纳庚, 巽纳辛, 坎纳戊, 离纳己, 艮纳丙, 兑纳丁
    NAJIA = {
        "乾": ["壬戌","壬申","壬午","甲辰","甲寅","甲子"],  # 从初爻到上爻
        "坤": ["乙未","乙巳","乙卯","癸丑","癸亥","癸酉"],
        "震": ["庚子","庚寅","庚辰","庚午","庚申","庚戌"],
        "巽": ["辛丑","辛亥","辛酉","辛未","辛巳","辛卯"],
        "坎": ["戊寅","戊辰","戊午","戊申","戊戌","戊子"],
        "离": ["己卯","己丑","己亥","己酉","己未","己巳"],
        "艮": ["丙辰","丙午","丙申","丙戌","丙子","丙寅"],
        "兑": ["丁巳","丁卯","丁丑","丁亥","丁酉","丁未"],
    }

    # 世应表: 八宫卦序 → 世爻/应爻位置 (1-6, 从初爻起)
    SHI_YING = {
        0: (6, 3),  # 本宫卦: 世六应三
        1: (1, 4),  # 一世卦: 世初应四
        2: (2, 5),  # 二世卦: 世二应五
        3: (3, 6),  # 三世卦: 世三应六
        4: (4, 1),  # 四世卦: 世四应初
        5: (5, 2),  # 五世卦: 世五应二
        6: (4, 1),  # 游魂卦: 世四应初
        7: (3, 6),  # 归魂卦: 世三应六
    }

    # 八宫归属 (本宫卦)
    BA_GONG = {
        "乾为天":"乾","坤为地":"坤","震为雷":"震","巽为风":"巽",
        "坎为水":"坎","离为火":"离","艮为山":"艮","兑为泽":"兑",
    }

    # 六十四卦纳甲 (上卦+下卦 → 卦名+宫)
    GUA_TABLE = {
        ("乾","乾"):("乾为天","乾",0),("坤","坤"):("坤为地","坤",0),
        ("震","震"):("震为雷","震",0),("巽","巽"):("巽为风","巽",0),
        ("坎","坎"):("坎为水","坎",0),("离","离"):("离为火","离",0),
        ("艮","艮"):("艮为山","艮",0),("兑","兑"):("兑为泽","兑",0),
        ("乾","坎"):("天水讼","乾",3),("坎","乾"):("水天需","坎",3),
        ("乾","震"):("天雷无妄","乾",4),("震","乾"):("雷天大壮","震",4),
        ("乾","巽"):("天风姤","乾",1),("巽","乾"):("风天小畜","巽",1),
        ("乾","坤"):("天地否","乾",5),("坤","乾"):("地天泰","坤",5),
        ("坤","坎"):("地水师","坤",3),("坎","坤"):("水地比","坎",3),
        ("坤","震"):("地雷复","坤",4),("震","坤"):("雷地豫","震",4),
        ("坤","巽"):("地风升","坤",2),("巽","坤"):("风地观","巽",2),
        ("坎","震"):("水雷屯","坎",1),("震","坎"):("雷水解","震",2),
        ("坎","巽"):("水风井","坎",4),("巽","坎"):("风水涣","巽",4),
        ("离","震"):("火雷噬嗑","离",2),("震","离"):("雷火丰","震",5),
        ("离","巽"):("火风鼎","离",3),("巽","离"):("风火家人","巽",3),
        ("离","乾"):("火天大有","离",5),("乾","离"):("天火同人","乾",5),
        ("离","坤"):("火地晋","离",4),("坤","离"):("地火明夷","坤",4),
        ("艮","震"):("山雷颐","艮",5),("震","艮"):("雷山小过","震",5),
        ("兑","巽"):("泽风大过","兑",5),("巽","兑"):("风泽中孚","巽",5),
        ("艮","坎"):("山水蒙","艮",1),("坎","艮"):("水山蹇","坎",2),
        ("兑","坎"):("泽水困","兑",2),("坎","兑"):("水泽节","坎",5),
        ("艮","乾"):("山天大畜","艮",2),("乾","艮"):("天山遁","乾",2),
        ("兑","乾"):("泽天夬","兑",5),("乾","兑"):("天泽履","乾",5),
        ("艮","坤"):("山地剥","艮",5),("坤","艮"):("地山谦","坤",5),
        ("兑","坤"):("泽地萃","兑",2),("坤","兑"):("地泽临","坤",2),
        ("艮","巽"):("山风蛊","艮",3),("巽","艮"):("风山渐","巽",3),
        ("兑","离"):("泽火革","兑",3),("离","兑"):("火泽睽","离",3),
        ("艮","离"):("山火贲","艮",4),("离","艮"):("火山旅","离",4),
        ("兑","震"):("泽雷随","兑",3),("震","兑"):("雷泽归妹","震",3),
        ("坎","离"):("水火既济","坎",5),("离","坎"):("火水未济","离",5),
        ("艮","兑"):("山泽损","艮",4),("兑","艮"):("泽山咸","兑",4),
    }

    # 天干五行
    GAN_WX = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}
    # 地支五行
    ZHI_WX = {"子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火","午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}

    # 五行生克
    WX_SHENG = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    WX_KE = {"木":"土","土":"水","水":"火","火":"金","金":"木"}

    # 六亲表: 以本宫五行为我, 判断其他五行 → 六亲
    LIUQIN = {
        "同":"兄弟","生我":"父母","我生":"子孙","克我":"官鬼","我克":"妻财"
    }

    def __init__(self):
        super().__init__("六爻纳甲", 0.04)

    def _get_liuqin(self, wo_wx: str, ta_wx: str) -> str:
        if wo_wx == ta_wx: return "兄弟"
        if self.WX_SHENG[ta_wx] == wo_wx: return "父母"  # 生我
        if self.WX_SHENG[wo_wx] == ta_wx: return "子孙"  # 我生
        if self.WX_KE[ta_wx] == wo_wx: return "官鬼"     # 克我
        if self.WX_KE[wo_wx] == ta_wx: return "妻财"     # 我克
        return "兄弟"

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
        upper, lower = gua_info["上卦"], gua_info["下卦"]

        # 2. 查卦表
        gname, gong, gseq = self.GUA_TABLE.get((upper, lower), (f"{upper}{lower}卦", upper, 0))
        gong_wx = self.GUA_WX[gong]

        # 3. 配纳甲
        yao_list = self._assign_najia(upper, lower, gong_wx)

        # 4. 定世应
        shi, ying = self.SHI_YING.get(gseq, (3, 6))
        for i, y in enumerate(yao_list):
            y["世应"] = "世" if (i+1) == shi else ("应" if (i+1) == ying else "")

        # 5. 动爻
        dong_yao = gua_info["dong_yao"]
        if 1 <= dong_yao <= 6:
            yao_list[dong_yao-1]["动"] = True

        # 6. 变卦纳甲
        bian_gua = self._bian_gua(upper, lower, dong_yao, gong_wx)

        # 7. 日月建
        rizhu, yuezhu = self._get_rizhu_yuezhu(qt)

        # 8. 断卦分析
        judgment = self._judge(yao_list, gong_wx, rizhu, yuezhu, query_scene)

        # 9. 评分
        score = self._score(judgment, query_scene)

        details = {
            "起卦时间": qt.strftime("%Y-%m-%d %H:%M"),
            "本卦": gname, "宫": gong, "宫序": gseq,
            "上卦": upper, "下卦": lower, "动爻": dong_yao,
            "六爻": yao_list, "世爻": shi, "应爻": ying,
            "变卦": bian_gua,
            "日建": rizhu, "月建": yuezhu,
            "断卦": judgment,
        }

        # 数据质量标记
        details["_has_minute"] = birth_datetime.minute != 0
        details["_has_location"] = birth_location is not None
        
        # 六爻特有确定性评估
        yongshen_state = judgment.get("用神状态", "")
        if yongshen_state in ("旺", "衰"): details["_certainty_bonus"] = 0.08
        elif yongshen_state == "平": details["_certainty_bonus"] = 0.02
        else: details["_certainty_bonus"] = 0.0
        
        if judgment.get("六亲完整"): details["_certainty_bonus"] = details.get("_certainty_bonus", 0) + 0.04
        
        # 计算动态置信度
        confidence = self._calc_confidence(details, query_scene)
        
        result = CalculationResult(system=self.name, score=score,
            confidence=confidence, trend=self._score_to_trend(score),
            risk_level=judgment.get("风险","medium"),
            details=details, calculation_time_ms=int((_t.time()-t0)*1000))
        self._cache[ck] = result
        return result
    
    def _assess_certainty(self, result_data: Dict) -> float:
        return result_data.get("_certainty_bonus", 0.0)
    
    def _scene_fitness(self, scene: str) -> float:
        if scene == "具体事件": return 0.05
        elif scene == "月度趋势": return 0.03
        return 0.0

    def _time_qigua(self, dt):
        y, m, d, h = dt.year, dt.month, dt.day, dt.hour
        shi = (h // 2 + 1) % 12 or 12
        u = (y + m + d) % 8 or 8
        l = (y + m + d + shi) % 8 or 8
        dy = (y + m + d + shi) % 6 or 6
        return {"上卦":self.XIAN_TIAN_REV[u], "下卦":self.XIAN_TIAN_REV[l], "dong_yao":dy}

    def _assign_najia(self, upper, lower, gong_wx):
        upper_nj = self.NAJIA.get(upper, [])
        lower_nj = self.NAJIA.get(lower, [])
        yao_list = []
        for i in range(6):
            if i < 3:
                nj = lower_nj[i] if i < len(lower_nj) else "甲子"
                gua = lower
            else:
                nj = upper_nj[i-3] if i-3 < len(upper_nj) else "甲子"
                gua = upper
            # 提取干支五行
            if len(nj) >= 2:
                zhi = nj[1:]
                zhi_wx = self.ZHI_WX.get(zhi, "土")
                liuqin = self._get_liuqin(gong_wx, zhi_wx)
            else:
                zhi = nj; zhi_wx = "土"; liuqin = "兄弟"
            yao_list.append({
                "爻位": i+1, "纳甲": nj, "地支": zhi, "地支五行": zhi_wx,
                "六亲": liuqin, "所属卦": gua, "世应": "", "动": False
            })
        return yao_list

    def _bian_gua(self, upper, lower, dong_yao, gong_wx):
        if 1 <= dong_yao <= 3:
            new_lower = self.DUI_GUA[lower]
            new_upper = upper
        elif 4 <= dong_yao <= 6:
            new_upper = self.DUI_GUA[upper]
            new_lower = lower
        else:
            return {"name":"无变卦","六爻":[]}
        gname, gong, gseq = self.GUA_TABLE.get((new_upper, new_lower), (f"{new_upper}{new_lower}卦", new_upper, 0))
        yao = self._assign_najia(new_upper, new_lower, gong_wx)
        return {"name":gname, "上":new_upper, "下":new_lower, "六爻":yao}

    def _get_rizhu_yuezhu(self, dt):
        TIAN_GAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
        DI_ZHI = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
        base = datetime(2000,1,7)
        d = (dt.date() - base.date()).days
        ri = TIAN_GAN[d%10] + DI_ZHI[d%12]
        m_off = (dt.year - 1984) * 12 + dt.month
        yue = TIAN_GAN[(m_off+2)%10] + DI_ZHI[(dt.month+1)%12]
        return ri, yue

    def _judge(self, yao_list, gong_wx, rizhu, yuezhu, scene):
        result = {"分析":[]}
        # 找用神(根据场景)
        yongshen_map = {"终身格局":"父母","年度趋势":"官鬼","具体事件":"妻财","性格分析":"兄弟"}
        yongshen = yongshen_map.get(scene, "官鬼")

        # 用神爻
        yong_yao = [y for y in yao_list if y["六亲"] == yongshen]
        if yong_yao:
            result["用神"] = f"{yongshen}爻({yong_yao[0]['纳甲']})"
            # 用神是否持世
            shi_yao = [y for y in yao_list if y["世应"] == "世"]
            if shi_yao and shi_yao[0]["六亲"] == yongshen:
                result["分析"].append("用神持世，事在人为，成功率较高")
            else:
                result["分析"].append(f"用神({yongshen})不持世，需借助外力")
        else:
            result["用神"] = f"{yongshen}(卦中不现)"
            result["分析"].append(f"用神不现，力量不足")

        # 日建月建对用神的影响
        rz_wx = self.ZHI_WX.get(rizhu[1:] if len(rizhu)>1 else rizhu, "土")
        yz_wx = self.ZHI_WX.get(yuezhu[1:] if len(yuezhu)>1 else yuezhu, "土")

        yong_wx_list = [self.WX_SHENG.get(gong_wx)] if yongshen == "子孙" else []
        for y in yong_yao:
            ywx = y["地支五行"]
            if self.WX_SHENG[rz_wx] == ywx or self.WX_SHENG[yz_wx] == ywx:
                result["分析"].append("用神得日月建之生，力量增强")
            elif self.WX_KE[rz_wx] == ywx or self.WX_KE[yz_wx] == ywx:
                result["分析"].append("用神受日月建之克，力量减弱")

        # 动爻
        dong = [y for y in yao_list if y.get("动")]
        if dong:
            dy = dong[0]
            result["分析"].append(f"动爻在{dy['爻位']}爻({dy['纳甲']}，{dy['六亲']})")
            if dy["六亲"] == yongshen:
                result["分析"].append("用神发动，事情有变动力")
            elif self.WX_KE[self.ZHI_WX.get(dy["地支"],"土")] == gong_wx:
                result["分析"].append("动爻克世，有不利变动")

        # 综合判断
        good = sum(1 for a in result["分析"] if "增强" in a or "较高" in a or "发动" in a)
        bad = sum(1 for a in result["分析"] if "减弱" in a or "不现" in a or "不利" in a)
        if good > bad: result["综合"] = "吉"
        elif bad > good: result["综合"] = "凶"
        else: result["综合"] = "平"
        result["风险"] = "low" if result["综合"]=="吉" else "high" if result["综合"]=="凶" else "medium"
        return result

    def _score(self, judgment, scene):
        base = {"吉":76,"平":60,"凶":42}.get(judgment.get("综合","平"), 60)
        good = sum(1 for a in judgment.get("分析",[]) if "增强" in a or "较高" in a)
        bad = sum(1 for a in judgment.get("分析",[]) if "减弱" in a or "不利" in a)
        sf = {"终身格局":0.95,"具体事件":1.05,"年度趋势":1.0}.get(scene, 0.95)
        return min(100, max(0, round((base + (good-bad)*5) * sf, 2)))
