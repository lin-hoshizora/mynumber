import numpy as np
import cv2
from .utils.general import softmax, greedy_decode
from .utils.image import resize_h

class Dense8Base:
  """
  DenseNet8 Inference Class
  """
  def __init__(self, logger, **kwargs):
    self.logger = logger
    self.input_len = None
    self.ratio = None

  def preprocess(self, img, nchw=True):
    self.ratio = self.input_h / img.shape[0]
    img_pad, img_resize = resize_h(img, h=self.input_h, w=self.input_w, logger=self.logger)
    if nchw:
      img_pad = img_pad.transpose(2, 0, 1)
    img_pad = img_pad[np.newaxis, ...].astype(np.float32)
    self.input_len = img_resize.shape[1] // (self.input_h // 4)
    return img_pad

  def parse_result(self, logits, num_only):
    logits = logits.reshape(logits.shape[1], logits.shape[-1])
    if len(logits.shape) == 4:
      logits = logits.transpose(1, 0)
    if num_only:
      logits_num = np.zeros_like(logits)
      num_indices = [1,6,17,31,34,42,46,49,50,39, logits.shape[-1]-1]
      logits_num[:, num_indices] = logits[:, num_indices]
      #probs = softmax(logits_num)
      probs = logits_num
    else:
      #probs = softmax(logits)
      probs = logits
    codes, probs, positions = greedy_decode(probs, self.input_len)
    positions = (positions * (self.input_h // 4) + (self.input_h // 8)) / self.ratio
    return codes, probs, positions

  def infer_sync(self, img, num_only=False):
    raise NotImplementedError
