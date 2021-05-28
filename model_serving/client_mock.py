import time
import yaml
from .models import DBNetArmNN, Dense8ArmNN
from .utils import ArmNNRuntime

class ModelClientMock:
  def __init__(self, logger):
    with open('config/model_server_config.yaml', encoding='utf-8') as f:
      self.config = yaml.safe_load(f)
    with open('config/err.yaml', encoding='utf-8') as f:
      self.err = yaml.safe_load(f)
    self.logger = logger
    common_setting = {"logger": logger, "runtime": ArmNNRuntime()}
    self.dbnet = {
      'landscape': DBNetArmNN(
        **self.config['dbnet']['armnn']['landscape'],
        **common_setting,
      ),
      'portrait': DBNetArmNN(
        **self.config['dbnet']['armnn']['portrait'],
        **common_setting,
      )
    }
    self.dense = {}
    dense_config = self.config['dense8']['armnn']
    backend = dense_config['backend']
    for path in dense_config["model_path"]:
      model = Dense8ArmNN(path, backend=backend, **common_setting)
      self.dense[int(model.input_w)] = model
      self.height = model.input_h

  def infer_sync(self, sess_id, network, img, key=None, num_only=None, layout=None, suppress_lines=None):
    if network == 'DBNet':
      t0 = time.time()
      boxes, scores, angle = self.dbnet[layout].infer_sync(img)
      self.logger.debug(f'DBnet total: {time.time() - t0:.3f}s')
      return boxes, scores, angle
    elif network == 'Dense':
      codes, probs, positions = self.dense[key].infer_sync(img, num_only=num_only)
      return codes, probs, positions
    else:
      raise ValueError(f"{network} is not implemented")
