"""
命理计算引擎 - 10大体系计算模块
"""

from .base import BaseFortuneSystem, CalculationResult
from .bazi import BaZiSystem
from .ziwei import ZiWeiSystem
from .astrology import AstrologySystem
from .qimen import QiMenSystem
from .liuren import LiuRenSystem
from .liuyao import LiuYaoSystem
from .meihua import MeiHuaSystem
from .numerology import NumerologySystem
from .nameology import NameologySystem
from .qizheng import QiZhengSystem

__all__ = [
    'BaseFortuneSystem',
    'CalculationResult',
    'BaZiSystem',
    'ZiWeiSystem', 
    'AstrologySystem',
    'QiMenSystem',
    'LiuRenSystem',
    'LiuYaoSystem',
    'MeiHuaSystem',
    'NumerologySystem',
    'NameologySystem',
    'QiZhengSystem',
]
