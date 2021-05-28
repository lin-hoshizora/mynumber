try:
  from .ctpnp_openvino import CTPNP_OpenVINO
  from .dense8_openvino import Dense8_OpenVINO
except ModuleNotFoundError:
  print('OpenVINO not installed')

try:
  from .dbnet_armnn import DBNetArmNN
  from .dense8_armnn import Dense8ArmNN
except ModuleNotFoundError:
  print('PyArmNN is not installed')
