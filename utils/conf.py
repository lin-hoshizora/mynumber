import yaml

def load_conf(path, encoding="utf-8"):
  with open(path, encoding=encoding) as f:
    config = yaml.safe_load(f)
  return config
