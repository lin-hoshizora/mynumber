from pathlib import Path
import pyarmnn as ann
from .dense8_base import Dense8Base

class Dense8ArmNN(Dense8Base):
  """
  ARMNN wrapper for Dense8 inference
  """
  def __init__(self, model_path, runtime, logger, **kwargs):
    super().__init__(logger, **kwargs)
    self.parser = ann.ITfLiteParser()
    netIdx = 0
    if Path(model_path).exists():
      self.net = self.parser.CreateNetworkFromBinaryFile(model_path)
    else:
      self.net = getattr(self.parser, "Create" + model_path)()
      if "192" in model_path: netIdx = 1
      if "1024" in model_path: netIdx = 2
      if "1408" in model_path: netIdx = 3
    self.graph_id = 0
    self.nodes_in = self.parser.GetSubgraphInputTensorNames(self.graph_id)
    assert len(self.nodes_in) == 1, f'{len(self.nodes_in)} inputs found, 1 expected'
    self.input_binding_info = self.parser.GetNetworkInputBindingInfo(self.graph_id, self.nodes_in[0])
    self.nodes_out = self.parser.GetSubgraphOutputTensorNames(self.graph_id)
    assert len(self.nodes_out) == 1, f'{len(self.nodes_out)} outputs found, 1 expected'
    self.output_binding_infos = [self.parser.GetNetworkOutputBindingInfo(self.graph_id, n) for n in self.nodes_out]
    self.output_tensors = ann.make_output_tensors(self.output_binding_infos)
    self.infer_idx = runtime.get_infer_idx()
    self.runtime = runtime.runtime
    backend = kwargs.get('backend', 'CpuAcc')
    self.logger.info(f'Dense8 uses ARMNN backend: {backend}')
    self.backend = ann.BackendId(backend)
    opt_options = ann.OptimizerOptions(backend=="GpuAcc", False, False, False, netIdx)
    self.logger.info(f'Dense8 FP16 Turbo mode: {opt_options.m_ReduceFp32ToFp16}')
    opt_net, messages = ann.Optimize(self.net, [self.backend], self.runtime.GetDeviceSpec(), opt_options)
    self.net_id, _ = self.runtime.LoadNetwork(opt_net)
    self.input_shape = tuple(self.input_binding_info[1].GetShape())
    logger.info(f"Dense input shape: {self.input_shape}")
    self.input_h = self.input_shape[1]
    self.input_w = self.input_shape[2]

  def infer_sync(self, img, num_only=False):
    feed = self.preprocess(img, nchw=False)[0]
    self.logger.debug("Dense8 preprocess done")
    input_tensors = ann.make_input_tensors([self.input_binding_info], [feed])
    self.logger.debug("Dense8 input ready")
    self.runtime.EnqueueWorkload(self.net_id, input_tensors, self.output_tensors)
    self.logger.debug("Dense8 inference done")
    logits = ann.workload_tensors_to_ndarray(self.output_tensors)[0]
    self.logger.debug("Dense8 output ready")
    codes, probs, positions = self.parse_result(logits, num_only)
    self.logger.debug("Dense8 output parsed")
    return codes, probs, positions

