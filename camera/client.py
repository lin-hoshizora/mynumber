import time
import numpy as np
import zmq
from utils import ensure_type


class CamClient:
  def __init__(self, conf):
    port = conf["zmq"]["port"]
    ensure_type(port, int)
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.SUBSCRIBE, b"")
    socket.setsockopt(zmq.CONFLATE, 1)
    socket.connect(f"tcp://localhost:{port}")
    self.socket = socket

  def read(self):
    raw = self.socket.recv()
    img = np.frombuffer(raw, dtype=np.uint8).reshape(1944, 2592, 3)
    return img
