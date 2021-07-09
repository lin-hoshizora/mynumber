"""A date class that can output string in different formats"""
ERA_OFFSET = {
    "m": 1867,
    "t": 1911,
    "s": 1925,
    "h": 1988,
    "r": 2018,
    "w": 0,
}


class Date:
  """Date class to hold year, month, day, and can output date string.

  Supported formats of output string:
    1. western style in digits
    2. short form used in mynumber card PIN generation

  Typical usage example:
    >>> d1 = Date(year="2021", month="1", date="22", era="w")
    >>> print(d1)
    20210122
    >>> print(d1.western_str())
    20210122
    >>> print(d1.mynum_str())
    210122
    >>> d2 = Date(year="3", month="2", date="22", era="h")
    >>> print(d2)
    19910222
    >>> print(d2.western_str())
    19910222
    >>> print(d2.mynum_str())
    030222

  Args:
    year: Year digits in string
    month: Month digits in string
    date: Day digits in string
    era: Japanese era tag in string.
        (m: 明治, t: 大正, s: 昭和, h: 平成, r: 令和, w: 西暦)
  """
  def __init__(self, year: str, month: str, date: str, era: str):
    self.m = month
    self.d = date
    self.y = str(int(year) + ERA_OFFSET[era])
    self.jpy = year if era != "w" else None

  def western_str(self):
    """Generates date string using western year."""
    date_str = self.y + self.m.zfill(2) + self.d.zfill(2)
    return date_str

  def mynum_str(self):
    """Generates string for MyNumber card verification."""
    if self.jpy is None:
      date_str = self.y[-2:] + self.m.zfill(2) + self.d.zfill(2)
    else:
      date_str = self.jpy.zfill(2) + self.m.zfill(2) + self.d.zfill(2)
    return date_str

  def __repr__(self):
    return self.western_str()

  def __str__(self):
    return self.western_str()
