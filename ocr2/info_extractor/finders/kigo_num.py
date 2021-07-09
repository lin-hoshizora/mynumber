"""A finder to extract 記号番号 from OCR results"""
from typing import List, Any
import yaml
from ..extract import get_kigo_num, get_kigo, get_num


def preprocess(line):
  text = line[-1].replace('ー', '-').replace('一', '-')
  return text

class KigoNumFinder(yaml.YAMLObject):
  """A finder class to extract 記号番号 from text lines output by OCR.

  Typical usage example:
    >>> finder = KigoNumFinder()
    >>> res = finder.extract([[[], "記号123番号456"]])
    >>> print(res["Kigo"])
    123
    >>> print(res["Num"])
    456
  """
  yaml_tag = u'!KigoNumFinder'
  def extract(self, texts: List[List[Any]]) -> dict:
    """Extracts 記号番号 from text lines.

    Args:
      texts: OCR results in a list, each element of each has also to be a
        list, each element of which is the text for each detected line.

    Returns:
      A dict with extracted Kigo and Num, value of each of which is `None`
      if nothing can be extracted.
    """
    self.info = {"Kigo": None, "Num": None}
    texts = list(map(preprocess, texts))
    # kigo num in the same line
    for text in texts:
      res = get_kigo_num(text)
      if res is not None:
        if isinstance(res, str): self.info["Num"] = res
        if isinstance(res, tuple):
          self.info["Kigo"] = res[0]
          self.info["Num"] = res[1]

    if self.info["Num"] is not None: return self.info

    # kigo num in two lines
    for idx in range(len(texts) - 1):
      res_kigo = get_kigo(texts[idx])
      res_num = get_num(texts[idx + 1])
      if isinstance(res_kigo, str) and isinstance(res_num, str):
        self.info["Kigo"] = res_kigo
        self.info["Num"] = res_num
        return self.info
    return self.info
