"""Čistý snímek projektu do větve `release` (jeden commit na vydání, bez vývojové historie).

Vezme commitnutý stav HEAD (ne pracovní kopii), vybere jen zveřejnitelné soubory, z Lua modu odstraní ladění a výsledek
zapíše jako nový commit větve `release`, aniž by sáhl na pracovní kopii nebo index. Ven se pushuje jen `release`.

Použití:
    .venv\\Scripts\\python.exe tools\\make_release.py "Release 1.0.0.0"     sestaví, ověří a commitne
    .venv\\Scripts\\python.exe tools\\make_release.py "..." --publish        navíc pushne a založí GitHub Release se zipem
                                                                            (tag v<version> z modDesc, verze se nesmí opakovat)
    .venv\\Scripts\\python.exe tools\\make_release.py --dry [--worktree]    jen sestaví do tmp/release/tree a ověří

Ladění se pozná podle příznaků (DEBUG, *.DEBUG_*, SprayDroneDebug.*, SprayDroneToolbox.debugLog), které jsou ve výchozím
stavu vypnuté: podmínky se vyhodnotí s nimi jako false, mrtvé větve zmizí, živé se rozbalí. Funkce se jménem *debug*
a funkce, které po úklidu nikdo nevolá, zmizí taky. Když v kódu zůstane cokoli, co vypadá jako ladění, skript skončí chybou.
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT / "tmp" / "release"
TREE = OUT / "tree"
BRANCH = "release"
MOD = "mod/FS25_SprayDroneTrailer"

INCLUDE = [
    MOD,
    "blender/templates",
    "blender/textures",
    "assets/fonts",
    "assets/gallery",
]
BLENDER_SCRIPTS = [
    "brand_layout", "build_canister", "build_drone", "build_link_items", "build_spray_mist", "build_trailer",
    "build_trailer_max", "build_trailer_middle", "build_trailer_mill", "build_trailer_mini", "canister_labels", "decal_layout",
    "export_max_mod", "export_middle_mod", "export_mill_mod", "export_mini_mod", "export_rims", "headless_max", "headless_middle",
    "headless_mill", "headless_mini", "sdt_bigtank", "sdt_contract", "sdt_generator", "sdt_labels", "sdt_lime", "sdt_mixer",
    "sdt_mlyn", "sdt_nozzle", "sdt_parts", "sdt_paths", "sdt_rims", "sdt_tanks",
]
TOOLS = [
    "audit_spec_fields", "check_all", "check_compound", "check_save", "check_xml_nodes", "lua_check",
    "make_brand_atlas", "make_decal_atlas", "make_map_icons", "make_relay_icon", "png2dds", "test_headlands",
    "test_mixer", "test_split", "validate_mod",
]
INCLUDE += [f"blender/{n}.py" for n in BLENDER_SCRIPTS] + [f"tools/{n}.py" for n in TOOLS]
EXTRA = PROJECT / "tools" / "release"  # README a .gitignore pro release
ZIP = OUT / "FS25_SprayDroneTrailer.zip"
MOD_FORMATS = {".xml", ".lua", ".dds", ".i3d", ".shapes", ".anim", ".ogg", ".wav", ".gls", ".ogv", ".gdm", ".grle", ".cache"}
REMOTE = "github"
# veřejné repo: autor bez soukromého e-mailu (GitHub noreply účtu sapavlisna)
PUBLIC_AUTHOR = {
    "GIT_AUTHOR_NAME": "sapavlisna", "GIT_AUTHOR_EMAIL": "8099203+sapavlisna@users.noreply.github.com",
    "GIT_COMMITTER_NAME": "sapavlisna", "GIT_COMMITTER_EMAIL": "8099203+sapavlisna@users.noreply.github.com",
}
RELEASE_NOTES = """## FS25 Spray Drone Service Trailer {version}

### Instalace

Stáhni `{zip}` a vlož ho (nerozbalený) do `Documents/My Games/FarmingSimulator2025/mods/`.

