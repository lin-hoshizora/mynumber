import numpy as np
import cv2
import regex as re
from .base_reader import BaseReader
from .utils.image import box_crop, save_scope


class Calibrator(BaseReader):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.scope = None
    conf = kwargs["conf"]
    self.matches = conf["match"]
    self.crop_margin = conf["crop_margin"]

  def flip(self, boxes, img):
    if np.sum(boxes[:, 3] < img.shape[0] // 2) < boxes.shape[0] * 0.7:
      self.img  = cv2.rotate(self.img, cv2.ROTATE_180)
      self.det_img = cv2.rotate(self.det_img, cv2.ROTATE_180)
      boxes[:, 1::2] = img.shape[0] - boxes[:, 1::2]
      boxes[:, 0::2] = img.shape[1] - boxes[:, 0::2]
      boxes_rot = boxes.copy()
      boxes_rot[:, :2], boxes_rot[:, 2:] = boxes[:, 2:], boxes[:, :2]
      boxes = boxes_rot
    return boxes

  def test_ocr(self, img):
    boxes, scores = self.find_texts(img)
    img, self.scope = box_crop(boxes, img, self.crop_margin)
    save_scope(self.scope, "scope.txt")
    boxes, scores = self.find_texts(img)
    boxes = self.flip(boxes, img)
    recog_results = self.read_texts(boxes=boxes)
    textlines = self.group_textlines(recog_results)
    all_text = "".join([l[-1] for l in textlines])
    for key_phrase in self.matches:
      if re.search(str(key_phrase) + "{e<2}", all_text) is None:
        print(key_phrase, all_text)
        return False
    return True
