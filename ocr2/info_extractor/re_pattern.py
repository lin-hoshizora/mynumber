"""Regex patterns for information extraction"""
import regex as re

def re_compile(patterns):
  if isinstance(patterns, str):
    return re.compile(patterns)
  if isinstance(patterns, list):
    return list(map(re.compile, patterns))
  if isinstance(patterns, dict):
    return {k: re_compile(v) for k, v in patterns.items()}
  raise TypeError(f"Unexpected type of patterns: {type(patterns)}")

BIRTHDAY = re_compile(r"生(年月日){e<3}")


INSURER = re_compile([
    r"[^被]保(険者(番号|名称)){e<2}",
    r"^[^被]?保(険者(番号|名称)){e<2}",
    r"^\D\D者(番号|名称)",
    r"(公費負){e<2}担(?!資)",
    r"(負担者番号){e<2}",
    r"(機関名)",
])


KOHI_NUM = re_compile([
    r"資格者\D{,3}番号{e<2}",
    r"受給者\D{,3}番号{e<2}",
    r"受給者\d",
    r"(記号番号){e<2}",
])


KIGO = re_compile([
    r"記号(.+)番号",
    r"記号[^番]+$",
])


VALID_FROM = re_compile([
    r"[発有]効期日{e<2}",
    r"[発有]効開始{e<2}",
    r"[発有]効年月日{e<2}",
    r"適用開始{e<2}",
    r"適用開始年月日{e<3}",
])


UNTIL_FIX = re_compile(r"(迄)(有効){e<2}")


VALID_UNTIL = re_compile([
    r"有(効期限){e<2}",
    r"喪失予定日{e<2}",
    r"有効終了{e<2}",
])


KOFU_FIX = re_compile(r"[交茭].?[付苻]")


KOFU = re_compile([
    r"交付年{e<2}",
    r"発行年{e<2}",
    r"(交\D?|\d\D?付)$",
    r"^付年月"
    r"交年月"
])


SKKGET = re_compile([
    r"資格取得{e<2}",
    r"認定年月日{e<2}",
    r"取得年月日{e<2}",
    r"資格認定{e<2}",
    r"扶養認定日{e<2}",
    r"適用開始{e<2}",
    r"適用開始年月日{e<2}",
    r"該当年月日{e<2}",
])


MONTH_DATE = r"([\D-]{1,3})(0[1-9]|[1-9]|1[0-2])([\D-])(0[1-9]|[1-9]|[1-2][0-9]0*|3[0-1]0*|99)(\D|$)" # pylint: disable=line-too-long


DATE = re_compile({
    "r": r"(令和|合和|令)\D?(0[1-9]|[1-9]|[1-9][0-9])" + MONTH_DATE,
    "h": r"(平成|平|成)(0[1-9]|[1-9]|[1-4][0-9])" + MONTH_DATE,
    "s": r"(昭和|昭)(0[1-9]|[1-9]|[1-5][0-9]|6[0-4])" + MONTH_DATE,
    "t": r"(大正|大|正)(0[1-9]|[1-9]|1[0-5])" + MONTH_DATE,
    "m": r"(明治|明|治)(0[1-9]|[1-9]|[1-3][0-9]|4[0-5])" + MONTH_DATE,
    "w": r"(19[0-9]{2}|2[0-9]{3})" + MONTH_DATE,
})


LAST_DAY = re.compile(r"[末未][日目]")


INSURER_NUM = re.compile(r"\d{6,8}")


ANY_NUM = re.compile(r"[\d-\pP]+")


PURE_NUM = re.compile(r"\d+")


DEDUCTIBLE_TAG = re.compile(r"(負担上限){e<3}")


DEDUCTIBLE_AMT = re.compile(r"([\do\pP]+)円")


DEDUCTIBLE_WITH_TAG = [
    re.compile(r"[入人]院([\do\pP]+)円"),
    re.compile(r"[入人]院外([\do\pP]+)円"),
    re.compile(r"外来([\do\pP]+)円"),
    re.compile(r"通院([\do\pP]+)円"),
    re.compile(r"調剤([\do\pP]+)円"),
]


DEDUCTIBLE_TAGS = [
    "入院",
    "入院外",
    "外来",
    "通院",
    "調剤",
]


PERCENT_SINGLE_DIGIT = re.compile(r"(一部負担金){e<2}(\d)$")


PERCENT = re_compile(r"\d割")


PERCENT_TAG = re.compile(r"一部負担金{e<2}")


DIV_TAG = re.compile(r"(適用区分){e<2}")


KBN = re.compile(r"(区分\D{1,3})")


GEN = re.compile(r"(現役\D{1,3})")


BRANCH = re_compile([
    r"枝番",
    r"番号.+[^号\d]+\d{2}$",
])

# 記号・番号記号1001番号4214102
KIGO_NUM = re_compile([
    r"^.号([^番号]+)番号[^\d(]?([\d(][\d\pP]*)",
    r"記.?号([^枝番号]+)番号?[^\d(]?([\d(][\d\pP]*)",
    r"記\D?([\d\pP]+)[\D]*番号[^\d(]?([\d(][\d\pP]*)",
    r"記\D?番号[^\d(]?(\d+)[^\d枝番]+(\d+)",
    r"記\D?番号[^\d(]?(\d+)",
    r"被保険者番号\D*([\d(][\d\pP]*)",
    r"記\D?([a-zA-Z0-9]+)番号[^\d(]?([\d(][\d\pP]*)",
    r"^([\d-]+)番号[^\d(]?([\d(][\d\pP]*)",
])


KIGO_SINGLE = re_compile([
    r"記号([\da-zA-Z-]+)",
    r"記号(.{1,4})$",
])


NUM_SINGLE = re_compile([
    r"番号([\d-]+)",
])
