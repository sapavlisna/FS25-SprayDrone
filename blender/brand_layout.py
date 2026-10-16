"""Atlas polepů značky (textures/sdt_brand.dds, 2048 x 2048, DXT5 s alfou) a designy pro konfiguraci Design.

Tvary znaků a barvy podle tmp/logo/znacka-navrhy.html (pole C: mark/word). Kreslí tools/make_brand_atlas.py (Pillow, písma
v assets/fonts), sdt_parts.brand_decal z oblastí počítá UV. Bez bpy, ať jde načíst z obou.

Oblasti na design KEY (pixely x, y, šířka, výška od levého horního rohu):
  lockupOnDark_KEY   znak + nápis + podtitul, světlý text pro tmavý podklad (plachta, tmavý lak), 4 : 1
  lockupOnLight_KEY  totéž s tmavým textem pro světlý podklad, 4 : 1
  mark_KEY           samotný znak (barvy designu, vnitřek bílý), 1 : 1
  stripe_KEY         plný pruh v barvě designu (natahuje se libovolně, vzorkuje se jen vnitřek buňky)
Lockup je v oblasti vystředěný s průhledným okrajem; skutečný podíl obsahu je LOCKUP_CONTENT[KEY].
"""

ATLAS_SIZE = 2048
ATLAS_PNG = "sdt_brand.png"
ATLAS_DDS = "sdt_brand.dds"

DEFAULT_DESIGN = "BZUK"
DESIGN_ORDER = ("BZUK", "ROSA", "KAPKA", "STRATUS")

# p = barva znaku na světlém podkladu, pd = na tmavém, s = doplňková; light_* / dark_* = text lockupu na světlém / tmavém
# podkladu (HTML: .lk.light / .lk.dark); stripe = pruh na plachtě. Vnitřek znaku (vrtule, oblouk) je vždy bílý.
DESIGNS = {
    "BZUK": {"title": "BZUK", "p": "#c8102e", "pd": "#e0263f", "s": "#ffffff", "stripe": "#c8102e",
             "light_fg": "#1a2329", "light_acc": "#c8102e", "dark_fg": "#f2f4f5", "dark_acc": "#ff6b7c"},
    "ROSA": {"title": "ROSA", "p": "#1f6b4a", "pd": "#3f9e6e", "s": "#c3d93b", "stripe": "#c3d93b",
             "light_fg": "#1a2329", "light_acc": "#1f6b4a", "dark_fg": "#f2f4f5", "dark_acc": "#c3d93b"},
    "KAPKA": {"title": "kapka", "p": "#1d6fd1", "pd": "#3d8ff0", "s": "#9fd3ff", "stripe": "#1d6fd1",
              "light_fg": "#1d6fd1", "light_acc": "#9fd3ff", "dark_fg": "#f2f4f5", "dark_acc": "#9fd3ff"},
    "STRATUS": {"title": "STRATUS AGRI", "p": "#2d3a45", "pd": "#c9d3da", "s": "#e86a1c", "stripe": "#e86a1c",
                "light_fg": "#2d3a45", "light_acc": "#e86a1c", "dark_fg": "#f2f4f5", "dark_acc": "#e86a1c"},
}
TARP_COLOR = "#4a4f55"          # plachtovina (SDT_Tarp), design ji nemění
TARP_HEM_COLOR = "#373b40"      # lemy a švy plachty (SDT_TarpHem)
TARP_STRAP_COLOR = "#24272a"    # popruhy (SDT_TarpStrap)

LOCKUP_W, LOCKUP_H = 1024, 256
MARK_SIZE = 512
STRIPE_CELL = (512, 64)          # buňka pruhu; UV bere jen vnitřek (STRIPE_INSET px od kraje), mipmapy nemíchají sousedy
STRIPE_INSET = 12

REGIONS = {}
for _i, _k in enumerate(DESIGN_ORDER):
    REGIONS[f"lockupOnDark_{_k}"] = (0, _i * 2 * LOCKUP_H, LOCKUP_W, LOCKUP_H)
    REGIONS[f"lockupOnLight_{_k}"] = (0, _i * 2 * LOCKUP_H + LOCKUP_H, LOCKUP_W, LOCKUP_H)
    REGIONS[f"mark_{_k}"] = (1024 + (_i % 2) * MARK_SIZE, (_i // 2) * MARK_SIZE, MARK_SIZE, MARK_SIZE)
    REGIONS[f"stripe_{_k}"] = (1024 + STRIPE_INSET, 1024 + _i * STRIPE_CELL[1] + STRIPE_INSET,
                               STRIPE_CELL[0] - 2 * STRIPE_INSET, STRIPE_CELL[1] - 2 * STRIPE_INSET)
del _i, _k

# podíl (šířka, výška) oblasti lockupu, který zabírá obsah (vystředěný); vypisuje make_brand_atlas.py. Nejširší je STRATUS AGRI,
# který je omezený šířkou - polep navrhovat tak, aby se vešel celý obdélník 4 : 1
LOCKUP_CONTENT = {"BZUK": (0.683, 0.906), "ROSA": (0.748, 0.906), "KAPKA": (0.659, 0.906), "STRATUS": (0.977, 0.858)}

KINDS = ("lockupOnDark", "lockupOnLight", "mark", "stripe")


def region_name(kind, design):
    if kind not in KINDS or design not in DESIGNS:
        raise KeyError(f"neznámý polep {kind}/{design}")
    return f"{kind}_{design}"


def aspect(kind):
    """Šířka / výška oblasti (pruh nemá pevný poměr: None)."""
    if kind == "stripe":
        return None
    x, y, w, h = REGIONS[region_name(kind, DEFAULT_DESIGN)]
    return w / h


def uv_rect(name, sub=None):
    """(u0, v0, u1, v1) oblasti v UV (v odspodu). sub = (fx0, fy0, fx1, fy1) výřez oblasti v podílech (y odshora)."""
    x, y, w, h = REGIONS[name]
    fx0, fy0, fx1, fy1 = sub or (0.0, 0.0, 1.0, 1.0)
    s = float(ATLAS_SIZE)
    inset = 0.5
    u0 = (x + inset + (w - 2 * inset) * fx0) / s
    u1 = (x + inset + (w - 2 * inset) * fx1) / s
    v1 = 1.0 - (y + inset + (h - 2 * inset) * fy0) / s
    v0 = 1.0 - (y + inset + (h - 2 * inset) * fy1) / s
    return u0, v0, u1, v1


# uzly s polepy jednoho designu: brand_<KEY>_<místo> (sdt_parts.brand_decal_set); export je sám přidá do i3dMappings,
# nevýchozí skryje a vygeneruje <designConfigurations> (export_middle_mod.design_configurations_xml)
BRAND_NODE_PREFIX = "brand_"


def brand_node_name(design, place):
    return f"{BRAND_NODE_PREFIX}{design}_{place}"


def brand_node_design(name):
    """KEY designu z názvu uzlu brand_<KEY>_<místo>, jinak None."""
    if not name.startswith(BRAND_NODE_PREFIX):
        return None
    key = name[len(BRAND_NODE_PREFIX):].split("_", 1)[0]
    return key if key in DESIGNS else None
