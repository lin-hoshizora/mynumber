"""App that extracts information from insurance card image
"""
from pathlib import Path
import pickle
import logging
from typing import Any
import cv2
import numpy as np
from ..utils.image import get_rect, get_chips, rotate_if_necessary, merge, rotate
from ..utils.general import group_lines
from ..utils.text import fuzzy_match, clean_half_width


INSURANCE_WORDS = [
    '保険',
    '共済',
    '受給',
    '公費',
    '高齢',
    '限度額',
    '資格取得',
    '番号',
    '記号',
]

KOUHI_WORDS = [
    '公費',
    'ひとり親',
    '子育て支援',
    '指定難病',
    '心身障害者医療',
]

GENDO_WORDS = [
    '限度額認証',
    '限度額適用'
]

KOUREI_WORDS = [
    '高齢',
    '髙齢',
    '高齡',
    '髙齡',
]

class InsuranceReader:
  """OCR-based reader for insurance card.

  This is the class one uses to extract information in key-value pairs from
  insurance card images. It integrates modules that acutcally do OCR and
  key information extraction, thus requires corresponding instances during
  instantiation. All information has already been extracted when ocr_sync
  if done, and extract_info simply serves as an API that can be used by
  other packages.

    Typical usage example:
      >>> reader = InsuranceReader(
      >>>     model_server = a_client_of_model_server,
      >>>     analyzers = {"a": analyzer_for_a, "b": analyzer_for_b},
      >>>     logger = python_logger
      >>> )
      >>> syukbn = reader.ocr_sync(sess_id="123", img=img)
      >>> print(syukbn)
      主保険
      >>> hknja_num = reader.extract_info("HknjaNum")
      >>> print(hknja_num)
      12345678
      >>> bdate = reader.extract_info("Birthday")
      >>> print(bdate)
      20210401

  Args:
    model_server: An instance of `model_serving.client.Client`
    analyzers: A dict of analyzers to extract infomation
        from OCR results. Keys are possible values of syukbn that can be
        returned by ocr_sync. Information extraction will be skipped if
        there is no corresponding analyzer for a syukbn.
    logger: A logging.Logger
  """
  def __init__(self,
               model_server: Any,
               analyzers: dict,
               logger: logging.Logger):
    self.model_server = model_server
    self.logger = logger
    self.root_folder = Path(__file__).resolve().parent.parent
    with open(str(self.root_folder / 'id2char_std.pkl'), 'rb') as f:
      self.id2char = pickle.load(f)
    # standard charset
    assert len(self.id2char) == 7549
    self.is_portrait = False
    self.img = None
    self.info = {}
    self.syukbn = 'Uknown'
    self.session_id = 'init_id'
    self.min_wh_ratio = 0.5
    self.analyzers = analyzers
    self.pth = 0.5

  def prefetch_hknjanum(self):
    """Extracts 保険者番号"""
    hknjanum = self.analyzers["主保険"].finders["HknjaNum"].extract(self.texts)
    if hknjanum is None: hknjanum = ""
    return hknjanum

  def read_page_sync(self, img: np.ndarray, layout: str = None) -> list:
    """Reads text from an image and group results in textlines.

    Args:
      img: Image to run OCR on
      layout: Layout (portrait/landscape) based on which a text detection
          model is chosen

    Returns:
      OCR results in a list. Each element contains bounding box and recognized
      text for a line.
    """
    recog_results = []

    # check layout
    if img.shape[0] > img.shape[1]:
      self.is_portrait = True
      layout = 'portrait'
    else:
      self.is_portrait = False
      layout = 'landscape'

    # detect text
    det_res = self.model_server.infer_sync(
        sess_id=self.sess_id, network='Det',
        img=img,
        layout=layout,
        suppress_lines=False,
        check_local=False
    )
    if 'lines' in det_res:
      lines = det_res['lines']
    else:
      return det_res

    # abort if less than 2 text boxes are detected
    if lines.shape[0] < 2:
      self.logger.info(f'{lines.shape[0]} text boxes detected')
      return np.array([]), recog_results

    # filter out invalid boxes
    lines[lines < 0] = 0
    self.logger.debug(f'Detected text boxes b4 wh ratio filter: {len(lines)}')
    text_boxes = get_rect(lines, min_wh_ratio=self.min_wh_ratio)
    text_boxes = merge(text_boxes)
    self.logger.debug(f'Detected text boxes after wh ratio filter: '
                      f'{len(text_boxes)}, min wh ratio: {self.min_wh_ratio}')

    # abort if less than 2 text boxes are detected
    text_boxes = np.array(text_boxes)
    if text_boxes.shape[0] < 2:
      self.logger.info(f'{lines.shape[0]} text boxes detected')
      return np.array([]), recog_results

    # rotate when the detected angle is larger than 0.1 degree
    if 'angle' in det_res and np.abs(det_res['angle']) > 0.1:
      img = rotate(img, det_res["angle"])

    self.img = img

    # text recognition
    chips = get_chips(img, text_boxes)
    recog_res_dict = self.model_server.infer_batch_sync(
        sess_id=self.sess_id,
        network='Dense',
        imgs=chips,
        num_onlys=[False]*len(chips),
        check_local=False
    )
    if 'codes' not in recog_res_dict: return recog_res_dict
    for idx, (box, codes) in enumerate(zip(
        text_boxes,
        recog_res_dict["codes"]
    )):
      probs, positions = (
          recog_res_dict["probs"][idx],
          recog_res_dict["positions"][idx],
      )
      if codes.size == 0:
        continue
      indices = probs > self.pth
      probs = probs[indices]
      positions = positions[indices]
      codes = codes[indices]
      text = "".join([self.id2char[c] for c in codes])
      if text:
        recog_results.append([text, probs, positions, box])

    # group text areas in lines
    texts = group_lines(recog_results)
    return texts

  def is_kouhi(self, all_txt: str) -> bool:
    """Determines if an insurance is 公費.

    Args:
      all_txt: A single string containing all text recognized from an image.

    Returns:
      A boolean indicating if the image is a 公費
    """
    # check keywords

    if not self.is_portrait and ('兼高齢' in all_txt or '蒹高齢' in all_txt): return False
    for w in KOUHI_WORDS:
      if len(w) < 4 and w in all_txt: return True
      if 4 <= len(w) <= 6 and fuzzy_match(w, all_txt): return True
      if len(w) > 6 and fuzzy_match(w, all_txt, e_max=3): return True

    # check insurer number
    hknjanum = self.prefetch_hknjanum()
    if hknjanum.startswith('81') or hknjanum.startswith('82'): return True
    return False

  def is_gendo(self, all_txt: str) -> bool:
    """Determines if an insurance is gendo.

    Args:
      all_txt: A single string containing all text recognized from an image.

    Returns:
      A boolean indicating if the image is a 限度額認定証
    """
    for w in GENDO_WORDS:
      if fuzzy_match(w, all_txt): return True
    return False

  def is_kourei(self, all_txt: str) -> bool:
    """Determines if an insurance is 高齢受給者証.

    Args:
      all_txt: A single string containing all text recognized from an image.

    Returns:
      A boolean indicating if the image is a 高齢受給者証
    """
    if fuzzy_match('後期高齢者医療被保険者証', all_txt): return False
    if not self.is_portrait and ('兼高齢' in all_txt or '蒹高齢' in all_txt): return False
    if any([w in all_txt for w in KOUREI_WORDS]):
      if (not self.is_portrait) and self.prefetch_hknjanum().startswith('39'):
        return False
      return True
    return False

  def validate(self, texts: list) -> bool:
    """Checks if text is from an insurance.

    Args:
      texts: Return value of read_page_sync, OCR results in a list.

    Returns:
      A boolean indicating if the image is an insruance.
    """
    if not texts:
      self.logger.warning('No text detected, categorized as Unknown')
      return False
    all_txt = ''.join([w[0] for line in texts for w in line if len(w) > 1])
    if not sum([w in all_txt for w in INSURANCE_WORDS]) > 1:
      self.logger.warning('No isnurance key word found, categorized as Unknown')
      return False
    return True

  def categorize(self, texts: list) -> str:
    """Determines 主区分 of an image based on OCR results.

    Args:
      texts: Return value of read_page_sync, OCR results in a list.

    Returns:
      A string indicating 主区分
    """
    all_txt = ''.join([line[-1] for line in texts])
    if '介護' in all_txt:
      self.logger.warning('kaigo detected, categorized as Unknown')
      return 'Unknown'
    if self.is_kouhi(all_txt):
      return '公費'
    if self.is_gendo(all_txt):
      return '限度額認証'
    if self.is_kourei(all_txt):
      return '高齢受給者'
    return '主保険'

  def ocr_sync(self, sess_id: str, img: np.ndarray) -> str:
    """Runs OCR on insurance card.

    Args:
      sess_id: Session ID used in communication with the model server
      img: Image to extract information from

    Returns:
      A string indicating Syukbn of the input image.
    """
    self.info = {}
    for tag in self.analyzers:
      self.analyzers[tag].info.clear()
    self.sess_id = sess_id
    img = rotate_if_necessary(img, 1600, self.logger)

    # correct the orientation
    rotations = [
        None,
        cv2.ROTATE_180,
        cv2.ROTATE_90_CLOCKWISE,
        cv2.ROTATE_180,
    ]
    for rot in rotations:
      if rot is not None: img = cv2.rotate(img, rot)
      results = self.read_page_sync(img)
      # handle error
      if isinstance(results, dict): return results
      # check if a valid insurance based OCR results
      valid = self.validate(results)
      if valid: break

    # abort if not a valid insurance
    if not valid:
      self.syukbn = 'Unknown'
      self.img = img
      return self.syukbn

    # clean nums and convert to half width
    texts = clean_half_width(results)
    self.texts = texts

    for line in texts:
      print(" ".join(w[0] for w in line[:-1]))
      print(line[-1])

    # categorize insurance
    syukbn = self.categorize(texts)
    self.syukbn = syukbn

    # extract info
    if syukbn not in self.analyzers: return syukbn
    self.analyzers[syukbn].fit(texts)
    self.info = self.analyzers[syukbn].info
    return syukbn

  def extract_info(self, key: str) -> str:
    """Gets information for a specific item.

    Args:
      key: Name of the item to extract.

    Returns:
      A string for the item if it is sucessfully extracted, `None` otherwise.
      For example:
        >>> reader.extract_info("HknjaNum")
        12345678
        >>> reader.extract_info("Birthday")
        20210401
    """
    res = self.info.get(key, None)
    if res is not None and not isinstance(res, str): res = str(res)
    return res
