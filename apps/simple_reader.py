import unicodedata
import pickle
import cv2
import regex as re
import numpy as np
from .base_reader import BaseReader
from apps.utils_v1.text import *


class SimpleReader(BaseReader):
  def __init__(self, client, logger, conf):
    super().__init__(client=client, logger=logger, conf=conf)

  def ocr(self, img):
    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    self.info = {}
    boxes, scores = self.find_texts(img)
    recog_results = self.read_texts(boxes=boxes)
    texts = self.group_textlines(recog_results)
    for l in texts:
      print(l[-1])

    # Birthday
    for l in texts:
      if birthday_match(l[-1]):
        dates = get_date(l[-1])
        if dates:
          self.info["Birthday"] = dates[0]
          break

    # HknjaNum
    for l in texts:
      if insurer_match(l[-1]):
        num = get_insurer_no(l[-1].replace("年", "").replace("月", ""), [])
        if num:
          self.info["HknjaNum"] = num[0]
          break

    # Num
    for l in texts:
      if re.search(r"(受給者番号){e<2}", l[-1]):
        num = re.search(r"\d{6,8}", l[-1].replace("年", "").replace("月", ""))
        if num:
          self.info["Num"] = num[0]

    # Kigo
    # NumK
    # YukoStYmd
    for l in texts:
      if valid_from_match(l[-1]):
        dates = get_date(l[-1])
        if dates:
          self.info["YukoStYmd"] = dates[0]
          break

    # YukoEdYmd
    for l in texts:
      if valid_until_match(l[-1]):
        dates = get_date(l[-1])
        if dates:
          self.info["YukoEdYmd"] = dates[0]
          break
    # JgnGak
    # HknjaName
    # RouFtnKbn
    print(self.info)
    return "公費"

  def extract_info(self, key: str):
    """
    Borrowed from mainstream insurance reader
    """
    if key == 'SyuKbn':
      return "公費"
    else:
      result = {"text": self.info.get(key, None), "confidence": 1.0}
      return result
