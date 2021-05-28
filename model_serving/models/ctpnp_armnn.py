import numpy as np
import pyarmnn as ann
from .ctpnp_base import CTPNPBase

class CTPNP_ARMNN(CTPNPBase):
  def __init__(self, model_path: str, runtime, logger, **kwargs):
    super().__init__(logger, **kwargs)
    if model_path.endswith('.tflite'):
      self.parser = ann.ITfLiteParser()
      self.net = self.parser.CreateNetworkFromBinaryFile(model_path)
    else:
      raise NotImplementedError('Only tflite is supported')
    self.graph_id = 0
    self.nodes_in = self.parser.GetSubgraphInputTensorNames(self.graph_id)
    assert len(self.nodes_in) == 1, f'{len(self.nodes_in)} inputs found, 1 expected'
    self.input_binding_info = self.parser.GetNetworkInputBindingInfo(self.graph_id, self.nodes_in[0])
    self.nodes_out = self.parser.GetSubgraphOutputTensorNames(self.graph_id)
    assert len(self.nodes_out) == 3, f'{len(self.nodes_out)} outputs found, 3 expected'
    self.output_binding_infos = [self.parser.GetNetworkOutputBindingInfo(self.graph_id, n) for n in self.nodes_out]
    self.output_tensors = ann.make_output_tensors(self.output_binding_infos)
    self.infer_idx = runtime.get_infer_idx()
    self.runtime = runtime.runtime
    self.backend = ann.BackendId(kwargs.get('backend', 'CpuAcc'))
    self.logger.info('CTPNP uses ARMNN backend:', self.backend)
    opt_options = ann.OptimizerOptions()
    if self.backend == 'GpuAcc':
      opt_options.m_ReduceFP32ToFp16 = True
    opt_net, messages = ann.Optimize(self.net, [self.backend], self.runtime.GetDeviceSpec(), opt_options)
    self.net_id, _ = self.runtime.LoadNetwork(opt_net)
    self.input_shape = tuple(self.input_binding_info[1].GetShape())
    self.input_h = self.input_shape[1]
    self.input_w = self.input_shape[2]

  def infer_sync(self, img: np.ndarray, suppress_lines: bool = True):
    feed = self.preprocess(img, nchw=False)[0]
    input_tensors = ann.make_input_tensors([self.input_binding_info], [feed])

    import time
    t0 = time.time()

    self.runtime.EnqueueWorkload(self.net_id, input_tensors, self.output_tensors)
    
    # print(f'ctpnp enqueue time: {(time.time() - t0):.2f}s')

    cls_pred, cnt_pred, box_pred = ann.workload_tensors_to_ndarray(self.output_tensors)
    # exp is not supported in ARMNN 20.02
    box_pred = np.exp(box_pred)
    lines = self.parse_result(cls_pred, cnt_pred, box_pred, suppress_lines=suppress_lines)
    return lines
