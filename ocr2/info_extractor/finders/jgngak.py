"""A finder to extract 限度額 from OCR results"""
from typing import List, Any, Union
import yaml
from ..re_pattern import DEDUCTIBLE_TAG, DEDUCTIBLE_AMT, DEDUCTIBLE_WITH_TAG, DEDUCTIBLE_TAGS


class JgnGakFinder(yaml.YAMLObject):
  """A finder class to extract 限度額 from text lines output by OCR.

  Typical usage example:
    >>> finder = JgnGakFinder()
    >>> res = finder.extract([
            ["限度額"],
            ["通院1,000円/月"],
            ["入院1,000円/月"],
        ])
    >>> print(res)
    通院 1,000;入院 1,000;
  """
  yaml_tag = u'!JgnGakFinder'

  def _get_amount(self, line):
    limit = DEDUCTIBLE_AMT.findall(line[-1])
    if limit:
      self.info['JgnGak'] = limit[0].replace('o', '0')
      if self.info['JgnGak'][0] == '0' and len(self.info["JgnGak"]) > 1:
        self.info['JgnGak'] = '1' + self.info['JgnGak']
      return self.info['JgnGak']
    return None

  def _get_multi(self, texts: List[List[Any]]) -> str:
    """Extracts multile deductible values if possible.

    e.g. 入院 and 入院外 each has a deductible

    Args:
      texts: OCR results in a list, each element of each has also to be a
        list, each element of which is the text for each detected line.

    Returns:
      A string containing multiple 限度額 if any, empty string otherwise.
    """
    flags = [True for _ in range(len(DEDUCTIBLE_TAGS))]
    res = ""
    for line in texts:
      for idx, (tag, pattern, need) in enumerate(zip(
          DEDUCTIBLE_TAGS,
          DEDUCTIBLE_WITH_TAG,
          flags
      )):
        if not need: continue
        matched = pattern.findall(line[-1])
        if matched and matched[0] is not None:
          res += tag + " " + matched[0].replace('o', '0') + ";"
          flags[idx] = False
    return res

  def extract(self, texts: List[List[Any]]) -> Union[str, None]:
    """Extracts 限度額 from text lines if possible.

    Args:
      texts: OCR results in a list, each element of each has also to be a
        list, each element of which is the text for each detected line.

    Returns:
      A string of 限度額 if anything extracted, `None` otherwise.
    """
    self.info = {}

    multi_res = self._get_multi(texts)
    if multi_res: return multi_res

    for line in texts:
      if DEDUCTIBLE_TAG.search(line[-1]):
        amount = self._get_amount(line)
        if amount: return amount

    print('JgnGak with tag not found, search yen in each line')
    for line in texts:
      amount = self._get_amount(line)
      if amount: return amount

    if "JgnGak" not in self.info:
      self.info["JgnGak"] = None
    return None
