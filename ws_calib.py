import time
import json
import asyncio
import subprocess
import websockets

STEP = 10

def set_light(brightness):
  cmd = ["/home/almexusr/client_test/set_light.sh", str(brightness)]
  subprocess.run(cmd)
  time.sleep(1)

async def ocr():
  async with websockets.connect("ws://localhost:8766") as websocket:
    await websocket.send('{"Scan": "Brightness"}')
    res = await websocket.recv()
    res = json.loads(res)
    assert "Brightness" in res
    brightness = int(res["Brightness"]) + STEP
    set_light(res["Brightness"])
    while res.get("Result", "NG") == "NG":
      brightness -= STEP
      set_light(brightness)
      print("try", brightness)
      await websocket.send('{"Scan": "MyNumTest"}')
      res = await websocket.recv()
      res = json.loads(res)
    print("chose brightness", brightness)
    with open("/home/almexusr/brightness.ini", "w") as f:
      f.write(str(brightness))
    while True:
      if input("Put a MyNumber card, enter to continue, q to abort") == "q":
        break
      time.sleep(1)
      await websocket.send('{"Scan":"MyNumber"}')
      res = await websocket.recv()
      res = json.loads(res)
      await websocket.send('{"Patient":{"Birthday":{}},"MyNumber":{"YukoEdYmd":{},"Code":{}}}')
      res = await websocket.recv()
      res = json.loads(res)
      for k, v in res.items():
        if isinstance(v, dict):
          for kk, vv in v.items():
            if "text" in vv:
              print(kk, vv["text"])
            else:
              print(kk, vv)
        else:
          print(k, v)


asyncio.get_event_loop().run_until_complete(ocr())
