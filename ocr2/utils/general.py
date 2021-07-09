"""General helper functions for OCR"""
from typing import List, Any
import numpy as np


def group_lines(
    texts: List[List[Any]],
    iou_threshold: float = 0.4
) -> List[List[Any]]:
  """Groups texts with bounding boxes in lines.

  Args:
    texts: A list of OCR result, each element of which is also a list of
      [text, probability, position, bouding_box]
    iou_threshold: Threshold for IOU in vertical direction to determine if
      two bounding boxes belong to the same line.

  Returns:
    A list of lists of bouding boxes belonging to the same line.
  """
  grouped = []
  texts = sorted(texts, key=lambda x: (x[-1][1] + x[-1][3]) / 2)
  current_line = []
  for text in texts:
    if not current_line:
      current_line.append(text)
      continue
    y0s = [t[-1][1] for t in current_line]
    y1s = [t[-1][3] for t in current_line]
    inter = np.minimum(y1s, text[-1][3]) - np.maximum(y0s, text[-1][1])
    inter = np.maximum(inter, 0)
    union = np.maximum(y1s, text[-1][3]) - np.minimum(y0s, text[-1][1])
    iou = inter / union
    if iou.mean() > iou_threshold:
      current_line.append(text)
    else:
      current_line = sorted(current_line, key=lambda x: (x[-1][0] + x[-1][2]) / 2)
      current_line.append(''.join([w[0] for w in current_line]))
      grouped.append(current_line)
      current_line = [text]
  current_line = sorted(current_line, key=lambda x: (x[-1][0] + x[-1][2]) / 2)
  current_line.append(''.join([w[0] for w in current_line]))
  grouped.append(current_line)
  return grouped
