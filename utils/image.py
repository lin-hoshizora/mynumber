def crop(img):
  crop = img.copy()
  #crop = crop[300:-300, 200:-200, :]
  crop = crop[535:1445, 600:2150, :]
  return crop

def crop_print(img):
  return img[470:1435, 600:2130]
