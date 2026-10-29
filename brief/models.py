from dataclasses import dataclass, field


@dataclass
class RawItem:
    title: str
    source: str
    zone: str            # news | style
    rank: int = 1        # 1 = 該來源榜首
    url: str = ""
    traffic: int = 0     # 已知的搜尋量級（Google Trends 級距），未知為 0
    weight: float = 1.0  # 來源權重（含每週回饋調整）


@dataclass
class Hotspot:
    id: str
    topic: str
    zone: str
    sources: list = field(default_factory=list)
    titles: list = field(default_factory=list)
    score: float = 0.0
    traffic: int = 0
    growth: str = "stable"      # new | rising | stable
    analysis: dict = field(default_factory=dict)
