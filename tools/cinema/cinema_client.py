"""Klient příkazů pro mód FS25_SprayDroneCinema: zapíše cmd.xml, počká na ack.xml.

from cinema_client import send
ok, msg = send("setTime", hour=18.2)
ok, msg = send("camPath", keys=[{"t": 0, "x": 1, ...}], duration=5, wait=True, timeout=30)
Z příkazové řádky:  python tools/cinema/cinema_client.py ping
                    python tools/cinema/cinema_client.py setTime hour=18.2
                    python tools/cinema/cinema_client.py eval code="1+1"
"""

import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr

GAME = os.path.join(os.path.expanduser("~"), "Documents", "My Games", "FarmingSimulator2025")
DIR = os.path.join(GAME, "modSettings", "FS25_SprayDroneCinema")
CMD = os.path.join(DIR, "cmd.xml")
ACK = os.path.join(DIR, "ack.xml")
KEY_ATTRS = ("t", "x", "y", "z", "rel", "at", "tx", "ty", "tz", "trel", "tat", "fov", "roll", "full")


def fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(round(v, 4))
    return str(v)


def build_xml(cid, action, params, keys, code):
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<cmd id=%s action=%s>" % (quoteattr(str(cid)), quoteattr(action))]
    for name, value in params.items():
        lines.append("  <a n=%s v=%s/>" % (quoteattr(name), quoteattr(fmt(value))))
    for key in keys or []:
        attrs = " ".join("%s=%s" % (k, quoteattr(fmt(key[k]))) for k in KEY_ATTRS if k in key)
        lines.append("  <key %s/>" % attrs)
    if code is not None:
        lines.append("  <code>%s</code>" % code.replace("&", "&amp;").replace("<", "&lt;"))
    lines.append("</cmd>")
    return "\n".join(lines) + "\n"


def write_cmd(text):
    os.makedirs(DIR, exist_ok=True)
    tmp = CMD + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    for _ in range(40):
        try:
            os.replace(tmp, CMD)
            return
        except PermissionError:
            time.sleep(0.05)
    raise RuntimeError("cmd.xml je zamčený")


def read_acks():
    try:
        root = ET.parse(ACK).getroot()
    except (ET.ParseError, FileNotFoundError, PermissionError):
        return {}
    return {r.get("id"): (r.get("ok") == "true", r.get("msg", "")) for r in root.findall("r")}


def new_id():
    return str(int(time.time() * 10))


def send(action, keys=None, code=None, timeout=15.0, **params):
    """Pošle příkaz a počká na ack; vrací (ok, zpráva). Při vypršení (False, 'timeout')."""
    if params.get("wait") and "timeout" not in params:
        params["timeout"] = max(timeout - 1.0, 1.0)
    cid = new_id()
    while cid in read_acks():
        cid = str(int(cid) + 1)
    write_cmd(build_xml(cid, action, params, keys, code))
    end = time.time() + timeout
    while time.time() < end:
        acks = read_acks()
        if cid in acks:
            return acks[cid]
        time.sleep(0.05)
    return False, "timeout (%s)" % action


LUA_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FS25_SprayDroneCinema", "scripts")


def reload_live(timeout=30.0):
    """Nahraje Lua moduly módu ze zdrojové složky projektu bez restartu hry (kopie do nové složky, protože source() cache podle cesty)."""
    import shutil
    dst = os.path.join(DIR, "live", new_id())
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(LUA_SRC):
        shutil.copy2(os.path.join(LUA_SRC, name), os.path.join(dst, name))
    return send("reload", dir=dst.replace("\\", "/") + "/", timeout=timeout)


STATEMENT = re.compile(r"^(local|for|if|while|return|function|do)\b|^[\w.\[\]:\"']+\s*=[^=]|\n|;")


def ev(code, timeout=15.0):
    """Spustí Lua v módu (engine nemá loadstring, proto přes soubor + source). Výraz se vrátí, příkazy mohou mít `return`."""
    code = code.strip()
    body = code if STATEMENT.search(code) else "return " + code
    # source() si pamatuje cestu a soubor podruhé nespustí, proto každé volání dostane nové jméno
    path = os.path.join(DIR, "eval", "eval_%s.lua" % new_id())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for old in sorted(os.listdir(os.path.dirname(path)))[:-20]:
        os.remove(os.path.join(os.path.dirname(path), old))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("local C = SprayDroneCinema\nlocal ok, res = pcall(function()\n%s\nend)\nC.evalResult = (ok and \"\" or \"CHYBA \") .. tostring(res)\n" % body)
    return send("eval", file=path.replace("\\", "/"), timeout=timeout)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    params = {}
    for arg in sys.argv[2:]:
        k, _, v = arg.partition("=")
        params[k] = v
    timeout = float(params.pop("timeout", 15))
    if sys.argv[1] == "reload":
        ok, msg = reload_live()
    elif sys.argv[1] == "eval" and "file" in params:
        import shutil
        copy = os.path.join(DIR, "eval", "file_%s.lua" % new_id())
        os.makedirs(os.path.dirname(copy), exist_ok=True)
        shutil.copyfile(params["file"], copy)
        ok, msg = send("eval", file=copy.replace("\\", "/"), timeout=timeout)
    elif sys.argv[1] == "eval":
        ok, msg = ev(params.get("code", ""), timeout)
    elif sys.argv[1] == "keys":
        ok, msg = ev("C.keysOf(%s)" % params["path"], timeout)
    else:
        ok, msg = send(sys.argv[1], timeout=timeout, **params)
    print(("OK  " if ok else "ERR ") + msg)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
