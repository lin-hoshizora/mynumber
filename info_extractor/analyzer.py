from pathlib import Path
import numpy as np
import yaml
#from .textline import TextLine
from .finders import SimpleFinder, DatesFinder, WideFinder, JgnGakFinder, RouFtnKbnFinder
from .match import kohi_num_match, insurer_match
from .extract import find_one, get_num, get_date
from .re_pattern import KIGO

def load_finder(tag, category):
  path = Path(__file__).resolve().parent / "presets" / category / (tag.lower() + ".yaml")
  with open(str(path)) as f:
    obj = yaml.load(f, Loader=yaml.Loader)
  return obj

date_tags = [
  "入院",
  "入院外",
  "外来",
  "通院",
  "調剤",
  "無",
  "1割"
]

class Analyzer:
  def __init__(self):
    self.texts = []
    self.info = {}
    self.config = {
      "HknjaNum": "wide_finder",
      "Num": "simple_finder",
      #"Birthday": "birthday_finder",
      #("YukoStYmd", "YukoEdYmd"): "valid_date_finder",
      ("Birthday", "YukoStYmd", "YukoEdYmd", "KofuYmd"): "dates_finder",
      "JgnGak": JgnGakFinder(),
      "RouFtnKbn": RouFtnKbnFinder(),
    }
    self.finders = {}
    for tag, cat in self.config.items():
      if not isinstance(cat, str):
        self.finders[tag] = cat
        continue
      if isinstance(tag, str):
        self.finders[tag] = load_finder(tag, cat)
      elif isinstance(tag, tuple):
        self.finders[tag] = load_finder(cat, cat)


  def fit(self, texts):
    #self.texts = [TextLine(t) for t in texts]
    self.texts = texts
    self.info = {}
    for tag in self.finders:
      if isinstance(tag, str):
        self.info[tag] = self.finders[tag].extract(texts)
      if isinstance(tag, tuple):
        for k, v in self.finders[tag].extract(texts).items():
          self.info[k] = v

    # specil handling of hknjanum and num on the same line
    if self.info.get("HknjaNum", None) is None or self.info.get("Num", None) is None:
      for idx, line in enumerate(texts[:5]):
        ret1, text1 = insurer_match(line[-1])
        ret2, text2 = kohi_num_match(line[-1])
        #print(line[-1], ret1, ret2)
        if ret1 and ret2 and idx + 1 < len(texts):
          next_line = texts[idx + 1][-1]
          if next_line.isdigit():
            self.info["HknajaNum"] = next_line[:8]
            self.info["Num"] = next_line[8:]

    # special handling for kigo
    if "Kigo" not in self.info:
      self.info["Kigo"] = None
      for line in texts:
        for pattern in KIGO:
          match = pattern.findall(line[-1])
          if match and match[0] is not None:
            self.info["Kigo"] = match[0]

    # special handling for multiple dates
    froms = []
    untils = []
    tags = []
    for idx, line in enumerate(texts):
      has_from = "から" in line[-1] or (len(line[-1]) > 2 and "か" == line[-1][-2])
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
    #print(texts[0][-1])
    #print(froms, untils)
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


  def get(self, tag):
    return self.info.get(tag, None)
