import json
import asyncio
import websockets

INFO = {
  "Patient": {
    "Birthday": {}
  },
  "Insurance": {
    "HknjaNum": {},
    'Kigo':{},
    "Num": {},
    'Branch': {},
    'KofuYmd':{},
    'YukoStYmd': {},
    'YukoEdYmd': {},
    'RouFtnKbn':{},
    'Code':{},
  }
}

async def ocr():
  async with websockets.connect("ws://localhost:8766") as websocket:
    #await websocket.send('{"Scan": "Insurance"}')    
    await websocket.send('{"Scan": "MyNumber"}')
    #await websocket.send('{"Scan": "shuhoken"}')
    res = await websocket.recv()
    res = json.loads(res)
    print(res)
    await websocket.send(json.dumps(INFO))
    res = await websocket.recv()
    res = json.loads(res)
    for meta_k, meta_v in res.items():
      if isinstance(meta_v, dict):
        for k, v in meta_v.items():
          print(k, v["text"])

asyncio.get_event_loop().run_until_complete(ocr())
