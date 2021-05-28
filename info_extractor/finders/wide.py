import yaml
import numpy as np
from .. import match as m
from ..match import score
from .. import extract as e


class WideFinder(yaml.YAMLObject):
  yaml_tag = u'!WideFinder'
  def __init__(self, match_method, extract_method):
    self.mf = getattr(m, match_method)
    self.ef = getattr(e, extract_method)
    self.scores = np.array([])
    self.texts = []

  def extract(self, texts):
    self.scores, self.texts = score(self.mf, texts)
    for idx in reversed(self.scores.argsort()):
      if self.scores[idx] == 0: break
      res = self.ef(self.texts[idx])
      if res: return res
