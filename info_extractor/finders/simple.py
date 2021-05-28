import yaml
from .. import match as m
from .. import extract as e


class SimpleFinder(yaml.YAMLObject):
  yaml_tag = u'!SimpleFinder'
  def __init__(self, match_method, extract_method):
    self.match_method = match_method
    self.extract_method = extract_method

  def match_one(self, texts):
    for line in texts:
      mf = getattr(m, self.match_method)
      ret, text = mf(line[-1])
      if ret:
        return text

  def extract(self, texts):
    text = self.match_one(texts)
    if text is not None:
      res = getattr(e, self.extract_method)(text)
      return res
