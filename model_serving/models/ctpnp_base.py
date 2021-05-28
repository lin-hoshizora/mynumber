import numpy as np
from .utils.image import resize_ar, nms, get_rect

class CTPNPBase:
  """
  CTPN-Pixel Base Class
  """
  def __init__(self, logger, **kwargs):
    self.logger = logger
    self.min_score = kwargs.get('min_score', 0.2)
    self.stride = kwargs.get('stride', 4)
    self.iou_th = kwargs.get('iou_th', 0.5)
    self.min_h = kwargs.get('min_h', 16)
    self.max_hgap = kwargs.get('max_hgap', 32)
    self.min_voverlap = kwargs.get('min_voverlap', 0.7)
    self.min_size_sim = kwargs.get('min_size_sim', 0.7)
    self.ratio = None
    self.ori_shape = None

  def preprocess(self, img: np.ndarray, nchw: bool = True):
    self.ori_shape = img.shape
    resized, self.ratio = resize_ar(img, self.input_w, self.input_h)
    resized = resized.astype(np.float32) / 127.5 - 1
    feed = resized.transpose(2, 0, 1) if nchw else resized
    feed = feed[np.newaxis, ...]
    return feed

  def parse_result(self, cls_pred: np.ndarray, cnt_pred: np.ndarray, box_pred: np.ndarray, suppress_lines: bool = True):
    scores = cnt_pred * cls_pred
    yy, xx = np.where(scores[0, ..., 0] > self.min_score)
    top_bot = box_pred[scores[..., 0] > self.min_score]
    scores = scores[scores > self.min_score]
    if scores.size == 0:
      return np.array([]), np.array([])

    real_x1 = xx * self.stride
    real_x2 = real_x1 + self.stride
    real_yc = yy * self.stride + self.stride / 2
    real_y1 = real_yc - top_bot[:, 0]
    real_y2 = real_yc + top_bot[:, 1]
    real_boxes = np.concatenate([
      real_x1[:, np.newaxis],
      real_y1[:, np.newaxis],
      real_x2[:, np.newaxis],
      real_y2[:, np.newaxis]
    ], axis=1)

    hs = real_boxes[:, 3] - real_boxes[:, 1]
    real_boxes = real_boxes[hs > self.min_h]
    scores = scores[hs > self.min_h]

    final_boxes, final_scores = nms(real_boxes, scores, self.iou_th)
    final_boxes /= self.ratio
    lines = self._graph_connect(final_boxes, final_scores, tuple(self.ori_shape[:2]))
    if suppress_lines:
      lines = self.suppress_lines(lines)
    return lines, final_boxes

  def suppress_lines(self, lines: list):
    suppressed = []
    rects = get_rect(lines)
    merged = []
    for idx1, l1 in enumerate(lines):
      skip = False
      r1 = rects[idx1]
      a1 = (r1[3] - r1[1]) * (r1[2] - r1[0])
      for idx2, l2 in enumerate(lines):
        if (l1 == l2).all():
          continue
        r2 = rects[idx2]
        a2 = (r2[3] - r2[1]) * (r2[2] - r2[0])
        if a2 < a1:
          continue
        inter_x0 = max(r1[0], r2[0])
        inter_x1 = min(r1[2], r2[2])
        inter_y0 = max(r1[1], r2[1])
        inter_y1 = min(r1[3], r2[3])
        inter_area = max(inter_x1 - inter_x0, 0) * max(inter_y1 - inter_y0, 0)
        if inter_area / a1 > 0.5:
          skip = True
          continue
        if (inter_y1 - inter_y0) / (max(r1[3], r2[3]) - min(r1[1], r2[1])) > 0.7 and r1[0] < r2[0] < r1[2] < r2[2]:
          lines[idx1][2:6] = l2[2:6]
          merged.append(idx2)
      if not skip and idx1 not in merged:
        suppressed.append(idx1)
    suppressed = np.array([lines[idx] for idx in suppressed if idx not in merged])
    return suppressed

  def _check(self, h1: int, h2: int, box: np.ndarray, adj_box: np.ndarray):
    # vertial IOU
    u_y0 = min(box[1], adj_box[1])
    u_y1 = max(box[3], adj_box[3])
    i_y0 = max(box[1], adj_box[1])
    i_y1 = min(box[3], adj_box[3])
    v_iou = max(i_y1 - i_y0, 0) / (u_y1 - u_y0)
    # size similarity
    size_sim = min(h1, h2) / max(h1, h2)
    valid = v_iou >= self.min_voverlap and size_sim >= self.min_size_sim
    return valid

  def _graph_connect(self, boxes: np.ndarray, scores: np.ndarray, size: tuple):
    boxes[:, 0] = np.clip(boxes[:, 0], a_min=0, a_max=size[1] - 1)
    boxes[:, 1] = np.clip(boxes[:, 1], a_min=0, a_max=size[0] - 1)
    boxes[:, 2] = np.clip(boxes[:, 2], a_min=0, a_max=size[1] - 1)
    boxes[:, 3] = np.clip(boxes[:, 3], a_min=0, a_max=size[0] - 1)
    box_heights = boxes[:, 3] - boxes[:, 1]
    x_groups = [[] for _ in range(size[1])]
    for i, box in enumerate(boxes):
      x_groups[int(box[0])].append(i)
    graph = np.zeros((boxes.shape[0], boxes.shape[0]), np.bool)
    for i, box in enumerate(boxes):
      # look for successive boxes
      succ_indices = []
      start = max(int(box[0] + 1), 0)
      end = min(int(box[0] + self.max_hgap + 1), size[1])
      for x in range(start, end):
        for adj_idx in x_groups[x]:
          if self._check(box_heights[i], box_heights[adj_idx], box, boxes[adj_idx]):
            succ_indices.append(adj_idx)
        if len(succ_indices) != 0:
          break
      if len(succ_indices) == 0:
        continue
      # get index of successive box with highest score
      succ_idx = succ_indices[np.argmax(scores[succ_indices])]
      succ_box = boxes[succ_idx]
      # look for precursive boxes
      prec_indices = []
      start = max(int(succ_box[0] - 1), 0)
      end = max(int(succ_box[0] - 1 - self.max_hgap), 0)
      for x in range(start, end, -1):
        for adj_idx in x_groups[x]:
          if self._check(box_heights[succ_idx], box_heights[adj_idx], succ_box, boxes[adj_idx]):
            prec_indices.append(adj_idx)
        if len(prec_indices) > 0:
          break
      if not prec_indices:
        continue
      if scores[i] >= np.max(scores[prec_indices]):
        graph[i, succ_idx] = True
    # group text lines
    line_groups = []
    for i in range(graph.shape[0]):
      if not graph[:, i].any() and graph[i, :].any():
        line_groups.append([i])
        v = i
        while graph[v, :].any():
          v = np.where(graph[v, :])[0][0]
          line_groups[-1].append(v)
    text_lines = np.zeros((len(line_groups), 9), np.float32)
    for line_idx, box_indices in enumerate(line_groups):
      line_boxes = boxes[box_indices]
      if line_boxes.shape[0] == 1:
        x0, x1 = line_boxes[0, 0], line_boxes[0, 2]
        top_y0, top_y1 = line_boxes[0, 1], line_boxes[0, 1]
        bot_y0, bot_y1 = line_boxes[0, 3], line_boxes[0, 3]
      else:
        x0 = np.min(line_boxes[:, 0])
        x1 = np.max(line_boxes[:, 2])
        top = np.poly1d(np.polyfit(line_boxes[:, 0], line_boxes[:, 1], 1))
        bot = np.poly1d(np.polyfit(line_boxes[:, 2], line_boxes[:, 3], 1))
        top_y0, top_y1 = top(x0), top(x1)
        bot_y0, bot_y1 = bot(x0), bot(x1)
      score = np.mean(scores[list(box_indices)])
      text_lines[line_idx] = np.array([x0, top_y0, x1, top_y1, x1, bot_y1, x0, bot_y0, score])
    return text_lines

  def infer_sync(self, img: np.ndarray, suppress_lines: bool = True, x_mask: float = 1e9, y_mask: float = 0):
    raise NotImplementedError
