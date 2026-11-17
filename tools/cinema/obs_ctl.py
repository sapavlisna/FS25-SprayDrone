"""Ovládání OBS přes obs-websocket v5 (heslo v tmp/trailer/obs_pw.txt).

python tools/cinema/obs_ctl.py setup                 profil SDT (1080p60 CFR, NVENC, mkv), scéna s Game Capture + zvuk hry
python tools/cinema/obs_ctl.py bind                  po spuštění hry: Game Capture na okno hry + zvuk procesu hry
python tools/cinema/obs_ctl.py windows              seznam oken, která umí Game Capture
python tools/cinema/obs_ctl.py start [jmeno]         spustí záznam (soubor out/trailer/obs/<jmeno>.mkv po stop)
python tools/cinema/obs_ctl.py stop                  zastaví záznam, vypíše cestu
python tools/cinema/obs_ctl.py status
Jako modul: from obs_ctl import Obs; o = Obs(); o.start("s01"); ...; path = o.stop()
"""

import base64
import hashlib
import json
import os
import shutil
import sys
import time
import uuid

import websocket

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PW_FILE = os.path.join(ROOT, "tmp", "trailer", "obs_pw.txt")
OUT = os.path.join(ROOT, "out", "trailer", "obs")
PROFILE = "SDT"
COLLECTION = "SDT"
SCENE = "Hra"
GAME_EXE = "FarmingSimulator2025Game.exe"


