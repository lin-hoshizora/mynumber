from info_extractor.re_pattern import LAST_DAY


ERA_OFFSET = {
  "m": 1867,
  "t": 1911,
  "s": 1925,
  "h": 1988,
  "r": 2018,
  "w": 0,
}

MONTH_LAST_DAY = {
    '01':'31',
    '02':'28',
    '03':'31',
    '04':'30',
    '05':'31',
    '06':'30',
    '07':'31',
    '08':'31',
    '09':'30',
    '10':'31',
    '11':'30',
    '12':'31',
}


class Date:
  def __init__(self, year, month, date, era):
    self.m = month
    self.d = date
    self.y = str(int(year) + ERA_OFFSET[era])
    self.jpy = year if era != "w" else None
    self.check_last_day()

  def western_str(self):
    date_str = self.y + self.m.zfill(2) + self.d.zfill(2)
    return date_str

  def mynum_str(self):
    """ Generate string for MyNumber Car verification
    """
    if self.jpy is None:
      date_str = self.y[-2:] + self.m.zfill(2) + self.d.zfill(2)
    else:
      date_str = self.jpy.zfill(2) + self.m.zfill(2) + self.d.zfill(2)
    return date_str

  def __repr__(self):
    return self.western_str()

  def __str__(self):
    return self.western_str()

  def check_last_day(self):
    if str(self.d) == '99':
      if str(self.m.zfill(2)) == '02' and int(self.y)%4 ==0:
          self.d=29
      else:
          self.d = MONTH_LAST_DAY[str(self.m.zfill(2))]

