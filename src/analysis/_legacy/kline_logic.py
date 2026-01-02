from enum import Enum

class BarRelationship(Enum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    INSIDE = "INSIDE"
    OUTSIDE = "OUTSIDE"

def classify_k_line_combination(h1, l1, h2, l2):
    """
    根据前一根K线(h1, l1)和当前K线(h2, l2)的关系进行分类。
    这四种情况在数学上是完备的。
    """
    if h2 > h1 and l2 > l1:
        return BarRelationship.TREND_UP
    elif h2 < h1 and l2 < l1:
        return BarRelationship.TREND_DOWN
    elif h2 <= h1 and l2 >= l1:
        return BarRelationship.INSIDE
    else:
        # 此时必然满足 h2 >= h1 且 l2 <= l1 (或者其中一个相等)
        return BarRelationship.OUTSIDE
