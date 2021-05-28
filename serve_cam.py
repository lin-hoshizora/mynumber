import yaml
from camera import CamServer

with open("config/camera.yaml", encoding="utf-8") as f:
  conf = yaml.safe_load(f)

server = CamServer(conf)
server.start_pub()
