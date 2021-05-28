from copy import deepcopy
import yaml
import numpy as np
from .. import match
from .. import extract
from ..match import score


class DatesFinder(yaml.YAMLObject):
  yaml_tag = u'!DatesFinder'
  def __init__(self, match_methods, extract_method):
    self.match_methods = match_methods
    self.extract_method = extract_method
    self.scores = {}
    self.texts = {}
    self.info = {}

  def _score(self, texts):
    for tag, match_func in self.match_methods.items():
      self.scores[tag], self.texts[tag] = score(getattr(match, match_func), texts, no_ext=(tag != "Birthday"))

  def extract(self, texts):
    self.texts = {}
    self.info = {}
    self._score(texts)

    # date match NMS
    for i in range(len(texts)):
      key_keep, suppress = None, False
      for key, score in self.scores.items():
        if score[i] < 2:
          continue
        if suppress:
          # more than 1 line with score > 1
          suppress = False
          break
        key_keep = key
        suppress = True
      if suppress:
        for key in self.scores:
          # do not suppress another single match
          if key != key_keep and sum(self.scores[key]) - self.scores[key][i] > 0:
            self.scores[key][i] = 0

    # extract dates from lines with positive score for any key
    extract_f = getattr(extract, self.extract_method)
    dates_all = {}
    for (tag, lines), (_, scores) in zip(self.texts.items(), self.scores.items()):
      dates_all[tag] = [extract_f(line) if score > 0 else [] for score, line in zip(scores, lines)]

    # handle 2 dates in the same line
    for tag in ["YukoStYmd", "YukoEdYmd"]:
      for dates in dates_all[tag]:
        if len(dates) == 2:
          self.info["YukoStYmd"], self.info["YukoEdYmd"] = dates

    # assign dates recursively
    for th in np.arange(np.max(list(self.scores.values())), 0, -1):
      scores_prev = {}
      while not all([np.all(scores_prev.get(k, None) == v) for k, v in self.scores.items()]):
        scores_prev = deepcopy(self.scores)
        for key in self.scores:
          if self.info.get(key, None) is not None: continue
          val_max, idx_max = self.scores[key].max(), self.scores[key].argmax()
          if val_max >= th and len(self.scores[key][self.scores[key] == val_max]) == 1 \
             and len(dates_all[key][idx_max]) == 1:
            self.info[key] = dates_all[key][idx_max][0]
            # clear other scores
            for other_key in set(self.scores.keys()) - set(key):
              self.scores[other_key][idx_max] = 0


    # handle yukostymd and yukoedymd in the same line
    if "YukoStYmd" not in self.info and "YukoEdYmd" not in self.info:
      idx_from = self.scores["YukoStYmd"].argmax()
      idx_until = self.scores["YukoEdYmd"].argmax()
      dates_from = dates_all["YukoStYmd"][idx_from]
      dates_until = dates_all["YukoEdYmd"][idx_until]
      if str(dates_from) == str(dates_until) and len(dates_from) == 2:
        self.info["YukoStYmd"], self.info["YukoEdYmd"] = dates_from

    for key in self.scores:
      if key not in self.info:
        for idx in reversed(self.scores[key].argsort()):
          if dates_all[key][idx]:
            self.info[key] = dates_all[key][idx].pop(0)
            break

    for tag in self.match_methods:
      if tag not in self.info:
        self.info[tag] = None
    return self.info
