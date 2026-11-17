"""Popis dílů knihovny pro katalog a export: jméno, skupina, varianta z parametrů volání a díly, které žádný vlek nestaví
(dron, starší díly mlýnku). Zdroj dat o použití je parts_lib.stats["calls"] (zapisují ho úlohy katalogu).

    describe(call)  -> {"id", "title", "group", "variant", "variantLabel", "note"}
    extras(PL)      -> volání dílů mimo vleky (nutí postavit je do cache)
"""

import re

GROUPS = ["Elektrocentrála a rozvody", "Nádrže a čerpadla", "Kola", "Mlýnek na vápno", "Přenosná pumpa a násypka", "Dron", "Baterie", "Podvozek a oj"]

# funkce dílu -> (id, název, skupina, popis); popis doplní docstring funkce, když chybí
FUNCS = {
    "sdt_generator.build_generator": ("generator", "Elektrocentrála", GROUPS[0], None),
    "sdt_mixer.build_mixer": ("mixer", "Mixér", GROUPS[0], None),
    "sdt_bigtank.build_main_tanks": ("main_tanks", "Hlavní nádrže", GROUPS[1], None),
    "sdt_tanks.build_induction_tank": ("induction_tank", "Indukční nádrž", GROUPS[1], None),
    "sdt_tanks.build_pump": ("pump_unit", "Čerpadlo vleku", GROUPS[1], None),
    "sdt_lime.build_lime_vessel": ("lime_vessel", "Vápenná nádobka", GROUPS[1], None),
    "sdt_lime.build_rear_hitch": ("rear_hitch", "Tažný věšák", GROUPS[1], None),
    "sdt_rims.build_rim": ("rim", "Disk kola", GROUPS[2], None),
    "sdt_rims.build_tire": ("tire", "Pneumatika", GROUPS[2], None),
    "sdt_mlyn.part_chassis": ("mill_chassis", "Mlýnek: rám", GROUPS[3], None),
    "sdt_mlyn.part_drawbar": ("mill_drawbar", "Mlýnek: oj s podpěrným kolečkem", GROUPS[3], None),
    "sdt_mlyn.part_hopper": ("mill_hopper", "Mlýnek: nádoba na hrubé vápno", GROUPS[3], None),
    "sdt_mlyn.part_auger": ("mill_auger", "Mlýnek: šnek", GROUPS[3], None),
    "sdt_mlyn.part_mill": ("mill_mill", "Mlýnek: kladivový mlýn", GROUPS[3], None),
    "sdt_mlyn.part_engine": ("mill_engine", "Mlýnek: diesel", GROUPS[3], None),
    "sdt_mlyn.part_fuel_tank": ("mill_fuel_tank", "Mlýnek: palivová nádrž", GROUPS[3], None),
    "sdt_mlyn.part_bin": ("mill_bin", "Mlýnek: cyklónová nádobka", GROUPS[3], None),
    "sdt_mlyn.part_control_box": ("mill_control_box", "Mlýnek: rozvaděč", GROUPS[3], None),
    "sdt_mlyn.part_deck_details": ("mill_deck_details", "Mlýnek: akumulátor, klíny, světla", GROUPS[3], None),
    "sdt_mlyn.part_port_cap": ("mill_port_cap", "Mlýnek: slepá spojka", GROUPS[3], None),
    "sdt_mlyn.part_extra_details": ("mill_extra_details", "Mlýnek: doplňkové součástky", GROUPS[3], None),
    "sdt_mlyn.part_hose_end": ("hose_end", "Koncovka hadice Storz", GROUPS[4], None),
    "build_pump.part_frame": ("pump_frame", "Pumpa: rám", GROUPS[4], None),
    "build_pump.part_engine": ("pump_engine", "Motor pumpy a násypky", GROUPS[4], None),
    "build_pump.part_tank": ("pump_tank", "Palivová nádrž pumpy a násypky", GROUPS[4], None),
    "build_pump.part_head": ("pump_head", "Pumpa: těleso čerpadla", GROUPS[4], None),
    "build_pump.part_strainer": ("pump_strainer", "Pumpa: sací koš", GROUPS[4], None),
    "build_hopper.part_frame": ("hopper_frame", "Násypka: rám", GROUPS[4], None),
    "build_hopper.part_funnel": ("hopper_funnel", "Násypka: lievec", GROUPS[4], None),
    "build_hopper.part_feeder": ("hopper_feeder", "Násypka: podavač", GROUPS[4], None),
    "build_drone.part_fuselage": ("drone_fuselage", "Dron: trup", GROUPS[5], None),
    "build_drone.part_tank": ("drone_tank", "Dron: nádrž", GROUPS[5], None),
    "build_drone.part_arm": ("drone_arm", "Dron: rameno s motorem a tryskou", GROUPS[5], None),
    "build_drone.part_rotor": ("drone_rotor", "Dron: vrtule", GROUPS[5], None),
    "build_drone.part_gear": ("drone_gear", "Dron: podvozek", GROUPS[5], None),
    "sdt_parts.battery": ("battery", "Baterie", GROUPS[6], None),
    "sdt_drawbar.part_drawbar_car": ("drawbar_car", "Oj za auto s kulovou hlavou (Middle, Mini)", GROUPS[7], None),
    "sdt_drawbar.part_drawbar_max": ("drawbar_max", "Oj Maxu: A-rám se spojkou za traktor nebo auto", GROUPS[7], None),
    "sdt_deckedge.part_wood_edge": ("wood_edge", "Hrana paluby z dřevěných desek", GROUPS[7], None),
}

