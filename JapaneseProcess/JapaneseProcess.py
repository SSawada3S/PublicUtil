import re
import datetime
import mojimoji

### 文章全体に対する対応 ###

def preprocess_japanese_text(text):
  text = text.strip()
  text = text.replace("　", "").replace(" ", "")
  text = mojimoji.zen_to_han(text, kana=False)  # 全角→半角
  #text = re.sub(r"[^\wぁ-んァ-ン\u4E00-\u9FFF\u3400-\u4DBF\uF900-\uFAFF\U00020000-\U0002FA1F\.]", "", text) # 不要な記号削除
  return text

### 数字に対する対応 ###
# 全角→半角、カンマ除去
_Z2H = str.maketrans({**{chr(ord('０')+i): str(i) for i in range(10)}, '．': '.'})
def _normalize_numstr(s: str) -> str:
    return s.translate(_Z2H).replace(',', '')

# 漢数字（十・百・千対応）
KANJI_DIG = {'零':0,'〇':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
KANJI_UNIT = {'十':10,'百':100,'千':1000}

def _kanji_basic_to_int(s: str) -> int:
    total = 0
    tmp = 0
    has_any = False
    for ch in s:
        if ch in KANJI_DIG:
            tmp += KANJI_DIG[ch]
            has_any = True
        elif ch in KANJI_UNIT:
            tmp = 1 if tmp == 0 else tmp
            total += tmp * KANJI_UNIT[ch]
            tmp = 0
            has_any = True
    total += tmp
    return total if has_any else 0

def _parse_number_token(tok: str) -> float:
    t = _normalize_numstr(tok)
    if re.fullmatch(r"\d+(\.\d+)?", t):
        return float(t)
    return float(_kanji_basic_to_int(tok))

# 倍率テーブル
SCALE_FACTORS = {
    '兆': 10**12,
    '十億': 10**9,
    '億': 10**8,
    '千万': 10**7,
    '百万': 10**6,
    '十万': 10**5,
    '万': 10**4,
    '千': 10**3,
    '百': 10**2,
    '十': 10**1,
}

# 正規表現
# num = 数字または漢数字だけ
NUM_TOKEN = r"[0-9０-９]+(?:[\.．][0-9０-９]+)?|[一二三四五六七八九〇零十百千]+"
SCALE_TOKEN = r"(兆|十億|億|千万|百万|十万|万|千|百|十)?"
UNIT_TOKEN = r"[a-zA-Zぁ-んァ-ン一-龥]+"

AMOUNT_RE = re.compile(rf"(?P<num>{NUM_TOKEN})(?P<scale>{SCALE_TOKEN})(?P<unit>{UNIT_TOKEN})")

def extract_amounts(text: str):
    text=text.replace("．",".")
    results = []
    for m in AMOUNT_RE.finditer(text):
        raw = m.group(0)
        num_tok = m.group("num")
        scale_tok = m.group("scale") or ""
        unit_str = m.group("unit")

        n = _parse_number_token(num_tok)
        factor = SCALE_FACTORS.get(scale_tok, 1)
        results.append((raw, n * factor, unit_str))
    return results


### 年月日に対する対応 ###

# 元号→西暦の起点（元年=1年）
ERA_START = {
    "令和": 2019,
    "平成": 1989,
    "昭和": 1926,
    "大正": 1912,
    "明治": 1868,
}

# 全角数字→半角
_Z2H = str.maketrans({**{chr(ord('０')+i): str(i) for i in range(10)}})

KANJI_DIG = {"零":0,"〇":0,"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9}
KANJI_TEN = "十"

def _to_int_num(token: str) -> int:
    """半角/全角数字 or 漢数字(十含む) を int に。"""
    t = token.translate(_Z2H)
    if re.fullmatch(r"\d+", t):
        return int(t)
    # 漢数字（最大 99 まで想定：十の位のみ）
    total = 0
    cur = 0
    for ch in token:
        if ch in KANJI_DIG:
            cur += KANJI_DIG[ch]
        elif ch == KANJI_TEN:
            cur = 1 if cur == 0 else cur
            total += cur * 10
            cur = 0
        # それ以外は無視
    total += cur
    return total

# 文中対応・全角/漢数字対応（年・月・日すべて）
NUM = r"[0-9０-９〇零一二三四五六七八九十]+"
GREG_PATTERN = re.compile(r"(\d{3,4})年\s*([0-9０-９〇零一二三四五六七八九十]+)月\s*([0-9０-９〇零一二三四五六七八九十]+)日")
ERA_PATTERN  = re.compile(rf"(令和|平成|昭和|大正|明治)(元|{NUM})年\s*({NUM})月\s*({NUM})日")

def extract_dates(text: str):
    """文字列から (一致原文, datetime.date) をすべて返す。"""
    results = []

    # 西暦
    for m in GREG_PATTERN.finditer(text):
        y_str, mo_str, d_str = m.groups()
        y = _to_int_num(y_str)   # 2025 など（全角OK）
        mo = _to_int_num(mo_str)
        d  = _to_int_num(d_str)
        try:
            results.append((m.group(0), datetime.date(y, mo, d)))
        except ValueError:
            pass

    # 和暦
    for m in ERA_PATTERN.finditer(text):
        era, y_str, mo_str, d_str = m.groups()
        y = 1 if y_str == "元" else _to_int_num(y_str)   # 元年→1
        y = ERA_START[era] + y - 1
        mo = _to_int_num(mo_str)
        d  = _to_int_num(d_str)
        try:
            results.append((m.group(0), datetime.date(y, mo, d)))
        except ValueError:
            pass

    return results
