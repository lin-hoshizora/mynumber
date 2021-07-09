"""Functions to determine if there is certain information in text"""
from typing import Tuple, Union, Callable, List
import numpy as np
import regex as re
from .extract import get_date, get_insurer_num
from .re_pattern import BIRTHDAY, INSURER, KOHI_NUM, VALID_FROM, UNTIL_FIX
from .re_pattern import VALID_UNTIL, KOFU_FIX, KOFU, SKKGET, PERCENT, BRANCH


def match_one(patterns: list, text: str) -> Tuple[bool, Union[str, None]]:
  """Matches given patterns one by one in text, and returns the first matched.

  Args:
    patterns: A list of compiled regex expression
    text: Text to match

  Returns:
    `(success, res)`, where `success` is a boolean indicating if there is
    anything matched, and res is a `regex.Match` if anything matched, and
    `None` otherwise.
  """
  for p in patterns:
    matched = p.search(text)
    if matched is not None:
      return True, matched
  return False, None


def birthday_match(text: str) -> Tuple[bool, str]:
  """Checks if text contains a birth date.

  Args:
    text: Text to check

  Returns:
    `(success, text)`, where `success` is `True` if there is a birth date,
    `False` if not. `text` is exactly the same input argument.
  """
  if BIRTHDAY.search(text):
    return True, text
  return False, text


def insurer_match(text: str) -> Tuple[bool, Union[str, None]]:
  """Checks if text contains an insurer number.

  Args:
    text: Text to check

  Returns:
    `(success, text)`, where `sucess` is `True` if matched, `False` if not,
    and `text` is text truncated from the matched pattern if matched, `None`
    if not.
    e.g.
    >>> insurer_match("123456保険者番号87654321")
    True 保険者番号87654321
  """
  # get rid of phone number
  text = re.sub(r"\d+\(\d+\)\d+", "", text)
  ret, matched = match_one(INSURER, text)

  if ret:
    print(matched)

  # check right side at first
  if matched and get_insurer_num(text[matched.span()[0]:]):
    return ret, text[matched.span()[0]:]

  # check left if no no. found on right
  if matched and get_insurer_num(text[:matched.span()[0]]):
    return ret, text[:matched.span()[0]]

  return ret, text


def kohi_num_match(text: str) -> Tuple[bool, Union[str, None]]:
  """Checks if 公費受給者番号 exists in text.

  Args:
    text: Text to check

  Returns:
    `(success, text)`, where `sucess` is `True` if matched, `False` if not,
    and `text` is text truncated from the matched pattern if matched, `None`
    if not.
    e.g.
    >>> insurer_match("123456受給者番号87654321")
    True 受給者番号87654321
  """
  ret, matched = match_one(KOHI_NUM, text)
  text = text if matched is None else text[matched.span()[0]:]
  return ret, text


def valid_from_match(text: str) -> Tuple[bool, Union[str, None]]:
  """Checks if 有効開始日 exists in text.

  Args:
    text: Text to check

  Returns:
    `(success, text)`, where `sucess` is `True` if matched, `False` if not,
    and `text` is text truncated base on the matched pattern if matched,
    `None` if not.
    e.g.
    >>> insurer_match("2021年12月12日有効開始日2021年1月1日")
    True 有効開始日2021年1月1日
  """
  for keyword in ["まで", "迄"]:
    if keyword in text and len(get_date(text)) == 1:
      return False, text
  if re.search("自(?!己)", text):
    return 2, text[text.index("自") + 1:]
  match = re.search(r"か.$", text)
  if match:
    return 2, text[:match.span()[0]]
  if "から" in text:
    return 2, text[:text.index("から")]
  if len(text) > 2 and text[-2] == "か":
    return 2, text[:text.index("か")]
  if text.endswith("日か"):
    return 2, text[:-2]
  ret, matched = match_one(VALID_FROM, text)
  text = text if matched is None else text[matched.span()[0]:]
  return ret, text


