import yaml
from ..match import valid_from_match, valid_until_match
from .. import match
from .. import extract

class ValidDateFinder(yaml.YAMLObject):
  yaml_tag = u'!ValidDateFinder'
  def __init__(self):
    self.info = {}
    self.date_pairs = []

  def assign_dates(self, text, dates):
    

  def extract_same_line(self, texts):
    for i, text in enumerate(texts):
      if len(text.dates) == 2 and valid_from_match(text.all_text):
        date_pairs.append(tuple(text.dates))

  def extract_separate_lines(self, texts):
    for i, text in enumerate(texts):
      if valid_from_match(text.all_text) and len(text.dates) == 1:
        if len(texts[i + 1].dates) == 1:
          self.date_pairs.append((text.dates[0], texts[i + 1].dates[0]))
        if len(texts[i + 1].dates) == 0 and len(texts[i + 2].dates) == 1:
          self.date_pairs.append((text.dates[0], texts[i + 2].dates[0]))

  def assign_dates(self):
    

  def extract(self, texts):
    self.info.clear()
    self.extract_same_line(texts)
    self.extract_seperate_lines(texts)
    self.assign_dates()
