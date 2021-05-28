import numpy as np

def get_date_roi(mark_x, mark_y, w, h):
  x1 = max(mark_x - 790, 0)
  x2 = min(mark_x + 50, w - 1)
  y1 = min(mark_y + 245, h - 1)
  y2 = min(mark_y + 325, h - 1)
  box = np.array([x1, y1, x2, y2])
  return box

def get_num_roi(mark_x, mark_y, w, h):
  x1 = max(mark_x - 900, 0)
  x2 = max(mark_x - 740, 0)
  y1 = min(mark_y + 755, h - 1)
  y2 = min(mark_y + 855, h - 1)
  box = np.array([x1, y1, x2, y2])
  return box

