import asyncio
import queue
import threading
import json
from pathlib import Path
import time
import cv2
import yaml
import websockets
from apps import MyNumReader, Calibrator
from apps.insurance_reader import SimpleReader

from apps.utils.image import read_scope

from info_extractor import Analyzer
from ocr2.info_extractor.main_analyzer import MainAnalyzer


from utils import get_logger, get_timestamp, handle_err_ws, load_conf, validate_json
from camera import CamClient
from model_serving import ModelClientMock

x1, y1, x2, y2 = read_scope("scope.txt")

async def serve_ocr(websocket, path):
  async for data in websocket:
    sess_id = get_timestamp()
    img_path = data_folder / (sess_id + '.jpg')
    err_save_path = log_folder / (sess_id + '_err.json')
    logger.info(f'Websocket Received: {str(data)}')

    if not isinstance(data, str):
      await handle_err_ws(err['non-text'], err_save_path, logger, websocket)
      continue

    try:
      json_req = json.loads(data)
    except json.JSONDecodeError:
      await handle_err_ws(err['non-json'], err_save_path, logger, websocket)
      continue

    if not validate_json(json_req):
      await handle_err_ws(err['invalid-json'], err_save_path, logger, websocket)
      continue

    if "Scan" in json_req:
      # TODO: dynamic adjustment of init brightness
      if json_req["Scan"] == "Brightness":
        res_json = {"Brightness": "380"}
        res_str = json.dumps(res_json)
        with open(str(log_folder / (sess_id + '_brightness.json')), 'w', encoding='utf-8') as f:
          json.dump(res_json, f)
        logger.info(res_str)
        await websocket.send(res_str)
        continue

      t0 = time.time()
      try:
        # img = cap.read()
        img = cv2.imread('2021_04_20_14_53_43.jpg')
        cv2.imwrite('test.jpg',img)##########################################
        logger.info(f'Capture time: {time.time() - t0 :.2f}s')
      except Exception as e:
        logger.error(f'Capture Error: {str(e)}')
        await handle_err_ws(err['scan_err'], err_save_path, logger, websocket)
        continue

      if config["websocket"]["save_img"].get(json_req["Scan"].lower(), False):
        ret = cv2.imwrite(str(img_path), img)
        if not ret:
          await handle_err_ws(err['save_err'], err_save_path, logger, websocket)
          continue
      logger.info('Scan done')
      reader.scanned = True

      try:
        if json_req["Scan"] == "MyNumTest":
          if calibrator.test_ocr(img):
            res = "OK"
            reader.load_scope()
          else:
            res = "NG"
          res_json = {"Result": res}
          res_str = json.dumps(res_json)
          with open(str(log_folder / (sess_id + '_test.json')), 'w', encoding='utf-8') as f:
            json.dump(res_json, f)
          logger.info(res_str)
          await websocket.send(res_str)
          continue

        elif json_req["Scan"] == "MyNumber":
          syukbn = reader.ocr(img, category=json_req["Scan"])
        elif json_req["Scan"] == "shuhoken":
          syukbn = simple_reader.ocr(img)
          reader.info = simple_reader.main_info
          reader.syukbn = "主保険"
        else:
          syukbn = simple_reader.ocr(img)
          reader.info = simple_reader.info
          reader.syukbn = "公費"
        logger.info(f'OCR time: {time.time() - t0 :.2f}s')
      except Exception as e:
        logger.error(str(e))
        await handle_err_ws(err['ocr_err'], err_save_path, logger, websocket)
        continue

      res_json = {"Category": "NA", "Syukbn": syukbn, "ImagePath": str(img_path)}
      res_str = json.dumps(res_json)
      #with open(str(log_folder / (sess_id + '_scan.json')), 'w', encoding='utf-8') as f:
      #  json.dump(res_json, f)
      logger.info(f'OCR total: {time.time() - t0 :.2f}s')
      logger.info(res_str)
      await websocket.send(res_str)

    if 'Patient' in json_req or 'MyNumber' in json_req:
      if not reader.scanned:
        await handle_err_ws(err['no_scan'], err_save_path, logger, websocket)
        continue
      reader.scanned = False
      print(simple_reader.info)
      print(reader.info)
      res_json = {}
      for meta_k, meta_v in json_req.items():
        res_json[meta_k] = {}
        if isinstance(meta_v, dict):
          for field in meta_v:
            res_json[meta_k][field] = reader.extract_info(field)
            print(field, res_json[meta_k][field])
      res_str = json.dumps(res_json)
      #with open(str(log_folder / (sess_id + '_info.json')), 'w', encoding='utf-8') as f:
      #  json.dump(res_json, f)
      logger.info(res_str)
      await websocket.send(res_str)


# config
err = load_conf("config/err.yaml")
config = load_conf("config/api.yaml")
cam_conf = load_conf("config/camera.yaml")
mynum_conf = load_conf("config/mynum_reader.yaml")
insurance_conf = load_conf("config/insurance_reader.yaml")
calib_conf = load_conf("config/calibrator.yaml")

#miscs
logger = get_logger(config['logger'])
data_folder = Path(config['websocket']['data_path'])
log_folder = data_folder / 'backend_res'
if not log_folder.exists():
  log_folder.mkdir(parents=True, exist_ok=True)

# ocr
cap = CamClient(cam_conf)
client = ModelClientMock(logger=logger)
reader = MyNumReader(logger=logger, client=client, conf=mynum_conf)
simple_reader = SimpleReader(logger=logger, client=client, analyzer=Analyzer(),main_analyzer=MainAnalyzer(), conf=insurance_conf)
calibrator = Calibrator(logger=logger, client=client, conf=calib_conf)

# start server
ocr_ip = config["websocket"]["ocr"]["ip"]
ocr_port = config["websocket"]["ocr"]["port"]
logger.info(f"Starting OCR server at ws://{ocr_ip}:{ocr_port}")
ocr_server = websockets.serve(serve_ocr, ocr_ip, ocr_port)
asyncio.get_event_loop().run_until_complete(ocr_server)
asyncio.get_event_loop().run_forever()
