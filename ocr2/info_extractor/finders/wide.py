"""A finder that extracts information from lines near a matched pattern"""
import yaml
import numpy as np
from .. import match as m
from ..match import score
from .. import extract as e


class WideFinder(yaml.YAMLObject):
  """A finder that extracts information from lines near matched patterns.

  It matches a pattern in each given line, and tries to extract information
  from the line where the pattern is sucessfully matched. If nothing can be
  extracted, it will try the line above and the line below.

  YAMLObject: This class can be saved as a YAML file for reuse.

  Typical usage example:
    >>> finder = WideFinder(
          match_method="birthday_match",
          extract_method="get_date"
        )
    >>> print(finder.extract([["生年月日1960年12月12日"], ["another line"]]))
    [19601212]
    >>> print(finder.extract([["生年月日"], ["1960年12月12日"]]))
    [19601212]

  Args:
    match_method: Name of the function for pattern matching, which has to be
        defined in `..match`
    extract_method: Name of the function for information extraction, which has
        to be defined in `..extract`
  """
  yaml_tag = u'!WideFinder'
  def __init__(self, match_method: str, extract_method: str):
    self.mf = getattr(m, match_method)
    self.ef = getattr(e, extract_method)
    self.scores = np.array([])
    self.texts = []

  def extract(self, texts):
    self.scores, self.texts = score(self.mf, texts)
    print(self.scores,self.mf)
    for idx in (-self.scores).argsort(kind="meregesort"):
      if self.scores[idx] == 0: break
      res = self.ef(self.texts[idx])
      if res: return res
    return None
