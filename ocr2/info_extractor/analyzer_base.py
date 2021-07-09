"""A base class for analyzers.

This class implements the common methods shared among all analyzers.
"""
from pathlib import Path
from typing import Any, Union
import yaml


def load_finder(tag: str, category: str) -> Any:
  """Loads a predefined finder from YAML

  Args:
    tag: A string indicating what item the finder extracts
    category: A string indicating the type of the finder.
        e.g. wide_finder

  Returns:
    A finder with an extract method that can be used in
    `AnalyzerBase._finder_fit`.
  """
  path = (Path(__file__).resolve().parent /
          "presets" / category / (tag.lower() + ".yaml"))
  with open(str(path)) as f:
    obj = yaml.load(f, Loader=yaml.Loader)
  return obj

class AnalyzerBase:
  """Base class for all analyzer classes.

  Args:
    config: a dict specifying to use which finder for which item
  """
  def __init__(self, config: dict):
    self.texts = []
    self.info = {}
    self.config = config
    self.finders = {}
    for tag, cat in self.config.items():
      if not isinstance(cat, str):
        self.finders[tag] = cat
        continue
      if isinstance(tag, str):
        self.finders[tag] = load_finder(tag, cat)
      elif isinstance(tag, tuple):
        self.finders[tag] = load_finder(cat, cat)

  def _finder_fit(self, texts):
    self.texts = texts
    self.info = {}
    for tag in self.finders:
      if isinstance(tag, str):
        self.info[tag] = self.finders[tag].extract(texts)
      if isinstance(tag, tuple):
        for k, v in self.finders[tag].extract(texts).items():
          self.info[k] = v

  def _have(self, tag):
    return self.info.get(tag, None) is not None

  def get(self, tag: str) -> Union[str, None]:
    """Gets extracted information for a certain item.

    Args:
      tag: Name of the item to get.

    Returns:
      A string if required item was extracted sucessfully,
      `None` otherwise.
    """
    return self.info.get(tag, None)
