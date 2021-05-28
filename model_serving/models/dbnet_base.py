import numpy as np
import cv2
from .utils.image import resize_ar, get_min_box, get_score, unclip, get_rect

class DBNet:
  def __init__(self,
               logger,
               threshold: float = 0.3,
               box_th: float = 0.5,
               max_candidates: int = 1000,
               unclip_ratio: float = 2.,
               min_size: int = 3):
    self.logger = logger
    self.threshold = threshold
    self.box_th = box_th
    self.max_candidates = max_candidates
    self.unclip_ratio = unclip_ratio
    self.min_size = min_size

  def preprocess(self, img: np.ndarray):
    img, self.scale = resize_ar(img, self.input_w, self.input_h)
    self.img = img.copy()
    img = img.astype(np.float32)
    self.logger.debug(f"Preprocess Mode: {self.preproc_mode}")
    if self.preproc_mode == "caffe":
      img /= 255.
      img -= np.array([0.485, 0.456, 0.406])
      img /= np.array([0.229, 0.224, 0.225])
    img = img[np.newaxis, ...]
    return img

  def parse_result(self, result: np.ndarray):
    result = result[0, ..., 0]
    mask = result > self.threshold
    h, w = mask.shape
    contours, _ = cv2.findContours((mask * 255).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    n_contours = min(len(contours), self.max_candidates)
    boxes = []
    scores = []
    rects = []
    angles = []
    for idx, contour in enumerate(contours[:n_contours]):
      c = contour.squeeze(1)
      pts, sside, angle = get_min_box(c)
      if sside < self.min_size:
        continue
      score = get_score(result, c)
      if self.box_th > score:
        continue
      c = unclip(pts, unclip_ratio=self.unclip_ratio).reshape(-1, 1, 2)
      pts, sside, angle = get_min_box(c)
      if sside < self.min_size + 2:
        continue
      pts[:, 0] = np.clip(np.round(pts[:, 0]), 0, w)
      pts[:, 1] = np.clip(np.round(pts[:, 1]), 0, h)
      boxes.append(pts)
      scores.append(score)
      if np.abs(angle) > 0:
        angles.append(angle)

    boxes = np.array(boxes)
    scores = np.array(scores)
    angle = 0 if not angles else np.mean(angles)
    if np.abs(angle) > 0.1:
      m = cv2.getRotationMatrix2D((w//2, h//2), angle, 1)
      coords = boxes.reshape((-1, 2))
      coords = np.concatenate([coords, np.ones((coords.shape[0], 1))], axis=1)
      coords = np.dot(m, coords.transpose()).transpose()
      boxes = coords.reshape(boxes.shape)
    boxes /= self.scale
    boxes = get_rect(boxes)
    return boxes, scores, angle
