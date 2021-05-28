from ..extract import get_date, get_num, get_insurer_num


class Word:
  def __init__(self, word):
    self.text = word[0]
    self.probs = word[1]
    self.positions = word[2]
    self.bbox = word[3].astype(int)

  def prob_lower_than(self, threshold, method="any"):
    res = self.probs < threhold
    return getattr(res, method)()

class TextLine:
  def __init__(self, text):
    words, self.all_text = text[:-1], text[-1]
    self.words = [Word(w) for w in words]
    self.dates = get_date(self.all_text)
    self.any_num = get_num(self.all_text)
    self.hknja_num = get_insurer_num(self.all_text)
    self.len = len(self.all_text)
