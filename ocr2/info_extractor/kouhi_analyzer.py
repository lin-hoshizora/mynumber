"""Analyzer that extracts key information from OCR resutls of 公費保険"""
from typing import List, Any
from .finders import JgnGakFinder, RouFtnKbnFinder
from .match import kohi_num_match, insurer_match
from .extract import get_date
from .re_pattern import KIGO
from .analyzer_base import AnalyzerBase


date_tags = [
    "入院",
    "入院外",
    "外来",
    "通院",
    "調剤",
    "無",
    "1割"
]


class KouhiAnalyzer(AnalyzerBase):
  """Analyzer to extract key information from OCR results of 公費保険証.

  It tries to extract as much keyinformation as possible when `fit` is called.
  The input argument `texts` of `fit` is a list containing OCR results, each
  element of which also has to be a list, whose last element has to be text of
  one line.

  All extracted information is stored in info, and can be queried by tag via
  `get`.

  Typical usage example:
    >>> analyzer = MainAnalyzer()
  """
  def __init__(self):
    config = {
        "HknjaNum": "wide_finder",
        "Num": "simple_finder",
        ("Birthday", "YukoStYmd", "YukoEdYmd", "KofuYmd"): "dates_finder",
        "JgnGak": JgnGakFinder(),
        "RouFtnKbn": RouFtnKbnFinder(),
    }
    super().__init__(config)

  def fit(self, texts):
    self._finder_fit(texts)
    self._handle_nums(texts)
    self._handle_kigo(texts)
    self._handle_multi_dates(texts)

  def _handle_nums(self, texts: List[List[Any]]):
    """Handles hknjanum and num on the same line.

    Args:
      texts: OCR results in a list.
    """
    if self._have("HknjaNum") and self._have("Num"): return
    for idx, line in enumerate(texts[:5]):
      ret1, _ = insurer_match(line[-1])
      ret2, _ = kohi_num_match(line[-1])
      if ret1 and ret2 and idx + 1 < len(texts):
        next_line = texts[idx + 1][-1]
        if next_line.isdigit():
          self.info["HknajaNum"] = next_line[:8]
          self.info["Num"] = next_line[8:]

  def _handle_kigo(self, texts):
    # special handling for kigo
    if self._have("Kigo"): return
    self.info["Kigo"] = None
    for line in texts:
      for pattern in KIGO:
        match = pattern.findall(line[-1])
        if match and match[0] is not None:
          self.info["Kigo"] = match[0]

  def _handle_multi_dates(self, texts: List[List[Any]]):
    """Handles multiple dates.

    Args:
      texts: OCR results in a list.
    """
    froms = []
    untils = []
    for idx, line in enumerate(texts):
      has_from = "から" in line[-1] or (len(line[-1]) > 2 and line[-1][-2]) == "か"
      has_until = "迄" in line[-1] or "まで" in line[-1]
      if not has_from and not has_until: continue
      dates = get_date(line[-1])
      if has_from and has_until and len(dates) == 2:
        froms.append((idx, dates[0]))
        untils.append((idx, dates[1]))
        continue
      if has_from and len(dates) == 1:
        froms.append((idx, dates[0]))
      if has_until and len(dates) == 1:
        untils.append((idx, dates[0]))
    if not (len(untils) > 1 and len(froms) > 1): return
    new_st = ""
    new_ed = ""
    for (idx_f, date_f), (idx_u, date_u) in zip(froms, untils):
      start = max(0, idx_f - 2, idx_u - 2)
      end = min(len(texts) - 1, idx_f + 2, idx_u + 2)
      for cidx in range(start, end + 1):
        for tag in date_tags:
          if tag in texts[cidx][-1].replace("憮", "無"):
            new_st += tag + " " + str(date_f) + ";"
            new_ed += tag + " " + str(date_u) + ";"
            texts[cidx][-1].replace(tag, "")
    if new_st and new_ed:
      self.info["YukoStYmd"] = new_st
      self.info["YukoEdYmd"] = new_ed
