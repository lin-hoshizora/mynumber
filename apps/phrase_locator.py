import unicodedata
import pickle
import cv2
import regex as re
import numpy as np
from .base_reader import BaseReader

class PhraseLocator(BaseReader):
  def find(self, img, phrases):
    boxes, scores = self.find_texts(img)
    recog_results = self.read_texts(boxes=boxes)
    texts = self.group_textlines(recog_results)
    results = {}
    for line in texts:
      print(line[-1])
      for tag, text in phrases.items():
        if tag in results: continue
        pattern = re.compile("\D?".join([c for c in text]))
        matched = pattern.search(line[-1])
        if matched or (tag == "yuko_ed_ymd" and line[-1].endswith("で")):
          text = None
          if matched:
            text = matched.group(0)
          else:
            text = line[-1]
          start = line[-1].index(text)
          end = start + len(text) - 1
          lengths = [0] * (len(line) - 1)
          lengths[0] = len(line[0][0])
          box_start = None
          box_end = None
          print(line[-1], text)
          for i in range(len(lengths)):
            if i > 0: lengths[i] = lengths[i - 1] + len(line[i][0])
            print(line[i][0], lengths[i], start, end)
            if lengths[i] >= start and box_start is None:
              box_start = line[i][3]
            if lengths[i] >= end and box_end is None:
              box_end = line[i][3]
              break
          x1 = box_start[0]
          x2 = box_end[2]
          y1 = min(box_start[1], box_end[1])
          y2 = max(box_start[3], box_end[3])
          merged_box = np.array([x1, y1, x2, y2])
          results[tag] = merged_box
    return results
