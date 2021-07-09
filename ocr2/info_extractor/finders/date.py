"""Finder to extract all dates from multiple lines of text"""
from typing import List, Any
from copy import deepcopy
import yaml
import numpy as np
from .. import match
from .. import extract
from ..match import score


class DatesFinder(yaml.YAMLObject):
  """Finder to extract multiple dates from multiple text lines output by OCR.

  Disclaimer:
  This finder was originally designed to address the issue that different kinds
  of dates may be extracted from the same excerpt. However, THIS IS NOT MEANT
  TO BE A FINAL SOLUTION FOR DATE EXTRACTION due to limited time and testing
  data. If a maintainer finds out some code does not make sense, probably it's
  because the code does not make sense indeed, and such a maintainer is
  encouraged to modify or totally reimplement this finder.

  Another problem that can be addressed, but has NOT been addressed is
  inconsistency between extracted dates. e.g. YukoEdYmd is earlier than
  YukoStYmd. You are encouraged to implement a check for this problem
  if you ovserve such inconsistency in tests.

  Typical usage example:
    >>> match_methods = {
            "Birthday": "birthday_match",
            "YukoEdYmd": "valid_until_match",
            "YukoStYmd": "valid_from_match",
            "KofuYmd": "kofu_match",
        }
    >>> finder = DatesFinder(
            match_methods=match_methods,
            extract_method="get_date"
        )
    >>> texts = [
            ["生年月日平成1年2月3日"],
            ["有効開始日令和元年1月2日有効終了日令和2年1月2日"],
            ["令和元年1月1日交付"]
        ]
    >>> dates = finder.extract(texts)
    >>> print(dates["Birthday"])
    19890203
    >>> print(dates["YukoStYmd"])
    20190102
    >>> print(dates["YukoEdYmd"])
    20200102
    >>> print(dates["KofuYmd"])
    20190101

  Args:
    match_methods: Name of the function for pattern matching, which has to be
        defined in `..match`
    extract_method: Name of the function for information extraction, which has
        to be defined in `..extract`
  """
  yaml_tag = u'!DatesFinder'
  def __init__(self, match_methods: str, extract_method: str):
    self.match_methods = match_methods
    self.extract_method = extract_method
    self.scores = {}
    self.texts = {}
    self.info = {}

  def _score(self, texts: List[List[Any]]):
    """Scores each textline for each kind of date to extract.

    Args:
      texts: OCR results in a list, each element of each has also to be a
        list, each element of which is the text for each detected line.
    """
    for tag, match_func in self.match_methods.items():
      # only look above and below for birth dates
      self.scores[tag], self.texts[tag] = score(
          match_func=getattr(match, match_func),
          texts=texts,
          no_ext=(tag != "Birthday")
      )

      # if YukoEdYmd found within the first 2 lines, make an exception to look below
      if tag == "YukoEdYmd" and sum(self.scores[tag][:2]) == 1:
        self.scores[tag], self.texts[tag] = score(
            match_func=getattr(match, match_func),
            texts=texts,
            no_ext=False
        )

  def extract(self, texts: List[List[Any]]) -> dict:
    """Extracts all kinds of dates from text lines when possible.

    Args:
      texts: OCR results in a list, each element of each has also to be a
        list, each element of which is the text for each detected line.

    Returns:
      A dict of extracted dates
    """
    self.texts = {}
    self.info = {}
    self._score(texts)

    # extract dates from lines with positive score for any key
    extract_f = getattr(extract, self.extract_method)
    dates_all = {}
    for (tag, lines), (_, scores) in zip(
        self.texts.items(),
        self.scores.items()
    ):
      dates_all[tag] = [extract_f(line) if score > 0 else [] for score, line in zip(scores, lines)] #pylint: disable=line-too-long

    # date match NMS
    for i in range(len(texts)):
      key_keep, suppress = None, False
      for key, cur_score in self.scores.items():
        if cur_score[i] < 2:
          continue
        if suppress:
          # more than 1 line with score > 1
          suppress = False
          break
        key_keep = key
        suppress = True
      if suppress:
        for key, cur_dates in dates_all.items():
          if key == key_keep or not cur_dates: continue
          for idx, (dates1, dates2) in enumerate(zip(
              cur_dates,
              dates_all[key_keep]
          )):
            dates_all[key][idx] = [d1 for d1 in dates1 if d1 not in dates2]


    # suppress YukoStYmd when YukoEdYmd and KofuYmd matched on the same line
    for idx, dates in enumerate(dates_all["YukoEdYmd"]):
      if (self.scores["YukoStYmd"][idx] and
          self.scores["KofuYmd"][idx] and
          len(dates) < 3):
        self.scores["YukoStYmd"][idx] = 0
        dates_all["YukoStYmd"][idx].clear()

    # handle 2 dates in the same line
    for idx, dates in enumerate(dates_all["YukoEdYmd"]):
      if (len(dates) == 2 and
          self.scores["YukoStYmd"][idx] > 0 and
          self.scores["KofuYmd"][idx] == 0):
        self.info["YukoStYmd"], self.info["YukoEdYmd"] = dates
        if str(self.info["YukoStYmd"]) > str(self.info["YukoEdYmd"]):
          self.info["YukoStYmd"], self.info["YukoEdYmd"] = self.info["YukoEdYmd"], self.info["YukoStYmd"] #pylint: disable=line-too-long

    # assign dates recursively
    for th in np.arange(np.max(list(self.scores.values())), 0, -1):#pylint: disable=too-many-nested-blocks
      scores_prev = {}
      while not all([np.all(scores_prev.get(k, None) == v) for k, v in self.scores.items()]):#pylint: disable=line-too-long
        scores_prev = deepcopy(self.scores)
        for key in self.scores:
          if self.info.get(key, None) is not None: continue
          val_max, idx_max = self.scores[key].max(), self.scores[key].argmax()
          if (val_max >= th and
              len(self.scores[key][self.scores[key] == val_max]) == 1 and
              len(dates_all[key][idx_max]) == 1):
            self.info[key] = dates_all[key][idx_max][0]
            # pop out used date
            for other_key in set(self.scores.keys()) - set(key):
              other_dates = dates_all[other_key][idx_max]
              if other_dates:
                new_dates = [d for d in other_dates if str(d) != str(self.info[key])] #pylint: disable=line-too-long
                dates_all[other_key][idx_max] = new_dates

    # handle yukostymd and yukoedymd in the same line
    if "YukoStYmd" not in self.info and "YukoEdYmd" not in self.info:
      idx_from = self.scores["YukoStYmd"].argmax()
      idx_until = self.scores["YukoEdYmd"].argmax()
      dates_from = dates_all["YukoStYmd"][idx_from]
      dates_until = dates_all["YukoEdYmd"][idx_until]
      if str(dates_from) == str(dates_until) and len(dates_from) == 2:
        self.info["YukoStYmd"], self.info["YukoEdYmd"] = dates_from


    # handle YukoEdYmd and KofuYmd in the same line
    if (self.info.get("YukoEdYmd", None) is None and
        self.info.get("KofuYmd", None) is None):
      for idx in range(len(self.scores["YukoEdYmd"])):
        if (self.scores["KofuYmd"][idx] > 0 and
            len(dates_all["YukoEdYmd"][idx]) == 2 and
            len(dates_all["KofuYmd"][idx]) == 2):
          self.info["KofuYmd"], self.info["YukoEdYmd"] = dates_all["KofuYmd"][idx] #pylint: disable=line-too-long
          # make sure KofuYmd is earlier than YukoEdYmd
          if str(self.info["KofuYmd"]) > str(self.info["YukoEdYmd"]):
            self.info["KofuYmd"], self.info["YukoEdYmd"] = self.info["YukoEdYmd"], self.info["KofuYmd"] #pylint: disable=line-too-long

    for key in self.scores:
      if self.info.get(key, None) is None:
        for idx in (-self.scores[key]).argsort(kind="mergesort"):
          if dates_all[key][idx]:
            # use the earliest date for birthday
            if key == "Birthday":
              dates_all[key][idx] = sorted(dates_all[key][idx], key=str)
            self.info[key] = dates_all[key][idx].pop(0)
            break

    for tag in self.match_methods:
      if tag not in self.info:
        self.info[tag] = None
    return self.info
