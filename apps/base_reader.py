import time
import pickle
import unicodedata
from pathlib import Path
import numpy as np
import cv2
from .utils.image import merge, group_lines, get_clahe, draw_boxes, save_chips

class BaseReader:
  def __init__(self, client, logger, conf):
    self.client = client
    self.logger = logger
    preproc_conf = conf.get("preprocess", {})
    self.det_preproc = preproc_conf.get("detection", None)
    self.recog_preproc = preproc_conf.get("recognition", None)
    with open(str('./id2char_std.pkl'), 'rb') as f:
      self.id2char = pickle.load(f)
    assert len(self.id2char) == 7549
    self.clahe_op = get_clahe(conf["preprocess"]["clahe"])
    self.info = {}
    self.img = None
    self.det_img = None
    self.debug = conf.get("debug", {})
    if isinstance(self.debug.get("output", None), str):
      self.debug_out = Path(self.debug["output"])
      self.debug_out.mkdir(exist_ok=True)

  def clahe(self, img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    img_clahe = self.clahe_op.apply(gray)
    img_clahe = np.concatenate([img_clahe[..., np.newaxis]]*3, axis=-1)
    self.det_img = img_clahe
    return img_clahe

  def get_key(self, chip, lengths, height):
    lengths = sorted(lengths)
    w = int(height / chip.shape[0] * chip.shape[1])
    key = lengths[-1]
    for l in lengths:
      if w <= l:
        key = l
        break
    return key

  def find_texts(self, img):
    self.img = img
    self.det_img = None
    t0 = time.time()
    preproc = getattr(self, self.det_preproc)
    t0 = time.time()
    feed_img = preproc(img) if self.det_preproc is not None else img
    layout = "portrait" if img.shape[0] > img.shape[1] else "landscape"
    boxes, scores, angle = self.client.infer_sync(None, "DBNet", feed_img.copy(), layout=layout)
    if np.abs(angle) > 0.1:
      print("ANGLE", angle)
      m = cv2.getRotationMatrix2D((img.shape[1]//2, img.shape[0]//2), angle, 1)
      if self.img is not None: self.img = cv2.warpAffine(self.img, m, (img.shape[1], img.shape[0]), cv2.INTER_CUBIC)
      if self.det_img is not None: self.det_img = cv2.warpAffine(self.det_img, m, (img.shape[1], img.shape[0]), cv2.INTER_CUBIC)
    boxes = np.array(merge(boxes))
    if self.debug["draw_boxes"]: draw_boxes(self.det_img, boxes, self.debug_out)
    return boxes, scores

  def read_single_line(self, chip, box, num_only):
    lengths = list(self.client.dense.keys())
    height = self.client.height
    codes, probs, positions = self.client.infer_sync(None, 'Dense', chip, key=self.get_key(chip, lengths, height), num_only=num_only)
    text = ''.join([self.id2char[c] for c in codes])
    line = [[text, probs, positions, box], text]
    return line

  def read_texts(self, boxes):
    img = self.det_img if self.recog_preproc == self.det_preproc and self.det_img is not None else self.img
    boxes = boxes.astype(int)
    chips = map(lambda b: img[b[1]:b[3], b[0]:b[2]], boxes)
    chips = map(lambda img: cv2.resize(img, (int(64 / img.shape[0] * img.shape[1]), 64), cv2.INTER_AREA), chips)
    chips = list(chips)
    if self.debug["save_chips"]: save_chips(chips, self.debug_out)
    results = []
    while len(chips) > 0:
      merged_chip = (np.ones((64, 704 * 2, 3)) * 128).astype(np.uint8)
      start = 0
      ranges = []
      while len(chips) > 0 and 704 * 2 - start > chips[0].shape[1]:
        chip = chips.pop(0)
        merged_chip[:, start: start+chip.shape[1]] = chip
        end = start + chip.shape[1]
        ranges.append((start, end))
        start = end + 64
      if len(ranges) == 0:
        chip = chips.pop(0)
        merged_chip = chip
        ranges.append((0, 704 * 2))
      codes, probs, positions = self.client.infer_sync(None, 'Dense', merged_chip, key=704*2, num_only=False)
      #cv2.imwrite(f"./debug/merged_{len(chips)}_left.jpg", merged_chip)
      for r in ranges:
        pick = np.logical_and(r[0] <= positions, positions <= r[1])
        text = ''.join([self.id2char[c] for c in codes[pick]])
        text = unicodedata.normalize('NFKC', text)
        results.append((text, probs[pick], positions[pick]))
    results_with_box = [[r[0], r[1], r[2], b] for r, b in zip(results, boxes)]
    return results_with_box

  def group_textlines(self, recog_results):
    textlines = group_lines(recog_results)
    return textlines
