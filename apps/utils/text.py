"""
Subset of the same module in mainstream ocr2
"""
import regex as re


NUM_FIX = {
  'ｌ': '１',
  'ｉ': '１',
  'Ⅰ': '１',
  'ｔ': '１',
  '」': '１',
  '「': '１',
  '丁': '１',
  '亅': '１',
  '｝': '１',
  '｛': '１',
  'ｏ': '０',
  'ｓ': '５',
  'ｇ': '９',
}

dup_nums = re.compile(r'\D{2,}\d{3}[年月日]')

def fix_num(text):
  text = text.replace('５印年', '５０年')
  use_fix = False
  if re.findall('[年月日]\D[年月日]', text):
    use_fix = True
  if '番号' in text or '記号' in text:
    use_fix = True
  if len(text) == 2 and text[1] == '割':
    use_fix = True
  if use_fix:
    for k in NUM_FIX:
      text = text.replace(k, NUM_FIX[k])
  return text


def clean_year(line):
  matched = dup_nums.search(line[-1])
  if matched is None:
    return line
  start, end = matched.span()
  if line[0][1][start:end-1].min() > 0.95:
    return line
  rm_idx = line[0][1][start:end-1].argmin() + start
  line[-1] = line[-1][:rm_idx] + line[-1][rm_idx+1:]
  return line


def get_date(txt, return_jp_year):

  def search(pattern, txt):
    suffix = '([^\d-])\s*(0[1-9]|[1-9]|1[0-2])([^\d-])\s*(0[1-9]|[1-9]|[1-2][0-9]0*|3[0-1]0*|99)(\D|$)'
    m = re.findall(pattern + suffix, txt)
    return m

  def western_year(m, offset, return_jp_year):
    if return_jp_year:
      dates = [(str(int(gs[1]) + offset) + gs[3].zfill(2) + gs[5][:2].zfill(2), gs[1].zfill(2) + gs[3].zfill(2) + 
                gs[5][:2].zfill(2)) for gs in m]
    else:
      dates = [str(int(gs[1]) + offset) + gs[3].zfill(2) + gs[5][:2].zfill(2) for gs in m]
    return dates

  txt = re.sub('\D年', '元年', txt)
  txt = txt.replace('元年', '1年').replace(' ', '')
  txt = txt.replace('末日', '99日').replace('未目', '99日').replace('末目', '99日').replace('未日', '99日')
  m_r = search('(令和|合和)(0[1-9]|[1-9]|[1-9][0-9])', txt)
  m_h = search('(平成(?<!\d)){e<2}(0[1-9]|[1-9]|[1-4][0-9])', txt)
  m_s = search('(昭[^\d\s\pP])(0[1-9]|[1-9]|[1-5][0-9]|6[0-4])', txt)
  m_d = search('(大正(?<!\d)){e<2}(0[1-9]|[1-9]|1[0-5])', txt)
  m_m = search('(明治(?<!\d)){e<2}(0[1-9]|[1-9]|[1-3][0-9]|4[0-5])', txt)
  m_w = search('(19[0-9]{2}|2[0-9]{3})', txt)
  dates = []

  if m_m:
    dates += western_year(m_m, 1867, return_jp_year)
  if m_d:
    dates += western_year(m_d, 1911, return_jp_year)
  if m_s:
    dates += western_year(m_s, 1925, return_jp_year)
  if m_h:
    dates += western_year(m_h, 1988, return_jp_year)
  if m_r:
    dates += western_year(m_r, 2018, return_jp_year)
  if m_w:
      dates += [(gs[0]+gs[2].zfill(2)+gs[4].zfill(2),) for gs in m_w]
  return dates
