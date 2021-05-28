import unicodedata
import pickle
import cv2
import regex as re
import numpy as np
from .base_reader import BaseReader
from info_extractor import Analyzer
from info_extractor.date import Date


class SimpleReader(BaseReader):
  def __init__(self, client, analyzer, logger, conf):
    super().__init__(client=client, logger=logger, conf=conf)
    self.analyzer = analyzer

  def need_rotate(self, boxes):
    xs = boxes[:, 0::2]
    ys = boxes[:, 1::2]
    w = xs.max() - xs.min()
    h = ys.max() - ys.min()
    self.logger.info(f"w: {w}, h: {h}")
    return w < h and w < 900 and h < 1600

  def need_retry(self, texts):
    self.analyzer.fit(texts)
    retry = True
    for k, v in self.analyzer.info.items():
      if k == "JgnGak": continue 
      if v:
        retry = False
        break
    return retry


  def ocr(self, img):
    img_ori = img.copy()
    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    self.info = {}
    boxes, scores = self.find_texts(img)
    rotate = self.need_rotate(boxes)
    if rotate:
      # handle orientation for card type
      boxes, scores = self.find_texts(img_ori)
    recog_results = self.read_texts(boxes=boxes)
    texts = self.group_textlines(recog_results)

    # simple check to see if upside down
    if self.need_retry(texts):
      # flip upsidedown and retry
      if self.img is not None: self.img = cv2.rotate(self.img, cv2.ROTATE_180)
      if self.det_img is not None: self.det_img = cv2.rotate(self.det_img, cv2.ROTATE_180)
      boxes[:, 0::2] = self.img.shape[1] - 1 - boxes[:, 0::2]
      boxes[:, 1::2] = self.img.shape[0] - 1 - boxes[:, 1::2]
      boxes = boxes[:, [2, 3, 0, 1]]
      recog_results = self.read_texts(boxes=boxes)
      texts = self.group_textlines(recog_results)

    if self.need_retry(texts):
      # retry in another direction
      new_img = cv2.rotate(self.img, cv2.ROTATE_90_CLOCKWISE)
      boxes, scores = self.find_texts(new_img)
      recog_results = self.read_texts(boxes=boxes)
      texts = self.group_textlines(recog_results)

    if self.need_retry(texts):
      # flip upsidedown and retry
      if self.img is not None: self.img = cv2.rotate(self.img, cv2.ROTATE_180)
      if self.det_img is not None: self.det_img = cv2.rotate(self.det_img, cv2.ROTATE_180)
      boxes[:, 0::2] = self.img.shape[1] - 1 - boxes[:, 0::2]
      boxes[:, 1::2] = self.img.shape[0] - 1 - boxes[:, 1::2]
      boxes = boxes[:, [2, 3, 0, 1]]
      recog_results = self.read_texts(boxes=boxes)
      texts = self.group_textlines(recog_results)
      self.analyzer.fit(texts)

    for l in texts:
      print(l[-1])

    self.info = self.analyzer.info
    return "公費"

  def extract_info(self, key: str):
    """
    Borrowed from mainstream insurance reader
    """
    if key == 'SyuKbn':
      return "公費"
    else:
      text = self.info.get(key, None)
      if isinstance(text, Date):
        text = str(text)
      result = {"text": text, "confidence": 1.0}
      return result
