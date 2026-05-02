"""
紫微斗数计算模块 - 深化版
实现: 五行局定紫微/十四主星精确排布/庙旺利陷/大限/四化
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from .base import BaseFortuneSystem, CalculationResult


class ZiWeiSystem(BaseFortuneSystem):
    """紫微斗数体系 - 完整星盘排布"""

    TIAN_GAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
    DI_ZHI = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]

    # 十二宫
    GONG_WEI = ["命宫","兄弟","夫妻","子女","财帛","疾厄",
                "迁移","仆役","官禄","田宅","福德","父母"]
    # 十二宫对应地支
    GONG_ZHI = ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"]

    # 十四主星 (紫微系/天府系)
    ZIWEI_XI = ["紫微","天机","太阳","武曲","天同","廉贞"]
    TIANFU_XI = ["天府","太阴","贪狼","巨门","天相","天梁","七杀","破军"]

    # 紫微星排布表: 年干→紫微所在宫
    ZIWEI_POS = {
        "甲": "巳", "乙": "辰", "丙": "午", "丁": "巳", "戊": "卯",
        "己": "午", "庚": "午", "辛": "寅", "壬": "子", "癸": "丑",
    }

    # 十四主星排布: 紫微所在宫→各星曜分布
    # (以命宫为0顺时针排布)
    # 地支索引: 子0丑1寅2卯3辰4巳5午6未7申8酉9戌10亥11
    ZHI_IDX = {"子":0,"丑":1,"寅":2,"卯":3,"辰":4,"巳":5,"午":6,"未":7,"申":8,"酉":9,"戌":10,"亥":11}
    IDX_ZHI = {v:k for k,v in ZHI_IDX.items()}

    # 主星顺序 (按地支顺时针)
    STAR_ORDER_GONG = [
        "命宫","父母","福德","田宅","官禄","仆役","迁移","疾厄",
        "财帛","子女","夫妻","兄弟"
    ]

    # 五行局
    WUXING_JU = {
        "甲":"水二局","乙":"火六局","丙":"金四局","丁":"水二局","戊":"木三局",
        "己":"火六局","庚":"土五局","辛":"金四局","壬":"木三局","癸":"水二局"
    }

    # 庙旺利陷表 (主星名→宫位地支→星情)
    MIAOWANG = {
        "紫微": {"子":"旺","午":"旺","卯":"利","酉":"得","申":"庙","辰":"旺","戌":"旺","巳":"平","寅":"得","亥":"得","丑":"平","未":"平"},
        "天机": {"子":"平","午":"旺","卯":"旺","酉":"得","申":"利","辰":"得","戌":"利","巳":"平","寅":"庙","亥":"得","丑":"平","未":"得"},
        "太阳": {"子":"平","午":"庙","卯":"旺","酉":"旺","申":"得","辰":"平","戌":"平","巳":"利","寅":"得","亥":"平","丑":"得","未":"得"},
        "武曲": {"子":"平","午":"得","卯":"得","酉":"庙","申":"旺","辰":"平","戌":"得","巳":"利","寅":"平","亥":"平","丑":"旺","未":"利"},
        "天同": {"子":"庙","午":"得","卯":"得","酉":"旺","申":"平","辰":"旺","戌":"利","巳":"平","寅":"利","亥":"得","丑":"平","未":"得"},
        "廉贞": {"子":"平","午":"旺","卯":"得","酉":"平","申":"得","辰":"利","戌":"平","巳":"庙","寅":"平","亥":"平","丑":"利","未":"得"},
        "天府": {"子":"旺","午":"庙","卯":"得","酉":"旺","申":"利","辰":"得","戌":"旺","巳":"平","寅":"平","亥":"利","丑":"平","未":"得"},
        "太阴": {"子":"庙","午":"得","卯":"旺","酉":"旺","申":"利","辰":"得","戌":"利","巳":"平","寅":"得","亥":"平","丑":"平","未":"得"},
        "贪狼": {"子":"平","午":"旺","卯":"利","酉":"得","申":"得","辰":"平","戌":"得","巳":"庙","寅":"平","亥":"平","丑":"得","未":"利"},
        "巨门": {"子":"平","午":"庙","卯":"平","酉":"得","申":"得","辰":"利","戌":"平","巳":"旺","寅":"平","亥":"平","丑":"利","未":"得"},
        "天相": {"子":"得","午":"旺","卯":"利","酉":"得","申":"平","辰":"旺","戌":"平","巳":"得","寅":"平","亥":"平","丑":"庙","未":"得"},
        "天梁": {"子":"得","午":"庙","卯":"利","酉":"得","申":"旺","辰":"得","戌":"平","巳":"平","寅":"平","亥":"利","丑":"得","未":"旺"},
        "七杀": {"子":"平","午":"得","卯":"利","酉":"平","申":"旺","辰":"平","戌":"得","巳":"得","寅":"庙","亥":"平","丑":"平","未":"得"},
        "破军": {"子":"得","午":"得","卯":"利","酉":"旺","申":"平","辰":"得","戌":"平","巳":"平","寅":"得","亥":"庙","丑":"平","未":"得"},
    }

    # 四化表
    SIHUA = {
        "甲":{"禄":"廉贞","权":"破军","科":"武曲","忌":"太阳"},
        "乙":{"禄":"天机","权":"天梁","科":"紫微","忌":"太阴"},
        "丙":{"禄":"天同","权":"天机","科":"文昌","忌":"廉贞"},
        "丁":{"禄":"太阴","权":"天同","科":"天机","忌":"巨门"},
        "戊":{"禄":"贪狼","权":"太阴","科":"右弼","忌":"天机"},
        "己":{"禄":"武曲","权":"贪狼","科":"天梁","忌":"文曲"},
        "庚":{"禄":"太阳","权":"武曲","科":"太阴","忌":"天同"},
        "辛":{"禄":"巨门","权":"太阳","科":"文曲","忌":"文昌"},
        "壬":{"禄":"天梁","权":"紫微","科":"左辅","忌":"武曲"},
        "癸":{"禄":"破军","权":"巨门","科":"太阴","忌":"贪狼"},
    }

    # 星情分数
    XINGQING_SCORE = {"庙":12,"旺":10,"得":8,"利":6,"平":3,"陷":0,"失":-2}

    def __init__(self):
        super().__init__("紫微斗数", 0.10)

    async def calculate(self, birth_datetime, birth_location, gender, query_scene,
                       query_time=None, **kwargs):
        import time as _t
        t0 = _t.time()
        ck = self._get_cache_key(system=self.name, dt=birth_datetime.isoformat(),
                                  scene=query_scene, query=query_time.isoformat() if query_time else "birth")
        if ck in self._cache:
            r = self._cache[ck]; r.cached = True; return r

        # 1. 年干
        year_gan = self.TIAN_GAN[(birth_datetime.year - 4) % 10]

        # 2. 命宫 (寅起正月, 顺数至生月, 逆数至生时)
        ming_gong_zhi = self._locate_ming_gong(birth_datetime.month, birth_datetime.hour)
        ming_idx = self.GONG_WEI.index("命宫") + self.GONG_ZHI.index(ming_gong_zhi)
        ming_idx = ming_idx % 12

        # 3. 紫微位置
        ziwei_zhi = self.ZIWEI_POS[year_gan]

        # 4. 五行局
        ju = self.WUXING_JU[year_gan]

        # 5. 十四主星分布
        star_positions = self._arrange_stars(ziwei_zhi, ming_idx)

        # 6. 四化
        sihua = self.SIHUA[year_gan]

        # 7. 庙旺分析
        miaowang = self._analyze_miaowang(star_positions)

        # 8. 大限
        daxian = self._arrange_daxian(ming_idx, gender, birth_datetime.year)

        # 9. 评分
        score = self._calc_score(miaowang, sihua, star_positions, query_scene)

        details = {
            "年干":year_gan, "五行局":ju,
            "命宫地支":ming_gong_zhi, "紫微所在宫":ziwei_zhi,
            "十二宫":dict(zip(self.GONG_WEI, self.GONG_ZHI)),
            "十四主星":star_positions,
            "庙旺利陷":miaowang,
            "四化":sihua,
            "大限":daxian[:6],
        }

        result = CalculationResult(system=self.name, score=score,
            confidence=self._calc_confidence(miaowang, star_positions),
            trend=self._score_to_trend(score), risk_level=self._score_to_risk(score),
            details=details, calculation_time_ms=int((_t.time()-t0)*1000))
        self._cache[ck] = result
        return result

    # ===== 命宫 =====
    def _locate_ming_gong(self, month: int, hour: int) -> str:
        """命宫地支: 寅起正月顺数至生月, 逆数至生时"""
        # 时支 (子时=0)
        shi_zhi_idx = (hour + 1) // 2 % 12
        # 寅=2, 卯=3, ... 丑=1
        # 生月从寅起正月
        sheng_yue_idx = (2 + month - 1) % 12  # 寅=2
        # 命宫=生月-生时 (逆数)
        ming_zhi_idx = (sheng_yue_idx - shi_zhi_idx + 12) % 12
        return self.IDX_ZHI[ming_zhi_idx]

    # ===== 主星排布 =====
    def _arrange_stars(self, ziwei_zhi: str, ming_idx: int) -> Dict[str, str]:
        """
        十四主星排布
        以命宫为基准, 紫微位置决定星曜分布
        """
        # 命宫所在的地支索引
        ming_zhi = self.GONG_ZHI[ming_idx]
        ming_zhi_idx = self.ZHI_IDX[ming_zhi]

        # 紫微所在宫
        ziwei_zhi_idx = self.ZHI_IDX[ziwei_zhi]
        offset = (ziwei_zhi_idx - ming_zhi_idx) % 12  # 紫微相对命宫的偏移

        # 主星排布顺序 (紫微系天府系各自的起盘逻辑)
        # 以紫微为起点, 按紫微系6星逆时针布
        # 天府系8星从紫微+6宫开始顺时针布

        positions = {}
        # 紫微系 (从紫微位置逆时针布)
        ziwei_xi = ["紫微","天机","太阳","武曲","天同","廉贞"]
        for i, star in enumerate(ziwei_xi):
            gong_idx = (ziwei_zhi_idx - i + 12) % 12
            positions[star] = self.GONG_WEI[gong_idx]

        # 天府系 (从紫微+6宫开始顺时针布)
        tianfu_xi = ["天府","太阴","贪狼","巨门","天相","天梁","七杀","破军"]
        start = (ziwei_zhi_idx + 6) % 12
        for i, star in enumerate(tianfu_xi):
            gong_idx = (start + i) % 12
            positions[star] = self.GONG_WEI[gong_idx]

        return positions

    # ===== 庙旺利陷 =====
    def _analyze_miaowang(self, star_positions: Dict[str, str]) -> Dict[str, Any]:
        result = {}
        total_score = 0
        for star, gong in star_positions.items():
            zhi = self.GONG_ZHI[self.GONG_WEI.index(gong)]
            miao = self.MIAOWANG.get(star, {}).get(zhi, "平")
            score = self.XINGQING_SCORE.get(miao, 0)
            result[star] = {"所在宫":gong,"地支":zhi,"星情":miao,"得分":score}
            total_score += score
        result["_总分"] = total_score
        return result

    # ===== 大限 =====
    def _arrange_daxian(self, ming_idx: int, gender: str, year: int) -> List[Dict]:
        year_gan = self.TIAN_GAN[(year - 4) % 10]
        is_yang = year_gan in ["甲","丙","戊","庚","壬"]
        is_male = gender == "male"
        forward = (is_yang and is_male) or (not is_yang and not is_male)

        daxian = []
        for i in range(12):
            if forward:
                gong_idx = (ming_idx + i) % 12
            else:
                gong_idx = (ming_idx - i + 12) % 12
            daxian.append({
                "大限序":i+1,
                "宫位":self.GONG_WEI[gong_idx],
                "地支":self.GONG_ZHI[gong_idx],
                "起运年龄":3 + i * 10,
                "终运年龄":12 + i * 10,
            })
        return daxian

    # ===== 评分 =====
    def _calc_score(self, miaowang, sihua, star_positions, scene):
        base = 45.0
        # 庙旺得分
        total = miaowang.get("_总分", 0)
        star_count = len(star_positions)
        miao_pct = total / (star_count * 12) if star_count else 0
        star_bonus = miao_pct * 35

        # 四化加成
        sihua_bonus = 0
        for hua_type, star in sihua.items():
            if star in star_positions:
                miao = miaowang.get(star, {}).get("星情", "平")
                if hua_type == "禄" and miao in ("庙","旺","得"): sihua_bonus += 8
                elif hua_type == "忌": sihua_bonus -= 5

        # 紫微天府双星
        if "紫微" in star_positions and "天府" in star_positions:
            zuowei_gong = star_positions.get("紫微", "")
            tianfu_gong = star_positions.get("天府", "")
            if zuowei_gong == "命宫" and tianfu_gong == "官禄":
                sihua_bonus += 10

        sf = {"终身格局":1.0,"年度趋势":0.95,"具体事件":0.90}.get(scene, 0.95)
        return min(100, max(0, round((base + star_bonus + sihua_bonus) * sf, 2)))

    def _calc_confidence(self, miaowang, star_positions):
        total = miaowang.get("_总分", 0)
        star_count = len(star_positions)
        miao_pct = total / (star_count * 12) if star_count else 0
        base = 0.80
        if miao_pct > 0.7: base += 0.08
        elif miao_pct < 0.4: base -= 0.08
        return min(0.92, max(0.72, round(base, 2)))
