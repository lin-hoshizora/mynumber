import pyarmnn as ann

class Runtime:
  def __init__(self):
    options = ann.CreationOptions()
    self.runtime = ann.IRuntime(options)
    self.infer_idx = 0

  def get_infer_idx(self):
    prev = self.infer_idx
    self.infer_idx += 1
    return prev
