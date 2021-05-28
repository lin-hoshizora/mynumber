ERA_OFFSET = {
  "m": 1867,
  "t": 1911,
  "s": 1925,
  "h": 1988,
  "r": 2018,
  "w": 0,
}

class Date:
  def __init__(self, year, month, date, era):
    self.m = month
    self.d = date
    self.y = str(int(year) + ERA_OFFSET[era])
    self.jpy = year if era != "w" else None

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
