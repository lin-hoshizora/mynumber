import cv2
import numpy as np
import os

import time

def max_iou(boxes, target):
  boxes = np.array(boxes)
  target = np.array(target)
  areas = (boxes[:, 2] - boxes[:, 0] + 1) * (boxes[:, 3] - boxes[:, 1] + 1)
  area_target = (target[2] - target[0]) * (target[3] - target[1])
  inter_x1 = np.maximum(boxes[:, 0], target[0])
  inter_y1 = np.maximum(boxes[:, 1], target[1])
  inter_x2 = np.minimum(boxes[:, 2], target[2])
  inter_y2 = np.minimum(boxes[:, 3], target[3])
  inter_w = np.maximum(inter_x2 - inter_x1 + 1, 0)
  inter_h = np.maximum(inter_y2 - inter_y1 + 1, 0)
  inter_area = inter_w * inter_h
  iou = inter_area / (areas + area_target - inter_area)
  indices = np.argsort(iou)
  max_idx = indices[-1]
  max_v = iou[max_idx]
  return max_v, max_idx

def dilate(img, size=1, shape=cv2.MORPH_ELLIPSE, iterations=1):
  dilation = cv2.dilate(img, cv2.getStructuringElement(shape, (2*size+1, 2*size+1), (size, size)),
                        iterations=iterations)
  return dilation

def erode(img, size=1, shape=cv2.MORPH_ELLIPSE, iterations=1):
  erosion = cv2.erode(img, cv2.getStructuringElement(shape, (2*size+1, 2*size+1), (size, size)), iterations=iterations)
  return erosion

def dilate_erode(img, iterations=1, size=1):
  for _ in range(iterations):
    img = erode(dilate(img, size=size), size=size)
  return img

def sharpen(img, intensity=3.):
  blur = cv2.GaussianBlur(img, (0, 0), 3)
  img = cv2.addWeighted(img, intensity, blur, 1 - intensity, 0)
  return img

def merge(boxes):
  merged_boxes = []
  skip = [False] * len(boxes)
  for i in range(len(boxes)):
    if skip[i]: continue
    b1 = boxes[i]
    for j in range(i+1, len(boxes)):
      if skip[j]: continue
      b2 = boxes[j]
      if b2[0] < b1[0] < b2[2] or b1[0] <  b2[0] < b1[2]:
        v_iou = (min(b1[3], b2[3]) - max(b1[1], b2[1])) / (max(b1[3], b2[3]) - min(b1[1], b2[1]))
        if v_iou > 0.7:
          skip[j] = True
          b1[0] = min(b1[0], b2[0])
          b1[1] = min(b1[1], b2[1])
          b1[2] = max(b1[2], b2[2])
          b1[3] = max(b1[3], b2[3])
    merged_boxes.append(b1)
  return merged_boxes

def group_lines(texts: list, iou_threshold: float = 0.4):
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

def get_clahe(conf):
  conf["tileGridSize"] = tuple(conf["tileGridSize"])
  clahe = cv2.createCLAHE(**conf)
  return clahe

def draw_boxes(img, boxes, out_folder):
  path = str(out_folder / "boxes.jpg")
  img = img.copy()
  assert boxes.shape[1] == 4
  boxes = boxes.astype(int)
  for b in boxes:
    cv2.rectangle(img, (b[0], b[1]), (b[2], b[3]), (255, 0, 0), 2)
    cv2.imwrite(path, img[..., ::-1])

  now = time.localtime()
  name = ''
  for i in now[0:6]:
    name = name + str(i) + '-'
  cv2.imwrite('./debug/'+name+'.jpg',img[..., ::-1])

def save_chips(chips, out_folder):
  for idx, chip in enumerate(chips):
    cv2.imwrite(str(out_folder / f"{idx}.jpg"), chip[..., ::-1])

def box_crop(boxes, img, margin):
  boxes = boxes.astype(int)
  x1 = max(boxes[:, 0::2].min() - margin["x"][0], 0)
  x2 = min(boxes[:, 0::2].max() + margin["x"][1], img.shape[1] - 1)
  y1 = max(boxes[:, 1::2].min() - margin["y"][0], 0)
  y2 = min(boxes[:, 1::2].max() + margin["y"][1], img.shape[0] - 1)
  crop = img[y1:y2, x1:x2]
  return crop, (x1, y1, x2, y2)

def save_scope(scope, save_path):
  with open(save_path, "w") as f:
    f.write(",".join([str(x) for x in scope]))
    f.flush()
    os.fdatasync(f.fileno())
    

def read_scope(file_path):
  with open(file_path) as f:
    scope = tuple(int(x) for x in f.read().strip("\n").split(","))
  return scope
