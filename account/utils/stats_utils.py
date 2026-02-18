# account/utils/stats_utils.py
"""
utils：汎用関数置き場（views/servicesのどこからでも使える）
- stats_utils：回帰/パーセンタイル/ゾーン判定などの小物関数
"""

def linear_regression(points: list[tuple[float, float]]):
    """
    points: [(x, y), ...]
    return: (slope, intercept)
    """
    n = len(points)
    if n < 2:
        return None, None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    x_mean = sum(xs) / n
    y_mean = sum(ys) / n

    denom = sum((x - x_mean) ** 2 for x in xs)
    if denom == 0:
        return None, None

    num = sum((x - x_mean) * (y - y_mean) for x, y in points)
    slope = num / denom
    intercept = y_mean - slope * x_mean
    return slope, intercept

def percentile(values: list[int], p: float) -> int:
    """
    p: 0.0〜1.0
    線形補間のパーセンタイル（ざっくりで十分）
    """
    if not values:
        return 0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * p
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return xs[f]
    d = k - f
    return int(round(xs[f] + (xs[c] - xs[f]) * d))

def zone_label(cur: int, med: int, p75: int) -> str:
    if cur <= med:
        return "安定ゾーン"
    if cur <= p75:
        return "高めゾーン"
    return "負担感あり"
