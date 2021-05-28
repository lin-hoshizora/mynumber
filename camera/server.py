import queue
import threading
import time
import zmq
import cv2
import numpy as np
from utils import ensure_type

class CamServer:
  def __init__(self, conf):
    self.conf = conf
    self.validate_conf()
    self.cap = cv2.VideoCapture(conf["camera"]["path"])
    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, conf["camera"]["width"])
    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, conf["camera"]["height"])
    self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, conf["camera"]["ae"])
    self.cap.set(cv2.CAP_PROP_EXPOSURE, conf["camera"]["exposure"])

    self.q = queue.Queue()
    t = threading.Thread(target=self._reader)
    t.daemon = True
    t.start()

    context = zmq.Context()
    self.socket = context.socket(zmq.PUB)
    self.socket.bind(f"tcp://127.0.0.1:{conf['zmq']['port']}")


  def validate_conf(self):
    cam = self.conf["camera"]
    ensure_type(cam.get("path", None), str, "Invalid cam path")
    ensure_type(cam.get("width", None), int, "Invalid cam width")
    ensure_type(cam.get("height", None), int, "Invalid cam width")
    if cam.get("ae", None) not in [1, 0]:
      raise ValueError("Invalid cam AE")
    ensure_type(cam.get("exposure", None), int, "Invalid cam width")

    zmq = self.conf["zmq"]
    ensure_type(zmq.get("port", None), int, "Invalid ZMQ port")
    ensure_type(zmq.get("sleep", None), dict, "Invalid sleep conf")
    ensure_type(zmq["sleep"].get("check", None), float, "Invalid check interval")
    ensure_type(zmq["sleep"].get("flush", None), float, "Invalid flush interval")


  def _reader(self):
    while True:
      t0 = time.time()
      ret, img = self.cap.read()
      t_cap = time.time()
      if not ret:
        break
      if not self.q.empty():
        try:
          self.q.get_nowait()
        except queue.Empty:
          pass
      self.q.put((t0, t_cap, img))


  def start_pub(self):
    while True:
      t0, t_cap, img = self.q.get()
      data = img.tobytes()
      self.socket.send(data)
      time.sleep(self.conf["zmq"]["sleep"]["flush"])
