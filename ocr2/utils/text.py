"""Helper functions for text processing"""
from typing import List, Any
import unicodedata
import regex as re
import numpy as np

NUM_FIX = {
    'ｌ': '１',
    'ｉ': '',
    'Ⅰ': '',
    'ｔ': '１',
    '」': '１',
    '「': '１',
    '丁': '１',
    '亅': '１',
    '｝': '１',
    '｛': '１',
    'ｏ': '０',
    'ｓ': '５',
    'ｇ': '９',
}


YMD = re.compile(r"(年月日){e<2}")

def fix_num(text: str) -> str:
  """Fix incorrectly recognized numbers

  Args:
    text: a string

  Returns:
    A string, where certain incorrectly recognized numbers are corrected
  """
  use_fix = False
  if YMD.search(text) is not None:
    use_fix = True
  if '番号' in text or '記号' in text:
    use_fix = True
  if len(text) == 2 and text[1] == '割':
    use_fix = True
  if use_fix:
    for k in NUM_FIX:
      text = text.replace(k, NUM_FIX[k])
  return text


def fuzzy_match(target: str, text: str, e_max: int = 2) -> bool:
  """Match a keyword in text with torlerance

  Args:
    target: keyword to match
    text: text where to match the keyword
    e_max: # of mismatched chars that leads to a False return, default: 2

  Returns:
    A bool, True if the match is successful
  """
  pattern = re.compile("(" + target + "){e<" + str(e_max) + "}")
  if pattern.search(text) is not None:
    return True
  return False


def clean_half_width(texts: List[List[Any]]) -> List[List[Any]]:
  """Cleans text and converts to half-width.

  Args:
    texts: A list of OCR results, each element of which is also a list
      containing all information of one line.

  Returns:
    A list with the same structure as `texts` but cleaned text.
  """
  for idx, line in enumerate(texts):
    # remove nums that are too close
    for idx_w, (text, probs, positions, _) in enumerate(line[:-1]):
      x_dist = positions[1:] - positions[:-1]
      close_indices = np.where(x_dist < 32)
      if close_indices[0].size > 0 and all([not c.isdigit() for c in text]):
        for idx_m in close_indices[0]:
          if (unicodedata.normalize('NFKC', text[idx_m]) ==
              unicodedata.normalize('NFKC', text[idx_m + 1])):
            texts[idx][idx_w][0] = text[:idx_m + 1] + text[idx_m+2:]
            texts[idx][idx_w][1][idx_m:idx_m+2] = [probs[idx_m]]
            texts[idx][idx_w][2][idx_m:idx_m+2] = [positions[idx_m]]
        texts[idx][-1] = ''.join([l[0] for l in texts[idx][:-1]])

    texts[idx][-1] = unicodedata.normalize('NFKC', fix_num(line[-1])).upper()
  return texts
