import yaml
from ..re_pattern import DEDUCTIBLE_TAG, DEDUCTIBLE_AMT, DEDUCTIBLE_WITH_TAG, DEDUCTIBLE_TAGS


class JgnGakFinder(yaml.YAMLObject):
  yaml_tag = u'!JgnGakFinder'

  def _get_amount(self, line):
    limit = DEDUCTIBLE_AMT.findall(line[-1])
    if limit:
      self.info['JgnGak'] = limit[0].replace('o', '0')
      if self.info['JgnGak'][0] == '0' and len(self.info["JgnGak"]) > 1:
        self.info['JgnGak'] = '1' + self.info['JgnGak']
      return self.info['JgnGak']

  def _get_multi(self, texts):
    flags = [True for _ in range(len(DEDUCTIBLE_TAGS))]
    res = ""
    for line in texts:
      for idx, (tag, pattern, need) in enumerate(zip(DEDUCTIBLE_TAGS, DEDUCTIBLE_WITH_TAG, flags)):
        if not need: continue
        matched = pattern.findall(line[-1])
        #print(line[-1], matched)
        if matched and matched[0] is not None:
          res += tag + " " + matched[0].replace('o', '0') + ";"
          flags[idx] = False
    return res

  def extract(self, texts):
    self.info = {}

    multi_res = self._get_multi(texts)
    #print("multi res:", multi_res)
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
