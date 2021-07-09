"""A finder to extract 適用区分 and 負担割合 from OCR results"""
from typing import List, Any, Union
import yaml
from ..re_pattern import PERCENT_SINGLE_DIGIT, PERCENT, PERCENT_TAG, DIV_TAG, KBN, GEN


class RouFtnKbnFinder(yaml.YAMLObject):
  """A finder class to extract 負担区分 and 負担割合 from OCR results.

  NOTE: 適用区分 and 負担割合 are considered as the same item for output.

  Typical usage example:
    >>> finder = RouFtnKbnFinder()
    >>> res = finder.extract([["適用区分Ⅳ"]])
    >>> print(res)
    Ⅳ
  """
  yaml_tag = u'!RouFtnKbnFinder'
  def extract(self, texts: List[List[Any]]) -> Union[str, None]:
    """Extracts 負担区分 and 負担割合 from text lines.

    Args:
      texts: OCR results in a list, each element of each has also to be a
        list, each element of which is the text for each detected line.

    Returns:
      A string of 負担区分 and 負担割合 if anything extracted, `None` otherwise.
    """
    #pylint: disable=too-many-nested-blocks
    self.info = {}
    for idx_l, line in enumerate(texts):
      single_num = PERCENT_SINGLE_DIGIT.findall(line[-1])
      if single_num:
        self.info['RouFtnKbn'] = single_num[0][1] + "割"
        break
      cat = PERCENT.findall(line[-1])
      if cat:
        self.info['RouFtnKbn'] = cat[0]
        break

      if PERCENT_TAG.search(line[-1]):
        # num displacement
        if line[-1].endswith('割'):
          if idx_l > 0:
            prev_line = texts[idx_l - 1][-1]
            if prev_line.isdigit() and len(prev_line) == 1:
              self.info['RouFtnKbn'] = prev_line + '割'
              break
          if idx_l < len(texts) - 1:
            next_line = texts[idx_l + 1][-1]
            if next_line.isdigit() and len(next_line) == 1:
              self.info['RouFtnKbn'] = next_line + '割'
              break
      cap = DIV_TAG.findall(line[-1])
      if cap:
        convert1 = {
            'i': 'Ⅰ',
            '1': 'Ⅰ',
            'l': 'Ⅰ',
            'v': 'Ⅴ',
        }
        convert2 = {
            'ii': 'Ⅱ',
            'II': 'Ⅱ',
            'iv': 'Ⅳ',
            '1v': 'Ⅳ',
            'lv': 'Ⅳ',
            'vi': 'Ⅵ',
            'v1': 'Ⅵ',
            'vl': 'Ⅵ',
        }
        convert3 = {
            'iii': 'Ⅲ',
            'lll': 'Ⅲ',
            'III': 'Ⅲ',
            'II': 'Ⅱ',
            'IV': 'Ⅳ',
            'VI': 'Ⅵ',
            'V': 'Ⅴ',
            'I': 'Ⅰ',
            'ァ': 'ア',
            'ィ': 'イ',
            'ゥ': 'ウ',
            'ェ': 'エ',
            '工': 'エ',
            'ォ': 'オ',
        }
        if len(line[-1]) >= len(cap[0]) + 1:
          kbn = line[-1][line[-1].index(cap[0]) + len(cap[0]):]
          for cvt in [convert3, convert2, convert1]:
            for k in cvt:
              if k in kbn:
                kbn = kbn.replace(k, cvt[k])
          for key_word in 'アイウエオ':
            if key_word in kbn:
              kbn = key_word
              break
          self.info['RouFtnKbn'] = kbn
          break

        if idx_l > 0:
          print(f'RouFtnKbn not found in the same line with tag, '
                f'check the line above')
          cat = KBN.findall(texts[idx_l - 1][-1])
          if not cat:
            cat = GEN.findall(texts[idx_l - 1][-1])
          if cat:
            kbn = cat[0]
            for cvt in [convert3, convert2, convert1]:
              for k in cvt:
                if k in kbn:
                  kbn = kbn.replace(k, cvt[k])

            for key_word in 'アイウエオ':
              if key_word in kbn:
                kbn = key_word
                break
            self.info['RouFtnKbn'] = kbn
            break

        if idx_l < len(texts) - 1:
          print(f'RouFtnKbn not found in the same line with tag, '
                f'check the line below')
          cat = KBN.findall(texts[idx_l + 1][-1])
          if not cat:
            cat = GEN.findall(texts[idx_l + 1][-1])
          if cat:
            kbn = cat[0]
            for cvt in [convert3, convert2, convert1]:
              for k in cvt:
                if k in kbn:
                  kbn = kbn.replace(k, cvt[k])

            for key_word in 'アイウエオ':
              if key_word in kbn:
                kbn = key_word
                break
            self.info['RouFtnKbn'] = kbn
            break
    if "RouFtnKbn" not in self.info:
      self.info["RouFtnKbn"] = None
    return self.info["RouFtnKbn"]
