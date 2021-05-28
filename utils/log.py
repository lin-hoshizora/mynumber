from pathlib import Path
import sys
import logging
import json
from datetime import datetime
from . import valid_path


def get_logger(config):
  formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  logger = logging.getLogger()
  logger.handlers = []
  logger.setLevel(getattr(logging, config.get('level', 'DEBUG')))

  # stream
  stream_handler = logging.StreamHandler(stream=sys.stdout)
  stream_handler.setFormatter(formatter)
  logger.addHandler(stream_handler)

  # file
  log_path = config.get('path', None)
  if log_path is not None:
    log_folder = Path(log_path)
    if not log_folder.exists():
      log_folder.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(f"{log_folder}/{get_timestamp()}_scanner.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
  return logger


def get_timestamp():
  timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
  return timestamp


def handle_err(err, save_path, logger):
  save_path = valid_path(save_path)
  with open(str(save_path), 'w', encoding='utf-8') as f:
    json.dump(err, f)
  logger.error(f'[{err["ErrCode"]}] {err["ErrMsg"]}')
  err_str = json.dumps(err)
  return err_str


async def handle_err_ws(err, save_path, logger, websocket):
  err_str = handle_err(err, save_path, logger)
  await websocket.send(err_str)

