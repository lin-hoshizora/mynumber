"""Helper functions for image processing"""
from typing import List
import logging
import numpy as np
import cv2


def rotate_if_necessary(
    img: np.ndarray,
    threshold: int,
    logger: logging.Logger
) -> np.ndarray:
  """Rotate image according to orientation and size.

  Rotate image if small size is portrait or large size is landscape,
  while small/large is defined by `threshold`

  Args:
    img: an image
    threshold: Threshold of long size. Any image whose long size is longer than
      threshold is considered large.
    logger: a Python logger

  Returns:
    An image with fixed orientation
  """
  if max(img.shape) > threshold:
    if img.shape[1] > img.shape[0]:
      img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
      logger.info('Rotate large landscape image by 90 counterclockwise')
  else:
    if img.shape[0] > img.shape[1]:
      img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
      logger.info('Rotate small portrait image by 90 counterclockwise')
  return img


def get_rect(polygons: np.ndarray, min_wh_ratio: float = 0) -> np.ndarray:
  """Gets rectangles from polygons.

  Args:
    polygons: 2d numpy array with a shape of (n, 8), where n is number of
      polygons. If the 2nd dimension is larger than 8, only the first 8
      numbers will be used.
    min_wh_ratio: Minimum width-height ratio for a valid rectangle

  Returns:
    A 2d numpy array with a shape of (n, 4), where n is number of rectangles.
  """
  polygons = polygons[:, :8]
  rects = []
  for polygon in polygons:
    pts = polygon.reshape(4, 2)
    x0, x1 = pts[:, 0].min(), pts[:, 0].max()
    #y0, y1 = pts[:, 1].min(), pts[:, 1].max()
    y0, y1 = pts[:2, 1].mean(), pts[2:, 1].mean()
    if y1 - y0 < 8 or x1 - x0 < 8: continue
    if (x1 - x0) / (y1 - y0) > min_wh_ratio:
      rects.append([x0, y0, x1, y1])
  rects = np.array(rects)
  return rects


def get_chips(img: np.ndarray, boxes: np.ndarray) -> List[np.ndarray]:
  """Gets images chips from an image based on given bounding boxes.

  Args:
    img: Image to extract chips from
    boxes: Bounding boxes

  Returns:
    A list of image chips, each of which is a numpy array.
  """
  assert len(boxes.shape) == 2 and boxes.shape[1] == 4
  assert (boxes >= 0).all(), 'expect all coords to be non-negative'
  chips = []
  for b in boxes.astype(int):
    x1 = min(max(b[0], 0), img.shape[1] - 2)
    x2 = max(b[2], x1 + 1)
    y1 = min(max(b[1], 0), img.shape[0] - 2)
    y2 = max(b[3], y1 + 1)
    chips.append(img[y1:y2, x1:x2])
  return chips


def merge(boxes: np.ndarray, viou_threshold: float = 0.6) -> List[np.ndarray]:
  """Merges overlapping or very close bounding boxes.

  Args:
    boxes: A numpy array with a shape of (n, 4), where n is number of boxes
    viou_threshold: Threshold of IOU in vertial direction to determine if two
      boxes should be considered for merging.

  Returns:
    A list of merged boxes.
  """
  merged_boxes = []
  skip = [False] * len(boxes)
  for i in range(len(boxes)): #pylint: disable=consider-using-enumerate
    if skip[i]: continue
    b1 = boxes[i]
    for j in range(i+1, len(boxes)):
      if skip[j]: continue
      b2 = boxes[j]
      if (b2[0] < b1[0] < b2[2]) or (b1[0] < b2[0] < b1[2]):
        v_iou = ((min(b1[3], b2[3]) - max(b1[1], b2[1])) /
                 (max(b1[3], b2[3]) - min(b1[1], b2[1])))
        if v_iou > viou_threshold:
          skip[j] = True
          b1[0] = min(b1[0], b2[0])
          b1[1] = min(b1[1], b2[1])
          b1[2] = max(b1[2], b2[2])
          b1[3] = max(b1[3], b2[3])
    merged_boxes.append(b1)
  return merged_boxes


def rotate(img, angle):
  rot_m = cv2.getRotationMatrix2D((img.shape[1]//2, img.shape[0]//2), angle, 1)
  out_shape = (img.shape[1], img.shape[0])
  img = cv2.warpAffine(img, rot_m, out_shape, cv2.INTER_CUBIC)
  return img
