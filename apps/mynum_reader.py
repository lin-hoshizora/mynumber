import time
import logging
import pickle
import unicodedata
from pathlib import Path
import multiprocessing
import subprocess
import cv2
import numpy as np
import regex as re
from .base_reader import BaseReader
from .utils.general import get_date_roi, get_num_roi
from .utils.text import get_date, fix_num, clean_year
from .utils.image import max_iou, dilate_erode, sharpen, read_scope, box_crop
from info_extractor.date import Date

import time


INFO_ITEMS = {
    'マイナンバーカード': {
      'Birthday': '生年月日',
      'YukoEdYmd': '有効終了日',
      'Code': '4桁コード',
    }
}

def match(img, target, method=cv2.TM_CCOEFF_NORMED, blur=5):
  img_blur = cv2.GaussianBlur(img, (blur, blur), 0)
  res = cv2.matchTemplate(img_blur, target, method)
  _, max_v, _, max_loc = cv2.minMaxLoc(res)
  return max_v, max_loc


class MyNumReader(BaseReader):
  def __init__(self, client, logger, conf):
    super().__init__(client=client, logger=logger, conf=conf)
    self.mark = cv2.imread('mynum_mark_processed.jpg', cv2.IMREAD_GRAYSCALE)
    self.mark_flip = cv2.rotate(self.mark, cv2.ROTATE_180)
    self.tm_threshold = 0.7
    #self.tm_threshold = -1
    self.syukbn = 'Unknown'
    self.scanned = False
    self.prob = {}
    self.n_retry = 2
    self.load_scope()
    self.skip_rot = True

  def load_scope(self):
    self.scope = read_scope("scope.txt")

  @staticmethod
  def clean_half_width(texts):
    """
    Borrowed from mainstream insurance reader
    """
    for idx, line in enumerate(texts):
      for idx_w, w in enumerate(line[:-1]):
        text, probs, positions, box = w
        # clean nums
        x_dist = positions[1:] - positions[:-1]
        close_indices = np.where(x_dist < 32)
        if close_indices[0].size > 0 and all([not c.isdigit() for c in text]):
          for idx_m in close_indices[0]:
            if unicodedata.normalize('NFKC', text[idx_m]) == unicodedata.normalize('NFKC', text[idx_m + 1]):
              texts[idx][idx_w][0] = text[:idx_m] + text[idx_m] + text[idx_m+2:]
              texts[idx][idx_w][1][idx_m:idx_m+2] = [probs[idx_m]]
              texts[idx][idx_w][2][idx_m:idx_m+2] = [positions[idx_m]]
          texts[idx][-1] = ''.join([l[0] for l in texts[idx][:-1]])
      texts[idx][-1] = unicodedata.normalize('NFKC', fix_num(line[-1])).upper()
    return texts

  def rotate_and_validate(self, img):
    if img.shape[0] > img.shape[1]:
      img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
      self.logger.info('Portrait layout detected for my number card, rotating...')
    h, w = img.shape[:2]

    img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    ori_max, max_loc = match(img_gray[:h//2, w//2:], self.mark)
    flip_max, max_loc_flip = match(img_gray[h//2:, :w//2], self.mark_flip)
    self.logger.info(f'TM max value: {ori_max :.3f}')
    self.logger.info(f'TM max value after flipping: {flip_max :.3f}')
    self.logger.info(f'TM threshold: {self.tm_threshold}')
    if ori_max < self.tm_threshold and flip_max < self.tm_threshold:
      #return img, False
      self.logger.info('No matched mynum mark, assuming mark on outter side')
      self.max_loc = (1200, 50)
      return img, True

    if ori_max > flip_max:
      self.max_loc = (max_loc[0] + w // 2, max_loc[1])
      return img, True

    self.logger.info("Image seems upsidedown, flipping...")
    x = w - (max_loc_flip[0] + self.mark_flip.shape[1])
    y = h - (max_loc_flip[1] + h // 2 + self.mark_flip.shape[0])
    self.max_loc = (x, y)
    img_flip = cv2.rotate(img, cv2.ROTATE_180)
    return img_flip, True

  def get_chip(self, img, boxes, roi, lower_y=False, num_sp=False):
    max_v, max_idx = max_iou(boxes, roi)
    force_roi = False
    if max_v > 0:
      box = boxes[max_idx]
      if num_sp:
        box[3] += int((box[3] - box[1]) * 0.15)
        self.logger.info("Using temp fix for num chip")
    else:
      box = roi
      box[0] += 5
      box[2] -= 20
      box[1] += 20
      box[3] = box[3] - 15 if lower_y else box[3] - 20
      force_roi = True
    #TODO: use better handling
    if box[1] >= box[3]:
      box[1], box[3] = 0, 32
    if box[0] >= box[2]:
      box[2], box[2] = 0, 32
    box = box.astype(int)
    chip = img[box[1]:box[3], box[0]:box[2]]
    return chip, box, max_idx, force_roi

  def save_chip(self, chip, name):
    if not name.endswith(".jpg"):
      name += ".jpg"
    save_path = str(self.debug_out / name)
    cv2.imwrite(save_path, chip[..., ::-1])

  def draw_roi(self, img, roi, name):
    img_draw = img.copy()
    cv2.rectangle(img_draw, (roi[0], roi[1]), (roi[2], roi[3]), (255, 0, 0), 2)
    if not name.endswith(".jpg"): name += ".jpg"
    save_path = str(self.debug_out / name)
    cv2.imwrite(save_path, img_draw[..., ::-1])

  def get_date_chip(self, img, boxes):
    date_roi = get_date_roi(self.max_loc[0], self.max_loc[1], img.shape[1], img.shape[0])
    chip, box, box_idx, force_roi = self.get_chip(img, boxes, date_roi, lower_y=True)
    if 32 / chip.shape[0] * chip.shape[1] < 400:
      for b_idx, b in enumerate(boxes):
        if b_idx == box_idx:
          continue
        inter_y1 = max(b[1], box[1])
        inter_y2 = min(b[3], box[3])
        union_y1 = min(b[1], box[1])
        union_y2 = max(b[3], box[3])
        #if max(inter_y2 - inter_y1, 0) / (union_y2 - union_y1) > 0.6:
        if max(inter_y2 - inter_y1, 0) / (union_y2 - union_y1) > 0.3:
            x1 = int(min(b[0], box[0]))
            x2 = int(max(b[2], box[2]))
            y1 = int(min(b[1], box[1]))
            y2 = int(max(b[3], box[3]))
            box = np.array([x1, y1, x2, y2])
            chip = img[y1:y2, x1:x2]
    if self.debug["draw_date_roi"]:
      self.draw_roi(img, date_roi, "date_roi")
    if self.debug["save_chips"]:
      self.save_chip(chip, "date")
    self.date_chip = chip
    chip = dilate_erode(chip)
    return chip, box

  def get_num_chip(self, img, boxes):
    num_roi = get_num_roi(self.max_loc[0], self.max_loc[1], img.shape[1], img.shape[0])
    if self.debug["draw_num_roi"]:
      self.draw_roi(img, num_roi, "num_roi")
    chip, box, box_idx, force_roi = self.get_chip(img, boxes, num_roi, num_sp=True)
    if self.debug["save_chips"]:
      self.save_chip(chip, "num")
    self.num_chip = chip
    return chip, box

  def get_bdate_yukoymd(self):
    for l in self.texts:
      if 'Birthday' in self.info: break
      dates = get_date(l[-1], return_jp_year=True)
      if len(dates) != 2 and l[0][1].size > 0:
        if l[0][1].min() < 0.95:
          rm_idx = l[0][1].argmin()
          dates = get_date(l[-1][:rm_idx] + l[-1][rm_idx+1:], return_jp_year=True)
      if len(dates) == 2:
        if isinstance(dates[0], tuple):
          self.info['Birthday'] = dates[0][-1]
        else:
          self.info['Birthday'] = dates[0]
        if isinstance(dates[1], tuple):
          self.info['YukoEdYmd'] = dates[1][0]
        else:
          self.info['YukoEdYmd'] = dates[1]
        prob = min(l[0][1])
        self.prob['Birthday'] = prob
        self.prob['YukoEdYmd'] = prob
    if len(self.info.get('Birthday', '')) == 8:
      self.info['Birthday'] = self.info['Birthday'][2:]

  def get_code(self):
    with open('texts-code.txt','w') as f:
      f.write(str(self.texts))
    for l in self.texts:
      if 'Code' in self.info: break
      if l[-1].isdigit() and len(l[-1]) == 4:
        self.info['Code'] = l[-1]
        self.prob['Code'] = min(l[0][1])
    if 'Code' not in self.info:
      self.logger.warning('No 4-digit PIN found, grabbing last digits from each line')
      self.logger.warning('3-digit kara 4-difit ni tasu!')
      for l in self.texts:
        codes = re.findall(r'\d{3,4}$', l[-1])
        if codes:
          if len(codes[-1])==4:
            pass
          else:
            self.logger.warning('code3 debug: '+ str(codes[-1]))
            code3 = codes[-1]
            if code3[0] == code3[1]:
	              code3 = code3[1] + code3
            elif code3[2] == code3[1]:
              code3 = code3 + code3[1]
            codes[-1] = code3          
          ##
          self.info['Code'] = codes[-1]
          self.prob['Code'] = min(l[0][1])
          break

  def crop(self, img, margin):
    img = img.copy()
    x1, y1, x2, y2 = self.scope if margin is None else margin
    img = img[y1:y2, x1:x2]
    return img

  def draw_max_loc(self, img):
    img = img.copy()
    cv2.rectangle(img,
                  (self.max_loc[0], self.max_loc[1]),
                  (self.max_loc[0] + 100, self.max_loc[1] + 100), (255, 0, 0), 2)
    save_path = str(self.debug_out / "max_loc.jpg")
    cv2.imwrite(save_path, img)

  def get_chip_box(self, img, margin=None):
    img = self.crop(img, margin)
    img, valid = self.rotate_and_validate(img)
    boxes, scores = self.find_texts(img)
    chip_img = self.det_img if self.recog_preproc == self.det_preproc else self.img
    _, date_box = self.get_date_chip(chip_img, boxes)
    _, num_box = self.get_num_chip(chip_img, boxes)
    return date_box, num_box

  def ocr(self, img, category, margin=None):
    self.info = {}
    img = self.crop(img, margin)
    img, valid = self.rotate_and_validate(img)
    if self.debug["draw_max_loc"]: self.draw_max_loc(img)
    if valid:
      counter = 0;
      while counter < self.n_retry:
        counter += 1
        self.syukbn = "マイナンバーカード"
        try:
          t0 = time.time()
          boxes, scores = self.find_texts(img)
          print(f"find texts: {time.time() - t0:.3f}")
        except Exception as e:
          boxes = np.array([])
          scores = np.array([])
        self.logger.info(f'{len(boxes)} text boxes detected')
        if len(boxes) == 0: continue

        texts = []
        chip_img = self.det_img if self.recog_preproc == self.det_preproc else self.img
        # date
        chip, box = self.get_date_chip(chip_img, boxes)
        self.date_chip = chip
        date_line = self.read_single_line(chip, box, num_only=False)

        ##debug date line
        with open('date-line-mae.txt','w') as f:
          f.write(str(date_line[-1])+'\n')
          f.write(str(boxes)+'\n')
          f.write(str(box)+'\n')
        if re.findall('(昭.|平成|令和|合和|大正|明治).*',date_line[-1]):
          pass
        else:
          box[0] = box[0]-120
          chip, box = self.get_date_chip(chip_img, [box])
          date_line = self.read_single_line(chip, box, num_only=False)

        with open('date-line-shusei.txt','w') as f:
          f.write(str(date_line[-1])+'\n')
          f.write(str(boxes)+'\n')
          f.write(str(box)+'\n')
        ##debug

        if len(date_line[-1]) > 0:
          texts.append(date_line)
          self.logger.debug(f'Recogized date text: {date_line[-1]}')
          self.logger.debug(f'Probs: {str(date_line[0][1])}')
        else:
          self.logger.warning('No text recognized for date')
          continue

        # num
        chip, box = self.get_num_chip(chip_img, boxes)

        num_line = self.read_single_line(chip, box, num_only=True)
        if len(num_line[-1]) < 4:
          self.logger.warning('Fewer than 4 chars recognied in num roi, sharpen and try again')
          chip = sharpen(chip)
          num_line = self.read_single_line(chip, box, num_only=True)
        if num_line[0][1].size > 0:
          if num_line[0][1].min() < 0.95:
            self.logger.warning('Low confidence for num, sharpen and try again')
            chip_sharp = sharpen(chip)
            num_line_new = self.read_single_line(chip_sharp, box, num_only=True)
            if num_line_new[0][1].size > 0:
              if num_line_new[0][1].min() > num_line[0][1].min():
                self.logger.warning('sharpen result used')
                num_line = num_line_new
            else:
              self.logger.warning('sharpen result has lower confidence, discarded')

        if len(num_line[-1]) > 0:
          texts.append(num_line)
          self.logger.debug(f'Recognized num text: {num_line[-1]}')
          self.logger.debug(f'Probs: {str(num_line[0][1])}')
        else:
          self.logger.warning('No text recognized for num')
          continue

        texts = [clean_year(line) for line in self.clean_half_width(texts)]
        self.texts = texts
        self.get_bdate_yukoymd()
        self.get_code()

        done = True
        for k in ["Birthday", "YukoEdYmd", "Code"]:
          if k not in self.info:
            self.logger.warning(f"Cannot find {k}")
            done = False
            break
        if done: break
    else:
      self.syukbn = 'Unknown'

    now = time.localtime()
    name = ''
    for i in now[0:6]:
      name = name + str(i) + '-'
    try:
        with open('./debug/texts-all'+name+'.txt','w') as f:
            f.write(str(texts))
    except:
        with open('./debug/texts-all'+name+'.txt','w') as f:
            f.write('1\n')


    return self.syukbn

  def extract_info(self, key: str):
    """
    Borrowed from mainstream insurance reader
    """
    if key == 'SyuKbn':
      return self.syukbn
    else:
      text = self.info.get(key, None)
      if isinstance(text, Date):
        text = str(text)
      result = {"text": text, "confidence": 1.0}
      return result
