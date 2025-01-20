import re

def is_number(s):
    # 匹配整数或浮点数（包括正负数）
    pattern = r"^-?\d+(\.\d+)?$"
    return bool(re.match(pattern, s))