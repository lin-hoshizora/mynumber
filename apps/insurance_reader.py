from re import M
from time import process_time
import unicodedata
import pickle
import cv2
import regex as re
import numpy as np
from .base_reader import BaseReader
from info_extractor import Analyzer
from info_extractor.date import Date


def match(img, target, method=cv2.TM_CCOEFF_NORMED, blur=5):
  img_blur = cv2.GaussianBlur(img, (blur, blur), 0)
  res = cv2.matchTemplate(img_blur, target, method)
  _, max_v, _, max_loc = cv2.minMaxLoc(res)
  return max_v, max_loc
def rotate_and_validate(img,mark):
    tm_threshold = 0.6
    h, w = img.shape[:2]
    img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    ori_max, max_loc = match(img_gray[:h//2, w//2:], mark)
    if ori_max < tm_threshold:
        return img, False




class SimpleReader(BaseReader):
  def __init__(self, client, analyzer, main_analyzer,logger, conf):
    super().__init__(client=client, logger=logger, conf=conf)
    self.analyzer = analyzer
    self.main_analyzer = main_analyzer

  def need_rotate(self, boxes):
    xs = boxes[:, 0::2]
    ys = boxes[:, 1::2]
    w = xs.max() - xs.min()
    h = ys.max() - ys.min()
    self.logger.info(f"w: {w}, h: {h}")
    return w < h and w < 900 and h < 1600

  def need_retry(self, texts):
    self.analyzer.fit(texts)
    retry = True
    for k, v in self.analyzer.info.items():
      if k == "JgnGak": continue 
      if v:
        retry = False
        break
    return retry


  def ocr(self, img):
    img_res = None
    img_ori = img.copy()
    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    self.info = {}
    self.main_info = {}
    boxes, scores = self.find_texts(img)
    rotate = self.need_rotate(boxes)

    print(rotate)
    if rotate:
      # handle orientation for card type
      boxes, scores = self.find_texts(img_ori)
    try:
      recog_results = self.read_texts(boxes=boxes)
      texts = self.group_textlines(recog_results)
    except:
      cv2.imwrite('debug_img.jpg',self.img)
      with open('./boxes.pkl','wb') as f:
        pickle.dump(boxes,f)
      raise Exception('Boxes or texts are somthing wrong, please check debug_boxes.pkl and debug_img.jpg')
    # simple check to see if upside down
    if self.need_retry(texts):
      # flip upsidedown and retry
      if self.img is not None: self.img = cv2.rotate(self.img, cv2.ROTATE_180)
      if self.det_img is not None: self.det_img = cv2.rotate(self.det_img, cv2.ROTATE_180)
      boxes[:, 0::2] = self.img.shape[1] - 1 - boxes[:, 0::2]
      boxes[:, 1::2] = self.img.shape[0] - 1 - boxes[:, 1::2]
      boxes = boxes[:, [2, 3, 0, 1]]
      # print(boxes)
      recog_results = self.read_texts(boxes=boxes)
      texts = self.group_textlines(recog_results)

    if self.need_retry(texts):
      # retry in another direction
      new_img = cv2.rotate(self.img, cv2.ROTATE_90_CLOCKWISE)
      boxes, scores = self.find_texts(new_img)
      recog_results = self.read_texts(boxes=boxes)
      texts = self.group_textlines(recog_results)

    if self.need_retry(texts):
      # flip upsidedown and retry
      if self.img is not None: self.img = cv2.rotate(self.img, cv2.ROTATE_180)
      if self.det_img is not None: self.det_img = cv2.rotate(self.det_img, cv2.ROTATE_180)
      boxes[:, 0::2] = self.img.shape[1] - 1 - boxes[:, 0::2]
      boxes[:, 1::2] = self.img.shape[0] - 1 - boxes[:, 1::2]
      boxes = boxes[:, [2, 3, 0, 1]]
      recog_results = self.read_texts(boxes=boxes)
      texts = self.group_textlines(recog_results)
      self.analyzer.fit(texts)

    for l in texts:
      # print(l)
      print(l[-1])

    print('base',self.analyzer.info)
   
    self.main_analyzer.info.clear()
    self.main_analyzer.fit(texts)
    print('main',self.main_analyzer.info)



    self.main_info = self.main_analyzer.info
    self.info = self.analyzer.info
    
    self.check_multi_HKJnum(texts)


    #find usagi test
    # self.mark = cv2.imread('mynum_mark_processed.jpg', cv2.IMREAD_GRAYSCALE)
    # self.mark_flip = cv2.rotate(self.mark, cv2.ROTATE_180)
    # img_gray = cv2.cvtColor(self.img, cv2.COLOR_RGB2GRAY)
    # h, w = self.img.shape[:2]
    # ori_max, max_loc = match(img_gray[:h//2, w//2:], self.mark)
    # flip_max, max_loc_flip = match(img_gray[h//2:, :w//2], self.mark_flip)
    # print('125  ',ori_max,max_loc,flip_max,max_loc_flip)

    return "公費"

  def extract_info(self, key: str):
    """
    Borrowed from mainstream insurance reader
    """
    print('extract_info')
    if key == 'SyuKbn':
      return "公費"
    else:
      text = self.info.get(key, None)
      if isinstance(text, Date):
        print('date2str')
        text = str(text)
      text = str(text)
      result = {"text": text, "confidence": 1.0}
      return result

  def check_multi_HKJnum(self,texts):
    for idx, line in enumerate(texts):
      res = re.findall('(番号)',line[-1])
      if res:
  #         print("番号発見！")
  #         print(f"prev line:{reader.texts[idx-1][-1]}")
        line1_2 = texts[idx-1][-1]+line[-1]
        hkj = re.sub('\d','',line1_2)
        print(hkj)
        nums=[]
        if hkj =="公費負担者番号":    
          for txt in line[:-1]:
            num =  re.sub('\D','',txt[0])
            if num:
              print(num)
              nums.append(num)
          for txt in texts[idx-1][:-1]:
            num =  re.sub('\D','',txt[0])
            if num:
              print(num)
              nums.append(num)
          self.info['HknjaNum'] = nums
        if hkj =="受給者番号":
          for txt in line[:-1]:
            num =  re.sub('\D','',txt[0])
            if num:
              print(num)
              nums.append(num)
          for txt in texts[idx-1][:-1]:
            num =  re.sub('\D','',txt[0])
            if num:
              print(num)
              nums.append(num)
          self.info['Num'] = nums
  #         print(f"{idx}:\t",line[-1])



  

    
      
