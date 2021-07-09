"""Helper functions for OpenVINO"""
from pathlib import Path
from openvino.inference_engine import IECore

def get_openvino_dir() -> Path:
  """Gets root dir of OpenVINO."""
  home_install = Path.home()/'intel/openvino/'
  sys_install = Path('/opt/intel/openvino/')
  if sys_install.exists():
    return sys_install
  return home_install


def get_ie_core(dev: str) -> IECore:
  """Gets IRCore for OpenVINO inference.

  Args:
    dev: Name of inference hardware.

  Returns:
    An IECore object.
  """
  ie_core = IECore()
  if dev == 'CPU':
    ext_path = (get_openvino_dir() /
                'inference_engine/lib/intel64/libcpu_extension_sse4.so')
    if ext_path.exists():
      ie_core.add_extension(str(ext_path), dev)
  return ie_core
