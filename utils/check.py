from pathlib import Path


def ensure_type(v, t, msg=""):
  if not isinstance(v, t):
    raise TypeError(msg)


def valid_path(p):
  suffix = 0
  while p.exists():
    p = Path(str(p).replace(p.stem, p.stem + str(suffix)))
  return p


def validate_json(msg):
  if 'Scan' in msg or 'Patient' in msg or 'MyNumber' in msg:
    return True
  return False