class Obs:
    def __init__(self, host="127.0.0.1", port=4455):
        self.ws = websocket.create_connection("ws://%s:%d" % (host, port), timeout=15)
        hello = json.loads(self.ws.recv())["d"]
        ident = {"rpcVersion": 1}
        auth = hello.get("authentication")
        if auth:
            with open(PW_FILE, encoding="ascii") as f:
                pw = f.read().strip()
            secret = base64.b64encode(hashlib.sha256((pw + auth["salt"]).encode()).digest()).decode()
            ident["authentication"] = base64.b64encode(hashlib.sha256((secret + auth["challenge"]).encode()).digest()).decode()
        self.ws.send(json.dumps({"op": 1, "d": ident}))
        json.loads(self.ws.recv())

    def call(self, req, data=None, ok_codes=()):
        rid = uuid.uuid4().hex
        self.ws.send(json.dumps({"op": 6, "d": {"requestType": req, "requestId": rid, "requestData": data or {}}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg["op"] == 7 and msg["d"]["requestId"] == rid:
                st = msg["d"]["requestStatus"]
                if not st["result"] and st["code"] not in ok_codes:
                    raise RuntimeError("%s: %s %s" % (req, st["code"], st.get("comment")))
                return msg["d"].get("responseData") or {}

    def start(self, name):
        os.makedirs(OUT, exist_ok=True)
        self.call("SetRecordDirectory", {"recordDirectory": OUT})
        self.call("SetProfileParameter", {"parameterCategory": "Output", "parameterName": "FilenameFormatting", "parameterValue": name})
        self.call("StartRecord")

    def stop(self):
        res = self.call("StopRecord")
        for _ in range(100):
            if not self.status()["outputActive"]:
                break
            time.sleep(0.1)
        time.sleep(0.5)
        return res.get("outputPath")

    def status(self):
        return self.call("GetRecordStatus")

    def game_windows(self):
        res = self.call("GetInputPropertiesListPropertyItems", {"inputName": "Hra - záběr", "propertyName": "window"})
        return [i["itemValue"] for i in res.get("propertyItems", [])]


def setup(o):
    profiles = o.call("GetProfileList")["profiles"]
    if PROFILE not in profiles:
        o.call("CreateProfile", {"profileName": PROFILE})
    else:
        o.call("SetCurrentProfile", {"profileName": PROFILE})
    params = [
        ("Video", "BaseCX", "1920"), ("Video", "BaseCY", "1080"), ("Video", "OutputCX", "1920"), ("Video", "OutputCY", "1080"),
        ("Video", "FPSType", "0"), ("Video", "FPSCommon", "60"),
        ("Output", "Mode", "Advanced"),
        ("AdvOut", "RecType", "Standard"), ("AdvOut", "RecEncoder", "jim_nvenc"), ("AdvOut", "RecFormat2", "mkv"),
        ("AdvOut", "RecFilePath", OUT.replace("/", "\\")), ("AdvOut", "RecTracks", "1"), ("AdvOut", "RecUseRescale", "false"),
        ("Output", "FilenameFormatting", "sdt"),
    ]
    for cat, name, val in params:
        o.call("SetProfileParameter", {"parameterCategory": cat, "parameterName": name, "parameterValue": val})
    o.call("SetVideoSettings", {"baseWidth": 1920, "baseHeight": 1080, "outputWidth": 1920, "outputHeight": 1080, "fpsNumerator": 60, "fpsDenominator": 1})
    os.makedirs(OUT, exist_ok=True)
    cols = o.call("GetSceneCollectionList")["sceneCollections"]
    if COLLECTION not in cols:
        o.call("CreateSceneCollection", {"sceneCollectionName": COLLECTION})
    else:
        o.call("SetCurrentSceneCollection", {"sceneCollectionName": COLLECTION})
    time.sleep(1.5)
    scenes = [s["sceneName"] for s in o.call("GetSceneList")["scenes"]]
    if SCENE not in scenes:
        o.call("CreateScene", {"sceneName": SCENE})
    o.call("SetCurrentProgramScene", {"sceneName": SCENE})
    inputs = [i["inputName"] for i in o.call("GetInputList")["inputs"]]
    if "Hra - záběr" not in inputs:
        o.call("CreateInput", {"sceneName": SCENE, "inputName": "Hra - záběr", "inputKind": "game_capture",
                               "inputSettings": {"capture_mode": "any_fullscreen", "capture_cursor": False, "allow_transparency": False}})
    print("profil a scéna připraveny; okna hry:", [w for w in o.game_windows() if "Farming" in w])


def bind(o):
    wins = [w for w in o.game_windows() if GAME_EXE.lower() in w.lower()]
    if not wins:
        raise SystemExit("okno hry nenalezeno (hra musí běžet)")
    win = wins[0]
    o.call("SetInputSettings", {"inputName": "Hra - záběr", "inputSettings": {"capture_mode": "window", "window": win, "priority": 1}, "overlay": True})
    item = o.call("GetSceneItemId", {"sceneName": SCENE, "sourceName": "Hra - záběr"})["sceneItemId"]
    o.call("SetSceneItemTransform", {"sceneName": SCENE, "sceneItemId": item, "sceneItemTransform": {
        "positionX": 0, "positionY": 0, "alignment": 5, "boundsType": "OBS_BOUNDS_SCALE_INNER", "boundsAlignment": 0, "boundsWidth": 1920, "boundsHeight": 1080}})
    inputs = [i["inputName"] for i in o.call("GetInputList")["inputs"]]
    if "Hra - zvuk" not in inputs:
        o.call("CreateInput", {"sceneName": SCENE, "inputName": "Hra - zvuk", "inputKind": "wasapi_process_output_capture", "inputSettings": {}})
    items = o.call("GetInputPropertiesListPropertyItems", {"inputName": "Hra - zvuk", "propertyName": "window"}).get("propertyItems", [])
    audio = [i["itemValue"] for i in items if GAME_EXE.lower() in i["itemValue"].lower()]
    if audio:
        o.call("SetInputSettings", {"inputName": "Hra - zvuk", "inputSettings": {"window": audio[0]}, "overlay": True})
    print("navázáno:", win, "| zvuk:", audio[:1])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    o = Obs()
    if cmd == "setup":
        setup(o)
    elif cmd == "bind":
        bind(o)
    elif cmd == "windows":
        print("\n".join(o.game_windows()))
    elif cmd == "start":
        o.start(sys.argv[2] if len(sys.argv) > 2 else "sdt")
        print("záznam běží")
    elif cmd == "stop":
        print(o.stop())
    elif cmd == "status":
        print(o.status())
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
