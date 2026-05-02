"""
八字命理计算模块 (子平法) - 深化版
实现: 十神/旺衰/格局/用神/大运/流年/神煞/刑冲合害 完整算法
"""
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from .base import BaseFortuneSystem, CalculationResult


class BaZiSystem(BaseFortuneSystem):
    """八字命理体系 - 子平法完整实现"""

    TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    GAN_WUXING = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}
    ZHI_WUXING = {"子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火","午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}
    GAN_YINYANG = {"甲":"阳","乙":"阴","丙":"阳","丁":"阴","戊":"阳","己":"阴","庚":"阳","辛":"阴","壬":"阳","癸":"阴"}

    # 地支藏干
    ZHI_CANG = {
        "子":["癸"],"丑":["己","癸","辛"],"寅":["甲","丙","戊"],"卯":["乙"],
        "辰":["戊","乙","癸"],"巳":["丙","庚","戊"],"午":["丁","己"],
        "未":["己","丁","乙"],"申":["庚","壬","戊"],"酉":["辛"],
        "戌":["戊","辛","丁"],"亥":["壬","甲"],
    }
    # 藏干权重
    CANG_W = {
        "子":[1.0],"丑":[0.6,0.25,0.15],"寅":[0.6,0.25,0.15],"卯":[1.0],
        "辰":[0.6,0.25,0.15],"巳":[0.6,0.25,0.15],"午":[0.7,0.3],
        "未":[0.6,0.25,0.15],"申":[0.6,0.25,0.15],"酉":[1.0],
        "戌":[0.6,0.25,0.15],"亥":[0.7,0.3],
    }

    # 五行生克
    WX_SHENG = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    WX_KE = {"木":"土","土":"水","水":"火","火":"金","金":"木"}
    WX_BEI_SHENG = {"木":"水","火":"木","土":"火","金":"土","水":"金"}
    WX_BEI_KE = {"木":"金","土":"木","水":"土","火":"水","金":"火"}

    # 十神映射
    SS_MAP = {
        ("同","同"):"比肩",("同","异"):"劫财",("生","同"):"食神",("生","异"):"伤官",
        ("克","同"):"偏财",("克","异"):"正财",("被生","同"):"偏印",("被生","异"):"正印",
        ("被克","同"):"七杀",("被克","异"):"正官",
    }

    # 神煞
    TIANYI = {"甲":["丑","未"],"戊":["丑","未"],"庚":["丑","未"],"乙":["子","申"],"己":["子","申"],
              "丙":["亥","酉"],"丁":["亥","酉"],"壬":["卯","巳"],"癸":["卯","巳"]}
    YIMA = {"申":"寅","子":"寅","辰":"寅","寅":"申","午":"申","戌":"申",
            "巳":"亥","酉":"亥","丑":"亥","亥":"巳","卯":"巳","未":"巳"}
    WENCHANG = {"甲":"巳","乙":"午","丙":"申","丁":"酉","戊":"申","己":"酉","庚":"亥","辛":"子","壬":"寅","癸":"卯"}
    HUAGAI = {"寅":"戌","午":"戌","戌":"戌","巳":"丑","酉":"丑","丑":"丑",
              "申":"辰","子":"辰","辰":"辰","亥":"未","卯":"未","未":"未"}

    # 合冲刑害
    LIUHE = {"子":"丑","丑":"子","寅":"亥","亥":"寅","卯":"戌","戌":"卯",
             "辰":"酉","酉":"辰","巳":"申","申":"巳","午":"未","未":"午"}
    LIUCHONG = {"子":"午","午":"子","丑":"未","未":"丑","寅":"申","申":"寅",
                "卯":"酉","酉":"卯","辰":"戌","戌":"辰","巳":"亥","亥":"巳"}
    SANXING = {"寅":"巳","巳":"申","申":"寅","丑":"戌","戌":"未","未":"丑",
               "子":"卯","卯":"子","酉":"酉","午":"午","辰":"辰","亥":"亥"}
    LIUHAI = {"子":"未","未":"子","丑":"午","午":"丑","寅":"巳","巳":"寅",
              "卯":"辰","辰":"卯","申":"亥","亥":"申","酉":"戌","戌":"酉"}

    # 节气近似日
    JIEQI = {1:(2,4),2:(3,6),3:(4,5),4:(5,6),5:(6,6),6:(7,7),
             7:(8,7),8:(9,8),9:(10,8),10:(11,7),11:(12,7),12:(1,6)}

    GEJU_MAP = {"正官":"正官格","七杀":"七杀格","正印":"正印格","偏印":"偏印格",
                "食神":"食神格","伤官":"伤官格","正财":"正财格","偏财":"偏财格"}

    # 十二长生起点(阳干)
    CS_START = {"木":11,"火":2,"金":4,"水":7,"土":7}
    CS_ORDER = ["长生","沐浴","冠带","临官","帝旺","衰","病","死","墓","绝","胎","养"]

    def __init__(self):
        super().__init__("八字命理", 0.12)

    async def calculate(self, birth_datetime, birth_location, gender, query_scene,
                        query_time=None, **kwargs):
        import time as _t
        t0 = _t.time()

        ck = self._get_cache_key(system=self.name, dt=birth_datetime.isoformat(),
                                  scene=query_scene, query=query_time.isoformat() if query_time else "birth")
        if ck in self._cache:
            r = self._cache[ck]; r.cached = True; return r

        # 真太阳时
        solar = self._true_solar(birth_datetime, birth_location)
        # 四柱
        pillars = self._four_pillars(solar)
        bazi = {"年柱":pillars[0],"月柱":pillars[1],"日柱":pillars[2],"时柱":pillars[3]}
        dm = pillars[2][0]
        dm_wx = self.GAN_WUXING[dm]
        # 十神
        ss = self._shishen_all(bazi, dm)
        # 五行量化
        wx = self._wuxing_quantify(bazi)
        # 旺衰
        ws = self._wangshuai(dm, wx)
        # 格局
        geju = self._geju(bazi, ss, ws)
        # 用神
        ys = self._yongshen(dm_wx, ws, wx)
        # 神煞
        sha = self._shensha(bazi)
        # 刑冲合害
        xc = self._xingchong(bazi)
        # 大运
        dy = self._dayun(bazi, gender, solar)
        # 流年
        ln = self._liunian(dm_wx, ws, ys, query_time)
        # 评分
        score = self._score(ws, wx, geju, ys, sha, xc, ln, query_scene)
        trend_txt = self._trend_text(ws, ln, ys)
        risk_txt = self._risk_text(xc, ln, ws)

        details = {"四柱":bazi,"日主":dm,"日主五行":dm_wx,"旺衰":ws,"十神":ss,
                   "五行量化":wx,"格局":geju,"用神":ys["yongshen"],"喜神":ys["xishen"],
                   "忌神":ys["jishen"],"神煞":sha,"刑冲合害":xc,"大运":dy[:6],
                   "流年分析":ln,"综合趋势":trend_txt}

        result = CalculationResult(system=self.name, score=score,
            confidence=self._confidence(ws, wx), trend=self._score_to_trend(score),
            risk_level=risk_txt, details=details, calculation_time_ms=int((_t.time()-t0)*1000))
        self._cache[ck] = result
        return result

    # ===== 真太阳时 =====
    def _true_solar(self, dt, loc):
        lng = loc.get("longitude", 120.0)
        lng_min = (lng - 120) * 4
        N = dt.timetuple().tm_yday
        B = math.radians(360/365*(N-81))
        eot = 9.87*math.sin(2*B) - 7.53*math.cos(B) - 1.5*math.sin(B)
        return dt + timedelta(minutes=lng_min + eot)

    # ===== 四柱 =====
    def _four_pillars(self, dt):
        yp = self._year_pillar(dt)
        mp = self._month_pillar(dt, yp)
        dp = self._day_pillar(dt)
        hp = self._hour_pillar(dp[0], dt.hour)
        return [yp, mp, dp, hp]

    def _year_pillar(self, dt):
        y = dt.year
        if dt.month == 1 or (dt.month == 2 and dt.day < self.JIEQI[1][1]):
            y -= 1
        off = (y - 1984) % 60
        return (self.TIAN_GAN[off%10], self.DI_ZHI[off%12])

    def _month_pillar(self, dt, yp):
        m = dt.month
        jm, jd = self.JIEQI.get(m, (m, 15))
        if dt.day < jd:
            m -= 1
            if m == 0: m = 12
        zi = (m + 1) % 12
        ygi = self.TIAN_GAN.index(yp[0])
        sg = {0:2,5:2,1:4,6:4,2:6,7:6,3:8,8:8,4:0,9:0}[ygi]
        gi = (sg + m - 1) % 10
        return (self.TIAN_GAN[gi], self.DI_ZHI[zi])

    def _day_pillar(self, dt):
        base = datetime(2000,1,7)
        d = (dt.date() - base.date()).days
        return (self.TIAN_GAN[d%10], self.DI_ZHI[d%12])

    def _hour_pillar(self, dg, hour):
        sc = 0 if hour == 23 else (hour+1)//2 % 12
        dgi = self.TIAN_GAN.index(dg)
        sg = {0:0,5:0,1:2,6:2,2:4,7:4,3:6,8:6,4:8,9:8}[dgi]
        return (self.TIAN_GAN[(sg+sc)%10], self.DI_ZHI[sc])

    # ===== 十神 =====
    def _get_ss(self, dm, tg):
        if dm == tg: return "比肩"
        dw = self.GAN_WUXING[dm]; tw = self.GAN_WUXING[tg]
        dy = self.GAN_YINYANG[dm]; ty = self.GAN_YINYANG[tg]
        if dw == tw: rel = "同"
        elif self.WX_SHENG[dw] == tw: rel = "生"
        elif self.WX_KE[dw] == tw: rel = "克"
        elif self.WX_BEI_SHENG[dw] == tw: rel = "被生"
        elif self.WX_BEI_KE[dw] == tw: rel = "被克"
        else: return "比肩"
        yd = "同" if dy == ty else "异"
        return self.SS_MAP.get((rel, yd), "比肩")

    def _shishen_all(self, bazi, dm):
        r = {}
        for pn, (g, z) in bazi.items():
            r[f"{pn}_干"] = self._get_ss(dm, g)
            r[f"{pn}_支藏"] = [{"干":c,"十神":self._get_ss(dm,c)} for c in self.ZHI_CANG[z]]
        return r

    # ===== 五行量化 =====
    def _wuxing_quantify(self, bazi):
        s = {"金":0.0,"木":0.0,"水":0.0,"火":0.0,"土":0.0}
        for _, (g, z) in bazi.items():
            s[self.GAN_WUXING[g]] += 1.0
            for i, c in enumerate(self.ZHI_CANG[z]):
                s[self.GAN_WUXING[c]] += self.CANG_W[z][i]
        # 月令加成
        mz = bazi["月柱"][1]
        s[self.ZHI_WUXING[mz]] += 1.0
        return s

    # ===== 旺衰 =====
    def _wangshuai(self, dm, wx):
        dw = self.GAN_WUXING[dm]
        self_s = wx[dw]
        sheng = wx[self.WX_BEI_SHENG[dw]]
        wosheng = wx[self.WX_SHENG[dw]]
        kewo = wx[self.WX_BEI_KE[dw]]
        wokewo = wx[self.WX_KE[dw]]
        hp = self_s + sheng; dp = wosheng + kewo + wokewo
        r = hp / max(dp, 0.1)
        if r >= 3.0: lv = "太旺"
        elif r >= 2.0: lv = "偏旺"
        elif r >= 1.2: lv = "中和偏旺"
        elif r >= 0.8: lv = "中和"
        elif r >= 0.5: lv = "中和偏弱"
        elif r >= 0.33: lv = "偏弱"
        else: lv = "太弱"
        return {"level":lv,"助身":round(hp,2),"耗身":round(dp,2),"比值":round(r,2),
                "助身方":f"比劫({self_s:.1f})+印({sheng:.1f})",
                "耗身方":f"食伤({wosheng:.1f})+官杀({kewo:.1f})+财({wokewo:.1f})"}

    # ===== 格局 =====
    def _geju(self, bazi, ss, ws):
        lv = ws["level"]
        if lv == "太旺":
            zw = {"木":"曲直格","火":"炎上格","土":"稼穑格","金":"从革格","水":"润下格"}
            return zw.get(self.GAN_WUXING[bazi["日柱"][0]], "专旺格")
        if lv == "太弱": return "从弱格"
        ms = ss.get("月柱_支藏", [])
        for i in range(min(len(ms), 3)):
            sn = ms[i]["十神"]
            if sn in self.GEJU_MAP: return self.GEJU_MAP[sn]
        return "建禄格" if lv in ["中和偏旺","偏旺"] else "正印格"

    # ===== 用神 =====
    def _yongshen(self, dm_wx, ws, wx):
        lv = ws["level"]
        if lv in ("太旺","偏旺"):
            ys_wx = self.WX_KE[dm_wx]       # 官杀制身
            xs_wx = self.WX_SHENG[dm_wx]     # 食伤泄秀
            js_wx = self.WX_BEI_SHENG[dm_wx] # 印生身(忌)
        elif lv in ("太弱","偏弱","中和偏弱"):
            ys_wx = self.WX_BEI_SHENG[dm_wx] # 印生身
            xs_wx = dm_wx                     # 比劫帮身
            js_wx = self.WX_KE[dm_wx]         # 财耗身(忌)
        else:
            ys_wx = dm_wx                     # 中和取比劫
            xs_wx = self.WX_BEI_SHENG[dm_wx]
            js_wx = self.WX_KE[dm_wx]
        return {"yongshen":ys_wx,"xishen":xs_wx,"jishen":js_wx}

    # ===== 神煞 =====
    def _shensha(self, bazi):
        result = []
        dm = bazi["日柱"][0]
        all_zhi = [z for _, (_, z) in bazi.items()]
        all_gan = [g for _, (g, _) in bazi.items()]
        # 天乙贵人
        for z in self.TIANYI.get(dm, []):
            if z in all_zhi: result.append(f"天乙贵人({z})")
        # 驿马
        nz = bazi["年柱"][1]
        ym = self.YIMA.get(nz, "")
        if ym and ym in all_zhi: result.append(f"驿马({ym})")
        # 文昌
        wc = self.WENCHANG.get(dm, "")
        if wc and wc in all_zhi: result.append(f"文昌({wc})")
        # 华盖
        hg = self.HUAGAI.get(nz, "")
        if hg and hg in all_zhi: result.append(f"华盖({hg})")
        if not result: result.append("无明显吉神")
        return result

    # ===== 刑冲合害 =====
    def _xingchong(self, bazi):
        result = []
        zhis = [z for _, (_, z) in bazi.items()]
        for i in range(len(zhis)):
            for j in range(i+1, len(zhis)):
                a, b = zhis[i], zhis[j]
                if self.LIUCHONG.get(a) == b:
                    result.append(f"{a}{b}冲")
                if self.LIUHE.get(a) == b:
                    result.append(f"{a}{b}合")
                if self.SANXING.get(a) == b:
                    result.append(f"{a}{b}刑")
                if self.LIUHAI.get(a) == b:
                    result.append(f"{a}{b}害")
        return result if result else ["无明显刑冲合害"]

    # ===== 大运 =====
    def _dayun(self, bazi, gender, birth_dt):
        dm = bazi["日柱"][0]
        yy = self.GAN_YINYANG[dm]
        # 阳男阴女顺排，阴男阳女逆排
        forward = (yy == "阳" and gender == "male") or (yy == "阴" and gender != "male")
        mz = bazi["月柱"]
        mgi = self.TIAN_GAN.index(mz[0])
        mzi = self.DI_ZHI.index(mz[1])
        step = 1 if forward else -1
        dy = []
        for i in range(1, 9):
            gi = (mgi + step * i) % 10
            zi = (mzi + step * i) % 12
            dy.append({"大运":f"{self.TIAN_GAN[gi]}{self.DI_ZHI[zi]}",
                        "起运年龄": i * 10, "五行": self.GAN_WUXING[self.TIAN_GAN[gi]]})
        return dy

    # ===== 流年 =====
    def _liunian(self, dm_wx, ws, ys, query_time):
        year = (query_time or datetime.now()).year
        result = []
        for offset in range(-1, 2):
            y = year + offset
            off = (y - 1984) % 60
            gz = f"{self.TIAN_GAN[off%10]}{self.DI_ZHI[off%12]}"
            # 流年天干与日主关系
            fg = self.TIAN_GAN[off%10]
            fz = self.DI_ZHI[off%12]
            fg_wx = self.GAN_WUXING[fg]
            # 判断吉凶
            if fg_wx == ys["yongshen"]:
                luck = "吉"
            elif fg_wx == ys["jishen"]:
                luck = "凶"
            else:
                luck = "平"
            result.append({"年份":y,"干支":gz,"五行":fg_wx,"吉凶":luck,
                           "说明":f"流年{gz}，天干{fg_wx}，{'用神到位' if luck=='吉' else '忌神当值' if luck=='凶' else '中性流年'}"})
        return result

    # ===== 评分 =====
    def _score(self, ws, wx, geju, ys, sha, xc, ln, scene):
        lv = ws["level"]
        # 基础分(中和最吉)
        base = {"中和":72,"中和偏旺":68,"中和偏弱":66,"偏旺":60,"偏弱":58,"太旺":45,"太弱":42}.get(lv, 60)
        # 五行平衡度
        vals = list(wx.values())
        avg = sum(vals) / 5
        var = sum((v-avg)**2 for v in vals) / 5
        balance = max(0, 15 - var * 3)
        # 神煞加成
        sha_bonus = len([s for s in sha if "天乙" in s]) * 5 + len([s for s in sha if "文昌" in s]) * 3
        # 刑冲扣分
        xc_pen = len([x for x in xc if "冲" in x]) * 5 + len([x for x in xc if "刑" in x]) * 3
        # 流年加成
        cur_ln = [l for l in ln if l.get("年份") == (datetime.now().year)]
        ln_bonus = 0
        if cur_ln and cur_ln[0]["吉凶"] == "吉": ln_bonus = 8
        elif cur_ln and cur_ln[0]["吉凶"] == "凶": ln_bonus = -8
        # 场景系数
        sf = {"终身格局":1.0,"年度趋势":0.95,"具体事件":0.85,"性格分析":0.9}.get(scene, 0.9)
        return min(100, max(0, round((base + balance + sha_bonus - xc_pen + ln_bonus) * sf, 2)))

    def _trend_text(self, ws, ln, ys):
        cur = [l for l in ln if l.get("吉凶")]
        if cur and cur[0]["吉凶"] == "吉": return "流年用神到位，整体向好"
        if cur and cur[0]["吉凶"] == "凶": return "流年忌神当值，需谨慎"
        return "运势平稳，守成为主"

    def _risk_text(self, xc, ln, ws):
        chong = [x for x in xc if "冲" in x]
        bad_ln = [l for l in ln if l.get("吉凶") == "凶"]
        if len(chong) >= 2 or len(bad_ln) >= 2: return "high"
        if chong or bad_ln: return "medium"
        if ws["level"] in ("太旺","太弱"): return "medium"
        return "low"

    def _confidence(self, ws, wx):
        base = 0.85
        if ws["level"] == "中和": base += 0.05
        elif ws["level"] in ("太旺","太弱"): base -= 0.1
        vals = list(wx.values())
        if min(vals) > 0: base += 0.03
        return min(0.95, max(0.65, round(base, 2)))
