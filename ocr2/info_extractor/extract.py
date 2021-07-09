"""Functions to extract an named entity from text"""
from typing import Union, List, Any, Callable
import regex as re
from .re_pattern import DATE, LAST_DAY, INSURER_NUM, PURE_NUM
from .re_pattern import KIGO_NUM, KIGO_SINGLE, NUM_SINGLE
from .date import Date


def extract_one(patterns: list, text: str) -> Union[Any, None]:
  """Searches multiple patterns in text and returns the first match.

  Args:
    patterns: A list of compiled regex expression
    text: Text to search patterns in

  Returns:
    Matched content if any, `None` otherwise
  """
  for p in patterns:
    # print(p)
    res = p.findall(text)
    if res is not None and res and res[0]:
      res = res[0]
      return res
  return None


def clean_date(text: str) -> str:
  """Relaces special words in a date string.

  Args:
    text: Date string to clean

  Returns:
    A cleaned string.
  """
  text = text.replace("元年", "1年")
  text = LAST_DAY.sub("99日", text)
  return text


def get_date(text: str) -> List[Date]:
  """Extracts all dates from text.

  Args:
    text: Text to extract dates from

  Returns:
    A list of all dates that can be extracted from the text. Each date is
    a `Date` instance.
  """
  text = clean_date(text)
  dates = []
  for era, pattern in DATE.items():
    matches = pattern.findall(text)
    if not matches: continue
    for m in matches:
      if m[0].isdigit():
        dates.append(Date(year=m[0], month=m[2], date=m[4], era=era))
      else:
        dates.append(Date(year=m[1], month=m[3], date=m[5], era=era))
  return dates


def get_one_date(text: str) -> Union[Date, None]:
  """Gets one date from text

  This function calls `get_date` and returns the first element in
  the returned list. Therefore the returned date depends on the
  actual implementation of `get_date`, which means it does NOT
  have to be the first date appears in the text.

  Args:
    text: Text to extract dates from

  Returns:
    An Date instance if any date can be extracted from the text,
    `None` otherwise.
  """
  dates = get_date(text)
  if dates:
    return dates[0]
  return None


def date_western_str(text: str) -> List[str]:
  """Extracts dates as strings (western calendar year) from text.

  Args:
    text: Text to extract dates from

  Returns:
    A list of date strings. Empty if no date can be extracted.
  """
  return [d.western_str() for d in get_date(text)]


def get_insurer_num(text: str) -> Union[str, None]:
  """Extracts insurer number from text.

  Args:
    text: Text to extract insurer number from

  Returns:
    A string of insurer number. None if nothing can be extracted.
  """
  num = None
  if len(text) < 3:
    return num
  for keyword in ["受給", "資格者"]:
    if keyword in text:
      text = text[:text.index(keyword)]


  matches = INSURER_NUM.findall(text)
  if matches:
    num = matches[0]
  elif re.search("電話\d",text):
    return num

  elif not re.search("\d{2,3}-\d{4}-\d{4}", text):
    # get rid of wierd marks and try again
    new_text = re.sub(r"[ｌ\pP]+", "", text)
    matches = INSURER_NUM.findall(new_text)
    if matches: num = matches[0]
  return num


def get_pure_num(text: str) -> Union[str, None]:
  """Extracts a pure number from text.

  Args:
    text: Text to extract a number from

  Returns:
    A number string. `None` if no number can be extracted.
  """
  matched = PURE_NUM.search(text)
  if matched is None:
    return matched
  return matched.group(0)


def get_kigo_num(text: str) -> Union[tuple, None]:
  """Extracts 記号 and 番号 from text.

  Args:
    text: Text to extract 記号番号 from

  Returns:
    A tuple of (記号, 番号) if both are found. A string of 番号 if 記号 does
    not exist. `None` if nothing can be extracted.
  """
  
  res = extract_one(KIGO_NUM, text)
  # if res:
  #   print(1,text)
  return res


def get_kigo(text: str) -> Union[str, None]:
  """Extracts 記号 from text.

  Args:
    text: Text to extract 記号 from

  Returns:
    A string of 記号 if it can be extracted, `None` otherwise.
  """
  res = extract_one(KIGO_SINGLE, text)
  return res


def get_num(text: str) -> Union[str, None]:
  """Extracts 番号 from text.

  Args:
    text: Text to extract 番号 from

  Returns:
    A string of 番号 if it can be extracted, `None` otherwise.
  """
  res = extract_one(NUM_SINGLE, text)
  return res


def find_one(match_func: Callable[[str], bool], texts: List[list]) -> list:
  """Finds one matched line given a matching function.

  Args:
    match_func: A function that takes a text, and returns `True` when matched,
        and `False` otherwise.
    texts: A list of textlines. Each element should also be a list whose last
        element is text of the whole line.

  Returns:
    A matched element in texts. `None` if no match.
  """
  for line in texts:
    if match_func(line[-1]):
      return line
  return None
