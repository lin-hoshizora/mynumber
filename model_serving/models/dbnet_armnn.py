import time
from pathlib import Path
import pyarmnn as ann
from .dbnet_base import DBNet

class DBNetArmNN(DBNet):
  def __init__(self, model_path, preprocess, runtime, backend, logger, **kwargs):
    super().__init__(logger, **kwargs)
    self.graph_id = 0
    parser = ann.ITfLiteParser()
    netIdx = 0
    if Path(model_path).exists():
      net = parser.CreateNetworkFromBinaryFile(model_path)
    elif model_path == "landscape":
      net = parser.CreateDetLandscape()
      netIdx = 4
    elif model_path == "portrait":
      net = parser.CreateDetPortrait()
      netIdx = 5
    else:
      raise ValueError(f"Invalid model path: {model_path}")
    self.preproc_mode = preprocess
    self.runtime = runtime.runtime
    self.infer_idx = runtime.get_infer_idx()
    opt_options = ann.OptimizerOptions(backend=="GpuAcc", False, False, False, netIdx)
    from inspect import getmembers
    logger.info(f"Det Backend: {backend}, FP16 Turbo Mode: {opt_options.m_ReduceFp32ToFp16}")
    preferredBackends = [ann.BackendId(backend)]
    opt_net, msg = ann.Optimize(net, preferredBackends, self.runtime.GetDeviceSpec(), opt_options)
    self.net_id, _ = self.runtime.LoadNetwork(opt_net)

    nodes_in = parser.GetSubgraphInputTensorNames(self.graph_id)
    assert len(nodes_in) == 1, f'{len(nodes_in)} inputs found, 1 expected'
    self.input_info = parser.GetNetworkInputBindingInfo(self.graph_id, nodes_in[0])
    self.input_shape = tuple(self.input_info[1].GetShape())
    self.input_h = self.input_shape[1]
    self.input_w = self.input_shape[2]
    logger.info(f"DetNet input shape: {self.input_shape}")

    nodes_out = parser.GetSubgraphOutputTensorNames(self.graph_id)
    assert len(nodes_out) == 1, f'{len(nodes_out)} outputs found, 1 expected'
    self.output_info = parser.GetNetworkOutputBindingInfo(self.graph_id, nodes_out[0])
    self.output_tensors = ann.make_output_tensors([self.output_info])
    self.logger = logger

  def infer_sync(self, img):
    feed = self.preprocess(img)
    t0 = time.time()
    input_tensors = ann.make_input_tensors([self.input_info], [feed])
    self.runtime.EnqueueWorkload(self.net_id, input_tensors, self.output_tensors)
    result = ann.workload_tensors_to_ndarray(self.output_tensors)[0]
    self.logger.debug(f'DBnet enqueue: {time.time() - t0:.3f}s')
    boxes, scores, angle = self.parse_result(result)
    return boxes, scores, angle