BATTERY_KEY = {(0.30, 0.19, 0.11): "S", (0.37, 0.23, 0.13): "M", (0.41, 0.25, 0.145): "L"}


def _val(v):
    """Hodnota z bezztrátového kódování parts_lib.encode (tuple, Vector…) na obyčejný Python."""
    if isinstance(v, dict):
        if "__t" in v:
            return tuple(_val(x) for x in v["__t"])
        if "__v" in v:
            return tuple(v["__v"])
        if "__d" in v:
            return {_val(k): _val(x) for k, x in v["__d"]}
    if isinstance(v, list):
        return [_val(x) for x in v]
    return v


def _slug(text):
    t = text.lower()
    for a, b in (("á", "a"), ("č", "c"), ("ď", "d"), ("é", "e"), ("ě", "e"), ("í", "i"), ("ň", "n"), ("ó", "o"), ("ř", "r"), ("š", "s"),
                 ("ť", "t"), ("ú", "u"), ("ů", "u"), ("ý", "y"), ("ž", "z")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def describe(call):
    """Popis volání dílu (záznam z parts_lib.stats["calls"]): id dílu, varianta (slug a štítek) a skupina. Varianty jsou jen
    skutečné rozdíly tvaru: velikost, parametr dílu."""
    func = call["func"]
    pid, title, group, note = FUNCS[func]
    args = [_val(a) for a in call["args"]["__t"]] if isinstance(call["args"], dict) else [_val(a) for a in call["args"]]
    kwargs = {k: _val(v) for k, v in _val(call["kwargs"]).items()} if call.get("kwargs") else {}
    variant = ""
    if func == "sdt_generator.build_generator":
        variant = "zadní průchodka kabelu" if kwargs.get("rear_socket") else "zásuvka nabíječky na boku"
    elif func == "sdt_tanks.build_induction_tank":
        variant = "s přívodem plnicí hadice" if kwargs.get("hose_inlet") else "základní"
    elif func == "sdt_rims.build_rim":
        variant = str(args[0])
    elif func == "sdt_rims.build_tire":
        variant = f"Ø {args[2] * 2:.2f} m, šířka {args[3]:.2f} m"
    elif func == "sdt_parts.battery":
        key = BATTERY_KEY.get(tuple(round(x, 3) for x in args[1]), "")
        variant = {"S": "S (DB800)", "M": "M (DB1560)", "L": "L (DB2160)"}.get(key, key)
    elif func.startswith("build_drone.part_"):
        variant = f"velikost {args[0]}"
    elif func.startswith("sdt_drawbar.part_drawbar_"):
        variant = f"oj {abs(args[0] - args[1]):.2f} m".replace(".", ",")
    elif func == "sdt_deckedge.part_wood_edge":
        variant = f"délka {args[0]:.2f} m, výška {args[1] * 100:.0f} cm".replace(".", ",")
    return {"id": "part_" + pid, "title": title, "group": group, "variant": _slug(variant), "variantLabel": variant, "note": note,
            "func": func}


def extras(PL):
    """Díly, které žádný vlek ani objekt nestaví, ale patří do knihovny (dron)."""
    import build_drone as BD
    for size in "SML":
        for fn in (BD.part_fuselage, BD.part_tank, BD.part_arm, BD.part_rotor, BD.part_gear):
            PL.call(fn, size)
