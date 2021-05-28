import numpy as np
import regex as re
from .extract import get_date
from .re_pattern import BIRTHDAY, INSURER, KOHI_NUM, VALID_FROM, UNTIL_FIX, VALID_UNTIL, KOFU_FIX, KOFU, SKKGET, PERCENT



def match_one(patterns: list, text: str):
  for p in patterns:
    matched = p.search(text)
    if matched is not None:
      return True, matched
  return False, None


def birthday_match(text: str):
  if BIRTHDAY.search(text):
    return True, text
  return False, text


def insurer_match(text: str):
  ret, matched = match_one(INSURER, text)
  text = text if matched is None else text[matched.span()[0]:]
  return ret, text


def kohi_num_match(text: str):
  ret, matched = match_one(KOHI_NUM, text)
  text = text if matched is None else text[matched.span()[0]:]
  return ret, text


def valid_from_match(text: str):
  for keyword in ["まで", "迄"]:
    if keyword in text and len(get_date(text)) == 1:
      return False, text
  if re.search("自(?!己)", text):
    return 2, text[text.index("自") + 1:]
  match = re.search(r"か.$", text)
  if match:
    return 2, text[:match.span()[0]]
  if "から" in text:
    return 2, text[:text.index("から" )]
  if len(text) > 2 and "か" == text[-2]:
    return 2, text[:text.index("か")]
  if text.endswith("日か"):
    return 2, text[:-2]
  ret, matched = match_one(VALID_FROM, text)
  text = text if matched is None else text[matched.span()[0]:]
  return ret, text


def valid_until_match(text: str):
  text = UNTIL_FIX.sub(r"\g<1>有効", text)
  if not PERCENT.search(text):
    if "至" in text:
      return 2, text[text.index("至") + 1:]
    for key in ["まで", "迄有効"]:
      if key in text and not PERCENT.search(text):
        return 2, text[:text.index(key)]
  ret, matched = match_one(VALID_UNTIL, text)
  text = text if matched is None else text[matched.span()[0]:]
  return ret, text


def kofu_match(text: str):
  text = KOFU_FIX.sub("交付", text)
  ret, matched = match_one(KOFU, text)
  text = text if matched is None else text[matched.span()[0]:]
  return ret, text


def skkget_match(text: str):
  if "認定日" in text:
    return True, text[text.index("認定日") + 1:]
  ret, matched = match_one(SKKGET, text)
  text = text if matched is None else text[matched.span()[0]:]
  return ret, text


def score(match_func, texts, no_ext=False):
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