Vleky, kanystry, relé tyč a tablet najdeš v obchodě ve vlastních kategoriích modu.
"""
DROP = [f"{MOD}/scripts/SprayDroneDebug.lua"]

LOCAL_PATH = re.compile(r"[A-Za-z]:[\\/]+(SteamLibrary|FS25-edit|ClaudeProjects|Users)", re.I)
# ve veřejném repu se autor uvádí jen jako sapavlisna
PRIVATE = re.compile(r"Mazálek|Mazalek|iresoft", re.I)
ALLOWED = re.compile(r"debug\.traceback|drawDebugLine")
LEFTOVER = re.compile(r"SprayDroneDebug|\bDEBUG\b|DEBUG_|Logging\.info|\bprint\(|debugLog|function [\w.:]*[dD]ebug|[Ll]adění|[Ll]adic")
DEBUG_COMMENT = re.compile(r"debug|DEBUG|[Ll]adění|[Ll]adic")


# --- Lua: tokeny -------------------------------------------------------------------------------------------------------

LONG_OPEN = re.compile(r"\[(=*)\[")
NAME = re.compile(r"[A-Za-z_]\w*")
NUMBER = re.compile(r"0[xX][0-9a-fA-F]+|(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")
SYMBOLS = ["...", "..", "==", "~=", "<=", ">=", "::"]


def tokenize(src):
    toks, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c.isspace():
            i += 1
            continue
        start = i
        if src.startswith("--", i):
            m = LONG_OPEN.match(src, i + 2)
            if m:
                close = "]" + m.group(1) + "]"
                i = src.index(close, m.end()) + len(close)
            else:
                j = src.find("\n", i)
                i = n if j < 0 else j
            toks.append(("comment", src[start:i], start, i))
            continue
        if c in "\"'":
            i += 1
            while src[i] != c:
                i += 2 if src[i] == "\\" else 1
            i += 1
            toks.append(("string", src[start:i], start, i))
            continue
        m = LONG_OPEN.match(src, i)
        if m:
            close = "]" + m.group(1) + "]"
            i = src.index(close, m.end()) + len(close)
            toks.append(("string", src[start:i], start, i))
            continue
        m = NAME.match(src, i) or NUMBER.match(src, i)
        if m and m.end() > i:
            i = m.end()
            toks.append(("name" if c.isalpha() or c == "_" else "number", src[start:i], start, i))
            continue
        for s in SYMBOLS:
            if src.startswith(s, i):
                i += len(s)
                break
        else:
            i += 1
        toks.append(("sym", src[start:i], start, i))
    return toks


def code_tokens(src):
    return [t for t in tokenize(src) if t[0] != "comment"]


# --- Lua: bloky --------------------------------------------------------------------------------------------------------

def parse_blocks(toks):
    """Najde příkazy if (s větvemi) a definice funkcí. Indexy jsou do toks."""
    ifs, funcs, stack = [], [], []
    for k, (kind, text, _, _) in enumerate(toks):
        if kind != "name":
            continue
        top = stack[-1] if stack else None
        if text == "if":
            node = {"type": "if", "start": k, "branches": [{"kw": k, "then": None}], "else": None, "end": None}
            stack.append(node)
        elif text == "then" and top and top["type"] == "if" and top["branches"][-1]["then"] is None:
            top["branches"][-1]["then"] = k
        elif text == "elseif" and top and top["type"] == "if":
            top["branches"].append({"kw": k, "then": None})
        elif text == "else" and top and top["type"] == "if":
            top["else"] = k
        elif text == "function":
            name, local = "", k > 0 and toks[k - 1][1] == "local"
            j = k + 1
            while j < len(toks) and toks[j][1] != "(":
                name += toks[j][1]
                j += 1
            stack.append({"type": "function", "start": k - 1 if local else k, "name": name, "end": None})
        elif text in ("while", "for"):
            stack.append({"type": "loop", "await_do": True})
        elif text == "do":
            if top and top.get("await_do"):
                top["await_do"] = False
            else:
                stack.append({"type": "do"})
        elif text == "repeat":
            stack.append({"type": "repeat"})
        elif text == "until":
            stack.pop()
        elif text == "end":
            node = stack.pop()
            node["end"] = k
            if node["type"] == "if":
                ifs.append(node)
            elif node["type"] == "function":
                funcs.append(node)
    assert not stack, "neuzavřený blok"
    return ifs, funcs


# --- Lua: vyhodnocení podmínek s vypnutým laděním ----------------------------------------------------------------------

def is_debug_atom(texts):
    s = "".join(texts)
    if re.fullmatch(r"DEBUG|[\w.]*\.DEBUG_\w+|SprayDroneDebug(\.\w+)*|[\w.]*\.debugLog", s):
        return True
    return False


class Expr:
    def __init__(self, op, items=None, text=None, value=None):
        self.op, self.items, self.text, self.value = op, items or [], text, value


def parse_expr(toks):
    pos = [0]

    def peek():
        return toks[pos[0]][1] if pos[0] < len(toks) else None

    def parse_or():
        items = [parse_and()]
        while peek() == "or":
            pos[0] += 1
            items.append(parse_and())
        return items[0] if len(items) == 1 else Expr("or", items)

    def parse_and():
        items = [parse_not()]
        while peek() == "and":
            pos[0] += 1
            items.append(parse_not())
        return items[0] if len(items) == 1 else Expr("and", items)

    def parse_not():
        if peek() == "not":
            pos[0] += 1
            return Expr("not", [parse_not()])
        return parse_atom()

    def parse_atom():
        start, depth = pos[0], 0
        while pos[0] < len(toks):
            t = toks[pos[0]][1]
            if depth == 0 and t in ("and", "or", ")"):
                break
            if t in "([{":
                depth += 1
            elif t in ")]}":
                depth -= 1
            pos[0] += 1
        part = toks[start:pos[0]]
        texts = [t[1] for t in part]
        if texts and texts[0] == "(" and matching(texts, 0) == len(texts) - 1:
            return Expr("paren", [parse_expr(part[1:-1])])
        if any(t in ("==", "~=", "<", ">", "<=", ">=") for t in texts) and any(is_debug_atom([t]) for t in texts):
            # srovnání s laděním (např. SprayDroneDebug ~= nil) se neumí vyhodnotit, ale musí zmizet spolu s okolím
            return Expr("atom", text=" ".join(texts), value=None)
        return Expr("atom", text=src_join(part), value=False if is_debug_atom(texts) else None)

    e = parse_or()
    assert pos[0] == len(toks), "nečekaný token v podmínce: " + " ".join(t[1] for t in toks)
    return e


def matching(texts, i):
    depth = 0
    for j in range(i, len(texts)):
        if texts[j] in "([{":
            depth += 1
        elif texts[j] in ")]}":
            depth -= 1
            if depth == 0:
                return j
    return -1


SOURCE = {"src": ""}


def src_join(part):
    return SOURCE["src"][part[0][2]:part[-1][3]] if part else ""


def simplify(e):
    """Vrátí (hodnota True/False/None, zjednodušený Expr, změněno)."""
    if e.op == "atom":
        return e.value, e, False
    if e.op == "paren":
        v, inner, ch = simplify(e.items[0])
        return v, inner if ch else e, ch
    if e.op == "not":
        v, inner, ch = simplify(e.items[0])
        return (None if v is None else not v), Expr("not", [inner]), ch
    absorb, neutral = (False, True) if e.op == "and" else (True, False)
    kept, changed = [], False
    for item in e.items:
        v, s, ch = simplify(item)
        changed |= ch
        if v is absorb:
            return absorb, None, True
        if v is neutral:
            changed = True
            continue
        kept.append(s)
    for s in kept:
        if s.op == "atom" and s.text and LEFTOVER.search(s.text):
            raise ValueError("podmínka míchá ladění s logikou, kterou nejde vyhodnotit: " + s.text)
    if not kept:
        return neutral, None, True
    if len(kept) == 1:
        return None, kept[0], True
    return None, Expr(e.op, kept), changed


def emit(e, parent=None):
    if e.op == "atom":
        return e.text
    if e.op == "paren":
        return "(" + emit(e.items[0]) + ")"
    if e.op == "not":
        inner = e.items[0]
        s = emit(inner, "not")
        return "not " + (s if inner.op in ("atom", "paren") else "(" + s + ")")
    s = f" {e.op} ".join(emit(i, e.op) for i in e.items)
    return "(" + s + ")" if parent in ("and", "not") and e.op == "or" else s


# --- Lua: úpravy textu -------------------------------------------------------------------------------------------------

def line_bounds(src, start, end):
    """Rozšíří úsek na celé řádky, když jsou kolem jen mezery; jinak vrátí původní."""
    ls = src.rfind("\n", 0, start) + 1
    le = src.find("\n", end)
    le = len(src) if le < 0 else le + 1
    if src[ls:start].strip() == "" and src[end:le].strip() == "":
        return ls, le, True
    return start, end, False


def with_debug_comments(src, start):
    """Posune začátek celořádkového úseku nad souvislé komentářové řádky, které mluví o ladění."""
    while start > 0:
        ps = src.rfind("\n", 0, start - 1) + 1
        line = src[ps:start].strip()
        if not line.startswith("--") or not DEBUG_COMMENT.search(line):
            break
        start = ps
    return start


def with_comments(src, start):
    while start > 0:
        ps = src.rfind("\n", 0, start - 1) + 1
        if not src[ps:start].strip().startswith("--"):
            break
        start = ps
    return start


def dedent(text):
    return "".join(l[4:] if l.startswith("    ") else l.lstrip(" ") if l.strip() == "" else l for l in text.splitlines(True))


def has_top_local(toks, a, b):
    depth = 0
    for kind, text, _, _ in toks[a:b]:
        if kind != "name":
            continue
        if text in ("if", "function", "do", "repeat"):
            depth += 1
        elif text in ("end", "until"):
            depth -= 1
        elif text == "local" and depth == 0:
            return True
    return False


def rewrite_if(src, toks, node):
    branches = []
    for b_i, br in enumerate(node["branches"]):
        nxt = node["branches"][b_i + 1]["kw"] if b_i + 1 < len(node["branches"]) else (node["else"] or node["end"])
        cond = toks[br["kw"] + 1:br["then"]]
        v, e, ch = simplify(parse_expr(cond))
        branches.append({"value": v, "expr": e, "changed": ch, "cond": cond, "body": (br["then"], nxt)})
    else_body = (node["else"], node["end"]) if node["else"] is not None else None
    if not any(b["changed"] or b["value"] is not None for b in branches):
        return None
    kept = []
    for b in branches:
        if b["value"] is False:
            continue
        if b["value"] is True:
            else_body = b["body"]
            break
        kept.append(b)
    a, z = toks[node["start"]][2], toks[node["end"]][3]
    if not kept:
        if else_body is None:
            s, e, full = line_bounds(src, a, z)
            return (with_debug_comments(src, s) if full else s), e, ""
        k0, k1 = else_body
        body_a, body_z = toks[k0][3], toks[k1][2]
        s, e, full = line_bounds(src, a, z)
        if not full:
            raise ValueError("rozbalení if uprostřed řádku")
        if has_top_local(toks, k0 + 1, k1):
            indent = src[s:a]
            return s, e, indent + "do" + src[body_a:body_z] + "end\n"
        body = src[body_a:body_z]
        body = body[body.find("\n") + 1:] if body[:body.find("\n") + 1].strip() == "" else body
        body = body[:body.rfind("\n") + 1]
        return s, e, dedent(body)
    out = ""
    for idx, b in enumerate(kept):
        cond = emit(b["expr"]) if b["changed"] else src_join(b["cond"])
        k0, k1 = b["body"]
        out += ("if " if idx == 0 else "elseif ") + cond + " then" + src[toks[k0][3]:toks[k1][2]]
    if else_body is not None:
        k0, k1 = else_body
        out += "else" + src[toks[k0][3]:toks[k1][2]]
    return a, z, out + "end"


def apply_edits(src, edits):
    edits.sort(key=lambda x: x[0])
    out, last = [], 0
    for s, e, rep in edits:
        if s < last:
            continue
        out.append(src[last:s])
        out.append(rep)
        last = e
    out.append(src[last:])
    return "".join(out)


def outermost(ranges):
    ranges = sorted(ranges, key=lambda r: (r[0], -r[1]))
    res, end = [], -1
    for r in ranges:
        if r[0] >= end:
            res.append(r)
            end = r[1]
    return res


def strip_ifs(src):
    while True:
        SOURCE["src"] = src
        toks = code_tokens(src)
        ifs, _ = parse_blocks(toks)
        edits = []
        for node in ifs:
            r = rewrite_if(src, toks, node)
            if r is not None:
                edits.append(r)
        edits = outermost(edits)
        if not edits:
            return src
        src = apply_edits(src, edits)


DEBUG_LINE = re.compile(r"^[ \t]*(local\s+)?[\w.]*\b(DEBUG\w*|debug\w*)\s*=.*\n|^[ \t]*source\(.*SprayDroneDebug.*\n", re.M)


def strip_lines(src):
    edits = []
    for m in DEBUG_LINE.finditer(src):
        edits.append((with_debug_comments(src, m.start()), m.end(), ""))
    return apply_edits(src, outermost(edits))


def func_short(name):
    return re.split(r"[.:]", name)[-1]


def strip_functions(sources, original, others):
    """Odstraní funkce *debug* a funkce, které před úklidem někdo volal a po něm už nikdo."""
    def counts(texts):
        joined = "\n".join(texts)
        return lambda w: len(re.findall(r"(?<![\w])" + re.escape(w) + r"(?!\w)", joined))
    before = counts(original)
    removed = set()
    while True:
        changed = False
        now = counts(list(sources.values()) + others)
        for path, src in sources.items():
            SOURCE["src"] = src
            toks = code_tokens(src)
            _, funcs = parse_blocks(toks)
            edits = []
            for f in funcs:
                short = func_short(f["name"])
                if not short:
                    continue
                dead = now(short) == 1 and before(short) > 1
                if "debug" in short.lower() or dead:
                    a, z = toks[f["start"]][2], toks[f["end"]][3]
                    s, e, full = line_bounds(src, a, z)
                    if not full:
                        continue
                    edits.append((with_comments(src, s), e, ""))
                    removed.add(f["name"])
                    if "debug" not in short.lower():
                        print(f"  bez volání po úklidu: {f['name']}")
            if edits:
                sources[path] = apply_edits(src, outermost(edits))
                changed = True
        if not changed:
            break
    # samostatné řádky s voláním odstraněné funkce (funkce se hlídala sama, volání bylo bez podmínky)
    for name in removed:
        call = re.compile(r"^[ \t]*" + re.escape(name).replace(r"\.", r"[.:]") + r"\([^\n]*\)[ \t]*\n", re.M)
        for path, src in sources.items():
            sources[path] = call.sub("", src)


DEBUG_LOCAL = re.compile(r"^[ \t]*local (\w+) = [^\n]*(DEBUG|SprayDroneDebug)[^\n]*\n", re.M)
DEBUG_FIELD = re.compile(r"\"\w*[dD]ebug\w*\",?[ \t]*")
COMMENT_LINE = re.compile(r"^[ \t]*--[^\n]*\n", re.M)
SEPARATOR = re.compile(r"^[ \t]*-{10,}[ \t]*\n(?=[ \t]*\n|\Z)", re.M)


def used_in_function(src, m):
    """Je lokální proměnná z řádku m použitá dál ve své funkci (do nejbližšího `end` na začátku řádku)?"""
    end = re.compile(r"^end\b", re.M).search(src, m.end())
    body = src[m.end():end.start() if end else len(src)]
    return re.search(r"(?<![\w.])" + m.group(1) + r"(?!\w)", body) is not None


def tidy(src):
    while True:
        m = next((m for m in DEBUG_LOCAL.finditer(src) if not used_in_function(src, m)), None)
        if m is None:
            break
        src = src[:m.start()] + src[m.end():]
    src = DEBUG_FIELD.sub("", src)
    src = re.sub(r"^[ \t]*\n", "\n", src, flags=re.M)  # řádky po vyškrtnutých položkách
    src = COMMENT_LINE.sub(lambda m: "" if LEFTOVER.search(m.group(0)) or re.search(r"[dD]ebug", m.group(0)) else m.group(0), src)
    src = SEPARATOR.sub("", src)
    src = re.sub(r"[ \t]+\n", "\n", src)
    src = re.sub(r"\n{3,}", "\n\n", src)
    return src


# --- sestavení ---------------------------------------------------------------------------------------------------------

def git(*args, env=None, input=None):
    r = subprocess.run(["git", *args], cwd=PROJECT, capture_output=True, env=env, input=input)
    if r.returncode:
        sys.exit(f"git {' '.join(args)}: {r.stderr.decode('utf-8', 'replace')}")
    return r.stdout


def export_tree(worktree):
    if TREE.exists():
        shutil.rmtree(TREE)
    TREE.mkdir(parents=True)
    if worktree:
        for rel in git("ls-files", "-z", "--", *INCLUDE).decode("utf-8").split("\0"):
            if rel and (PROJECT / rel).exists():
                (TREE / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(PROJECT / rel, TREE / rel)
    else:
        data = git("archive", "--format=tar", "HEAD", "--", *INCLUDE)
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(TREE, filter="data")
    for rel in DROP:
        (TREE / rel).unlink()
    # ModHub (TestRunner ObsoleteFiles) v modu nepovoluje jiné formáty: licence a podobné přijdou do repa vedle modu
    for p in sorted((TREE / MOD).rglob("*")):
        if p.is_file() and p.suffix.lower() not in MOD_FORMATS:
            dst = TREE / "licenses" / p.relative_to(TREE / MOD).as_posix().replace("/", "_")
            dst.parent.mkdir(exist_ok=True)
            p.replace(dst)
    for f in EXTRA.iterdir():
        shutil.copy2(f, TREE / f.name)
    for p in TREE.rglob("__pycache__"):
        shutil.rmtree(p)


def clean_mod():
    files = sorted((TREE / MOD / "scripts").rglob("*.lua"))
    original = [f.read_text(encoding="utf-8") for f in files]
    original.append((PROJECT / MOD / "scripts" / "SprayDroneDebug.lua").read_text(encoding="utf-8"))
    others = [p.read_text(encoding="utf-8") for p in (TREE / MOD).rglob("*.xml")]
    original += others
    sources = {}
    for f in files:
        sources[f] = strip_lines(strip_ifs(f.read_text(encoding="utf-8").replace("\r\n", "\n")))
    strip_functions(sources, original, others)
    for f, src in sources.items():
        f.write_text(tidy(src), encoding="utf-8", newline="")


def verify():
    bad = []
    for f in sorted((TREE / MOD).rglob("*.lua")):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            line_ = ALLOWED.sub("", line)
            if LEFTOVER.search(line_) or re.search(r"[dD]ebug", line_):
                bad.append(f"{f.relative_to(TREE)}:{n}: {line.strip()}")
    for f in sorted(p for p in TREE.rglob("*") if p.suffix in (".py", ".md", ".lua", ".xml", ".in", ".json")):
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if LOCAL_PATH.search(line):
                bad.append(f"{f.relative_to(TREE)}:{n}: místní cesta: {line.strip()}")
            if PRIVATE.search(line):
                bad.append(f"{f.relative_to(TREE)}:{n}: soukromé jméno nebo adresa: {line.strip()}")
    if (TREE / MOD / "modDesc.xml").read_text(encoding="utf-8").find("Debug") >= 0:
        bad.append("modDesc.xml: zmínka o Debug")
    from lupa import luajit21
    lua = luajit21.LuaRuntime()
    check = lua.eval("function(src, name) local f, err = loadstring(src, name) return err end")
    for f in sorted((TREE / MOD).rglob("*.lua")):
        err = check(f.read_text(encoding="utf-8"), "@" + f.name)
        if err:
            bad.append(f"syntaxe: {err}")
    return bad


def commit(message):
    index = OUT / "index"
    if index.exists():
        index.unlink()
    env = dict(os.environ, GIT_INDEX_FILE=str(index))
    git("--work-tree", str(TREE), "add", "-A", ".", env=env)
    tree = git("write-tree", env=env).decode().strip()
    parent = subprocess.run(["git", "rev-parse", "--verify", "-q", f"refs/heads/{BRANCH}"], cwd=PROJECT,
                            capture_output=True).stdout.decode().strip()
    if parent and git("rev-parse", f"{parent}^{{tree}}").decode().strip() == tree:
        print(f"{BRANCH}: beze změny proti {parent[:9]}")
        return
    args = ["commit-tree", tree, "-F", "-"] + (["-p", parent] if parent else [])
    sha = git(*args, input=message.encode("utf-8"), env=dict(os.environ, **PUBLIC_AUTHOR)).decode().strip()
    git("update-ref", f"refs/heads/{BRANCH}", sha, *( [parent] if parent else ["0" * 40]))
    print(f"{BRANCH}: {sha[:9]} {message.splitlines()[0]}")


def make_zip():
    """Mod k instalaci: obsah složky modu v kořeni zipu, jak ho hra čte z mods/."""
    root = TREE / MOD
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(root.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(root).as_posix())
    print(f"zip: {ZIP} ({ZIP.stat().st_size / 1e6:.1f} MB)")


def mod_version():
    return re.search(r"<version>([^<]+)</version>", (TREE / MOD / "modDesc.xml").read_text(encoding="utf-8")).group(1)


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], cwd=PROJECT, capture_output=True)
    if check and r.returncode:
        sys.exit(f"gh {' '.join(args)}: {r.stderr.decode('utf-8', 'replace')}")
    return r


def publish():
    """Pushne `release` na GitHub (jako main) a založí GitHub Release s tagem podle verze v modDesc a zipem modu."""
    url = git("remote", "get-url", REMOTE).decode().strip()
    repo = re.search(r"github\.com[/:](.+?)(\.git)?$", url).group(1)
    tag = "v" + mod_version()
    if gh("release", "view", tag, "-R", repo, check=False).returncode == 0:
        sys.exit(f"CHYBA: {tag} už je vydaná, zvyš <version> v modDesc.xml")
    git("push", REMOTE)
    gh("release", "create", tag, str(ZIP), "-R", repo, "--target", "main", "--title", tag,
       "--notes", RELEASE_NOTES.format(version=tag[1:], zip=ZIP.name))
    print(f"vydáno: https://github.com/{repo}/releases/tag/{tag}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("message", nargs="?")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--worktree", action="store_true", help="s --dry: vzít pracovní kopii místo HEAD")
    ap.add_argument("--publish", action="store_true", help="po commitu pushnout a založit GitHub Release se zipem")
    a = ap.parse_args()
    if not a.dry and not a.message:
        sys.exit("chybí zpráva commitu (nebo --dry)")
    if a.worktree and not a.dry:
        sys.exit("--worktree jde jen s --dry")
    if a.publish and a.dry:
        sys.exit("--publish nejde s --dry")
    export_tree(a.worktree)
    clean_mod()
    bad = verify()
    if bad:
        print("\n".join(bad))
        sys.exit(f"CHYBA: v release zůstalo ladění nebo chyba syntaxe ({len(bad)})")
    print(f"ok: {TREE}")
    make_zip()
    if not a.dry:
        commit(a.message)
    if a.publish:
        publish()


if __name__ == "__main__":
    main()