def valid_until_match(text: str) -> Tuple[bool, Union[str, None]]:
  """Checks if 有効終了日 exists in text.

  Args:
    text: Text to check

  Returns:
    `(success, text)`, where `sucess` is `True` if matched, `False` if not,
    and `text` is text truncated base on the matched pattern if matched,
    `None` if not.
    e.g.
    >>> insurer_match("有効開始日2021年12月12日有効終了日2021年1月1日")
    True 有効終了日2021年1月1日
  """
  text = UNTIL_FIX.sub(r"\g<1>有効", text)
  if not PERCENT.search(text):
    if "至" in text:
      return 2, text[text.index("至") + 1:]
    if "まで" in text and "までは" not in text and not PERCENT.search(text):
      return 2, text[:text.index("まで")]
    if "迄有効" in text and not PERCENT.search(text):
      return 2, text[:text.index("迄有効")]
  ret, matched = match_one(VALID_UNTIL, text)
  text = text if matched is None else text[matched.span()[0]:]
  return ret, text


def kofu_match(text: str) -> Tuple[bool, Union[str, None]]:
  """Checks if 交付年月日 exists in text.

  Args:
    text: Text to check

  Returns:
    `(success, text)`, where `sucess` is `True` if matched, `False` if not,
    and `text` is text truncated until the matched pattern if matched, `None`
    if not.
    e.g.
    >>> insurer_match("2009年12月1日交付有効終了日2021年1月1日")
    True 2009年12月1日
  """
  text = KOFU_FIX.sub("交付", text)
  ret, matched = match_one(KOFU, text)

  # nothing matched
  if matched is None: return ret, text

  # check right side first
  if get_date(text[matched.span()[0]:]):
    return ret, text[matched.span()[0]:]

  # check left side if nothing on right
  if get_date(text[:matched.span()[0]]):
    return ret, text[:matched.span()[0]]

  return ret, text


def skkget_match(text: str) -> Tuple[bool, Union[str, None]]:
  """Checks if 資格取得日 exists in text.

  Args:
    text: Text to check

  Returns:
    `(success, text)`, where `sucess` is `True` if matched, `False` if not,
    and `text` is text truncated until the matched pattern if matched, `None`
    if not.
    e.g.
    >>> insurer_match("2009年12月1日資格取得日2021年1月1日")
    True 2021年1月1日
  """
  if "認定日" in text:
    return True, text[text.index("認定日") + 1:]
  ret, matched = match_one(SKKGET, text)
  text = text if matched is None else text[matched.span()[0]:]
  return ret, text


def branch_match(text: str) -> Tuple[bool, Union[str, None]]:
  """Checks if 枝番 exists in text.

  Args:
    text: Text to check

  Returns:
    `(success, text)`, where `sucess` is `True` if matched, `False` if not,
    and `text` is text truncated until the matched pattern if matched, `None`
    if not.
    e.g.
    >>> insurer_match("12345枝番6789")
    True 枝番6789
  """
  ret, matched = match_one(BRANCH, text)
  text = text if matched is None else text[matched.span()[0]:]
  text = re.sub(r"番号\d+", "", text)
  return ret, text


def score(
    match_func: Callable[[str], Tuple[bool, str]],
    texts: List[list],
    no_ext: bool = False
) -> Tuple[np.ndarray, List[str]]:
  """Score each text line based on a given match function.

  When `no_ext` is `True`, a matched line has a score of 2. The line above
  it and the line below it has a score of 1.
  When `no_ext` is `False`, a matched line has a score of 1, and each other
  line has a score of 0.

  Args:
    match_func: A function used for pattern matching
    texts: A list of textline information. Each element is also a list whose
       last element is all text of thel textline.
    no_ext: If give lines below/above the matched one positive scores.

  Returns:
    `(scores, texts)`, where `scores` is a `np.ndarray` whose length is the same
    as texts. `texts` is all texts or `None` returned by `match_func` .
  """
  match_results = [match_func(line[-1]) for line in texts]
  scores = np.array([int(r[0]) for r in match_results])
  cut_texts = [r[1] for r in match_results]
  if no_ext:
    return scores, cut_texts
  scores_ext = scores.copy()
  # 2 for the hit lines
  scores_ext *= 2
  # 1 for lines above/below the hit lines
  scores_ext[:-1] += scores[1:]
  scores_ext[1:] += scores[:-1]
  return scores_ext, cut_texts
