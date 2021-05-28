import numpy as np
from .re_pattern import DATE, LAST_DAY, INSURER, ANY_NUM, INSURER_NUM
from .date import Date


def clean_date(text: str):
  text = text.replace("元年", "1年")
  text = LAST_DAY.sub("99日", text)
  return text


def get_date(text: str):
  text = clean_date(text)
  dates = []
  for era, pattern in DATE.items():
    matches = pattern.findall(text)
    if matches:
      for m in matches:
        if m[0].isdigit():
          dates.append(Date(year=m[0], month=m[2], date=m[4], era=era))
        else:
          dates.append(Date(year=m[1], month=m[3], date=m[5], era=era))
  return dates

def get_one_date(text: str):
  dates = get_date(text)
  if dates:
    return dates[0]


def date_western_str(text: str):
  return [d.western_str() for d in get_date(text)]


def get_insurer_num(text: str):
  num = None
  if len(text) < 3:
    return num
  for keyword in ["受給", "資格者"]:
    if keyword in text:
      text = text[:text.index(keyword)]

  matches = INSURER_NUM.findall(text)
  if matches:
    num = matches[0]
  return num


def get_num(text: str):
  matched = ANY_NUM.search(text)
  if matched is None: return
  return matched.group(0)


def find_one(match_func, texts):
  for line in texts:
    if match_func(line[-1]):
      return line
