"""
Normalization + technical attribute extraction.

Stage 1 of the pipeline: turns each CPSE's house-style description into
  (a) a normalized text for embedding/fuzzy comparison
  (b) a structured attribute dict used for hard compatibility checks (veto)
      and standardized description generation.

This is the "domain knowledge" layer — the abbreviations/synonyms here mirror
how Indian CPSE ERPs actually spell material master text.
"""
import re

# Ordered regex passes applied to the lowercased description.
_TEXT_RULES = [
    # unicode / punctuation cleanup
    (r"[–—-]+", " "),
    (r"°", " deg "),
    (r"\s+", " "),
]
# word-level synonym / abbreviation expansion (longest patterns first)
_WORD_RULES = [
    (r"\bhot dip galvanis(?:ed|ation)\b", "hot dip galvanized"),
    (r"\bh\.?d\.?g\.?\b", "hot dip galvanized"),
    (r"\bhdg\b", "hot dip galvanized"),
    (r"\bgalvanised\b", "galvanized"),
    (r"\bzinc pltd\b", "zinc plated"),
    (r"\bzinc plated\b", "zinc plated"),
    (r"\bzn\b", "zinc plated"),
    (r"\bzp\b", "zinc plated"),
    (r"\bblk ox(?:ide)?\b", "black oxide"),
    (r"\bblack\b", "black oxide"),
    (r"\bplain finish\b", "plain"),
    (r"\bpln\b", "plain"),
    # stainless steel grades (incl. A2/A4 European nut/bolt grade codes)
    (r"\bstainless steel 316\b", "ss316"),
    (r"\bs\.?s\.? ?316\b", "ss316"),
    (r"\bss-?316\b", "ss316"),
    (r"\ba4-?70\b", "ss316"),
    (r"\bgr\.?a4-?70\b", "ss316"),
    (r"\bstainless steel 304\b", "ss304"),
    (r"\bs\.?s\.? ?304\b", "ss304"),
    (r"\bss-?304\b", "ss304"),
    (r"\ba2-?70\b", "ss304"),
    (r"\bgr\.?a2-?70\b", "ss304"),
    (r"\btp316\b", "a312 tp316"),
    (r"\btp304\b", "a312 tp304"),
    # materials
    (r"\bcast steel\b", "caststeel"),
    (r"\bc\.?s\.?\b", "caststeel"),
    (r"\bforged steel\b", "forgedsteel"),
    (r"\bf\.?s\.?\b", "forgedsteel"),
    (r"\bcast iron\b", "castiron"),
    (r"\bc\.?i\.?\b", "castiron"),
    (r"\bbrz\b", "bronze"),
    (r"\ba106 gr ?b\b", "a106grb"),
    (r"\ba106-?gr-?b\b", "a106grb"),
    (r"\ba234 ?wpb\b", "a234wpb"),
    (r"\ba234-?wpb\b", "a234wpb"),
    # ends / connections
    (r"\bflg\b", "flanged"),
    (r"\bscr\b", "screwed"),
    (r"\bs\.?w\.?\b", "socket weld"),
    (r"\bwn\b", "weld neck"),
    (r"\bw-n\b", "weld neck"),
    (r"\bs-?o\b", "slip on"),
    (r"\bslip-?on\b", "slip on"),
    (r"\bwafer type\b", "wafer"),
    (r"\braised face\b", "rf"),
    (r"\br\.?f\.?\b", "rf"),
    # bearing terms
    (r"\bd\.?g\.?\b", "deep groove"),
    (r"\bsph\b", "spherical"),
    (r"\bcyl\b", "cylindrical"),
    (r"\bccw33\b", "cc w33"),
    (r"\bcc-?w33\b", "cc w33"),
    (r"\bopen type\b", "open"),
    # seals / finishes / phases
    (r"\b3-?ph(?:ase)?\b", "3 phase"),
    (r"\bmag(?:netic)? float\b", "magnetic float"),
    (r"\bmagnetic\b", "magnetic float"),
    (r"\bbourdon tube\b", "bourdon"),
    (r"\blithium ep\b", "lithiumep"),
    (r"\bli-?ep\b", "lithiumep"),
    (r"\bli\b", "lithium"),
    (r"\bmin\b", "mineral"),
    (r"\be\.?p\.?\b", "ep"),
    # seamless / ERW
    (r"\bsmls\b", "seamless"),
    (r"\be\.?r\.?w\.?\b", "erw"),
    # motor mount phrasing
    (r"\bfoot mounted b3\b", "b3"),
    (r"\bflange mounted b5\b", "b5"),
    (r"\bb-3\b", "b3"),
    (r"\bb-5\b", "b5"),
    # grades (order matters: prefixed/suffixed forms first, bare decimals last)
    (r"\bgr\.?(\d{1,2}(?:\.\d)?)\b", r"grade \1"),
    (r"\b(\d{1,2}(?:\.\d)?) gr\b", r"grade \1"),
    (r"\bb-?7\b", "b7"),
    (r"\bb-?16\b", "b16"),
    (r"(?<!grade )\b(8\.8|10\.9|12\.9|4\.6|5\.6|6\.8)\b", r"grade \1"),
    # pressure class: CL 150 / Class 150 / 150#
    (r"\b(?:cl|class) ?(\d{2,4})\b", r"class \1"),
    (r"\b(\d{3}) ?#", r"class \1"),
    # schedules
    (r"\bsch(?:edule)?[. -]?(\d{2,3})\b", r"sch \1"),
    # standards: IS:1239 / DIN-931 / ASTM-A105 -> spaced form
    (r"\b(is):?(\d{3,5})\b", r"\1 \2"),
    (r"\b(is)-(\d{3,5})\b", r"\1 \2"),
    (r"\b(din)-(\d{3,5})\b", r"\1 \2"),
    (r"\b(astm)-? ?(a\d{3})\b", r"\1 \2"),
    (r"\biso-vg-?(\d{2,3})\b", r"vg \1"),
    (r"\biso vg (\d{2,3})\b", r"vg \1"),
    (r"\bvg-?(\d{2,3})\b", r"vg \1"),
    (r"\bnlgi-?(\d)\b", r"nlgi \1"),
    (r"\bp\.?v\.?c\.?\b", "pvc"),
    # units and packs
    (r"\b(\d+) ?kgs?\b", r"\1 kg"),
    (r"\b(\d+) ?ltr\b", r"\1 l"),
    (r"\b(\d+(?:\.\d+)?) ?hp\b", r"\1 hp"),
    (r"\b(\d+) ?rpm\b", r"\1 rpm"),
    (r"\b(\d+(?:\.\d+)?) ?kv\b", r"\1 kv"),
    (r"\b(\d+) ?m3/hr\b", r"\1 m3hr"),
    (r"\b(\d+) ?lpm\b", r"\1 lpm"),
    (r"\bksc\b", "kg cm2"),
    (r"\bkg/cm2\b", "kg cm2"),
    (r"\b0-(\d+) kg cm2\b", r"range 0-\1"),
    # cable sizes: 3C x 2.5 sqmm / 3Cx2.5 / 3C-2.5SQMM -> canonical
    (r"\b(\d(?:\.\d)?)c ?x ?(\d+(?:\.\d+)?) ?sq ?mm\b", r"\1c x \2 sqmm"),
    (r"\b(\d(?:\.\d)?)c ?x ?(\d+(?:\.\d+)?)\b", r"\1c x \2 sqmm"),
    (r"\bsq ?mm\b", "sqmm"),
    # poles
    (r"\b([234])p\b", r"\1 pole"),
    # family normalization
    (r"\bsocket screw\b", "socket head cap screw"),
    (r"\bmotor\b", "induction motor"),
    (r"\bsteel pipe\b", "pipe"),
    # thread sizes: M16 X 60 / m16 x 60 mm / m16x60mm -> m16x60
    (r"\bm ?(\d{1,2}) ?x ?(\d{1,3}) ?mm\b", r"m\1x\2"),
    (r"\bm ?(\d{1,2}) ?x ?(\d{1,3})\b", r"m\1x\2"),
    # inch sizes: 2" / 2 INCH / 2" NB / 2" NPS -> "2 inch"
    (r"\b(\d+(?:\.\d+)?)\"(?: ?n(?:b|ps))?(?![a-z0-9])", r"\1 inch"),
    (r"\b(\d+(?:\.\d+)?) inch(?: ?n(?:b|ps))?\b", r"\1 inch"),
]


def normalize_text(desc: str) -> str:
    t = desc.lower()
    for pat, rep in _TEXT_RULES:
        t = re.sub(pat, rep, t)
    for pat, rep in _WORD_RULES:
        t = re.sub(pat, rep, t)
    return re.sub(r"\s+", " ", t).strip()


# ---------------------------------------------------------------------------
# Family detection (fine type) -> coarse category
# ---------------------------------------------------------------------------
_TYPE_MAP = [
    ("hex bolt", "fastener"), ("stud bolt", "fastener"), ("socket head cap screw", "fastener"),
    ("hex nut", "fastener"), ("nut", "fastener"), ("flat washer", "fastener"), ("washer", "fastener"),
    ("ball bearing", "bearing"), ("roller bearing", "bearing"), ("bearing", "bearing"),
    ("gate valve", "valve"), ("ball valve", "valve"), ("globe valve", "valve"),
    ("check valve", "valve"), ("butterfly valve", "valve"), ("safety valve", "valve"),
    ("elbow", "fitting"), ("tee", "fitting"), ("reducer", "fitting"), ("flange", "fitting"),
    ("pipe", "pipe"), ("cable", "electrical"), ("induction motor", "electrical"),
    ("contactor", "electrical"), ("mcb", "electrical"),
    ("grease", "lubricant"), ("hydraulic oil", "lubricant"), ("turbine oil", "lubricant"),
    ("gear oil", "lubricant"), ("oil", "lubricant"),
    ("centrifugal pump", "pump"), ("gear pump", "pump"),
    ("pressure gauge", "instrument"), ("thermowell", "instrument"), ("level indicator", "instrument"),
    # loose fallbacks so a typo'd family word still lands in the right block
    ("valve", "valve"), ("pump", "pump"), ("bolt", "fastener"), ("bearing", "bearing"),
    ("gauge", "instrument"), ("cable", "electrical"),
]


def detect_type(norm: str):
    for token, cat in _TYPE_MAP:
        if token in norm:
            return token, cat
    return "unknown", "unknown"


# ---------------------------------------------------------------------------
# Attribute extraction (ordered; operates on normalized text)
# ---------------------------------------------------------------------------
def _find(pattern, text, group=1, cast=str):
    m = re.search(pattern, text)
    return cast(m.group(group)) if m else None


def extract_attrs(norm: str, fine_type: str) -> dict:
    t = norm
    a = {}
    # sizes / threads
    m = re.search(r"\bm(\d{1,2})x(\d{1,3})\b", t)
    if m:
        a["thread"] = f"M{m.group(1)}x{m.group(2)}"
    elif re.search(r"\bhex (?:head )?bolt|stud|socket head cap screw|nut|washer\b", t) or "nut" in t or "washer" in t:
        d = _find(r"\bm(\d{1,2})\b", t)
        if d:
            a["thread"] = f"M{d}"
    # bearing designation + seal (only in bearing context so '2000 mm' or
    # '1440 rpm' in other families is never read as a designation)
    is_bearing = ("bearing" in t or "groove" in t or "roller" in t or "nu " in t or "nu3" in t)
    if is_bearing:
        m = re.search(r"\bnu ?(\d{3,4})( e)?\b", t)
        if m:
            # keep the E-suffix INSIDE the designation: NU310 and NU310 E are
            # different bearings and must hard-conflict even when seal text varies
            a["designation"] = f"NU{m.group(1)} E" if m.group(2) else f"NU{m.group(1)}"
        else:
            # strip std numbers first so DIN 933 isn't read as a designation
            t_nostd = re.sub(r"\b(?:din|iso|is|astm|asme)\s?\d{3,5}\b", " ", t)
            m = re.search(r"\b([1-9]\d{3,4})(?:\s*(2rs|zz|cc w33|w33))?\b", t_nostd)
            if m:
                a["designation"] = m.group(1)
                if m.group(2):
                    a["seal"] = m.group(2)
                elif re.search(rf"\b{m.group(1)} e\b", t_nostd):
                    a["designation"] = f"{m.group(1)} E"
    if "seal" not in a:
        for s in ("2rs", "zz", "cc w33", "w33"):
            if s in t:
                a["seal"] = s
                break
        else:
            if "open" in t and ("bearing" in t or "groove" in t or "roller" in t):
                a["seal"] = "open"
    # valve/pipe specs
    c = _find(r"\bclass (\d{2,4})\b", t)
    if c:
        a["class"] = c
    sch = _find(r"\bsch (\d{2,3})\b", t)
    if sch:
        a["schedule"] = f"SCH {sch}"
    inches = re.findall(r"(\d+(?:\.\d+)?) inch", t)
    if inches:
        a["inch"] = tuple(sorted({float(x) for x in inches}))
    # materials (word-bounded so 'ep' never matches inside 'deep groove')
    for token, tag in (("ss316", "SS316"), ("ss304", "SS304"), ("a312 tp316", "TP316"),
                       ("a312 tp304", "TP304"), ("a106grb", "A106B"), ("a234wpb", "WPB"),
                       ("a105", "A105"), ("a193", "A193"), ("is 1239", "IS1239"),
                       ("caststeel", "caststeel"),
                       ("forgedsteel", "forgedsteel"), ("castiron", "castiron"), ("bronze", "bronze"),
                       ("lithiumep", "lithiumep"), ("lithium", "lithium"), ("mineral", "mineral"),
                       ("ep", "ep"), ("hot dip galvanized", "HDG"), ("zinc plated", "ZN"),
                       ("black oxide", "BLK"), ("plain", "PLN")):
        if re.search(rf"\b{re.escape(token)}\b", t):
            a.setdefault("material", tag)
            break
    # second material pass for finishes as separate attr
    for token, tag in (("hot dip galvanized", "HDG"), ("zinc plated", "ZN"),
                       ("black oxide", "BLK"), ("plain", "PLN")):
        if token in t:
            a["finish"] = tag
            break
    # grades
    g = _find(r"\bgrade (\d{1,2}(?:\.\d)?)\b", t)
    if g:
        a["grade"] = g
    # bare '8' after nut/washer ERPs (CPCL/IOCL render grade without prefix)
    if "grade" not in a and fine_type in ("hex nut", "nut", "flat washer", "washer") \
            and re.search(r"\b8\b", t):
        a["grade"] = "8"
    for token, tag in (("b7", "B7"), ("b16", "B16")):
        if re.search(rf"\b{token}\b", t):
            a["grade"] = tag
            break
    # flange type
    if "weld neck" in t:
        a["flange_type"] = "WN"
    elif "slip on" in t:
        a["flange_type"] = "SO"
    # ends
    for token, tag in (("flanged", "FLG"), ("screwed", "SCR"), ("socket weld", "SW"), ("wafer", "WAFER")):
        if token in t:
            a["end"] = tag
            break
    # electrical
    m = re.search(r"\b(\d(?:\.\d)?)c x (\d+(?:\.\d+)?) sqmm\b", t)
    if m:
        a["cable_size"] = f"{m.group(1)}Cx{m.group(2)}"
    v = _find(r"\b(\d+(?:\.\d+)?) kv\b", t)
    if v:
        a["voltage"] = f"{v} kV"
    hp = _find(r"\b(\d+(?:\.\d+)?) hp\b", t)
    if hp:
        a["hp"] = f"{hp} HP"
    rpm = _find(r"\b(\d{3,4}) rpm\b", t)
    if rpm:
        a["rpm"] = f"{rpm} RPM"
    amps = _find(r"\b(\d{2,3}) a\b", t)
    if amps:
        a["amps"] = f"{amps} A"
    coil = _find(r"\b(\d{2,4}) v ac\b", t)
    if coil:
        a["coil"] = f"{coil} VAC"
    poles = _find(r"\b([234]) pole\b", t)
    if poles:
        a["poles"] = f"{poles}P"
    if re.search(r"\bc curve\b", t):
        a["curve"] = "C"
    for token, tag in (("xlpe", "XLPE"), ("pvc", "PVC")):
        if re.search(rf"\b{token}\b", t):
            a["insulation"] = tag
            break
    if re.search(r"\bb3\b", t):
        a["mount"] = "B3"
    elif re.search(r"\bb5\b", t):
        a["mount"] = "B5"
    if re.search(r"\b3 phase\b", t):
        a["phase"] = "3PH"
    # lubricants
    nlgi = _find(r"\bnlgi (\d)\b", t)
    if nlgi:
        a["nlgi"] = f"NLGI {nlgi}"
    vg = _find(r"\bvg (\d{2,3})\b", t)
    if vg:
        a["viscosity"] = f"VG {vg}"
    pack = _find(r"\b(\d+(?:\.\d+)?) (?:kg|l)\b", t)
    if pack:
        unit = "kg" if re.search(r"\b\d+(?:\.\d+)? kg\b", t) else "L"
        a["pack"] = f"{pack} {unit}"
    # pumps
    flow = _find(r"\b(\d+) m3hr\b", t)
    if flow:
        a["flow"] = f"{flow} m3/hr"
    kw = _find(r"\b(\d+(?:\.\d+)?) kw\b", t)
    if kw:
        a["drive"] = f"{kw} kW"
    head = _find(r"\b(\d+) m\b", t)
    if head and ("pump" in t or "head" in t):
        a["head"] = f"{head} m"
    bar = _find(r"\b(\d+) bar\b", t)
    if bar:
        a["pressure"] = f"{bar} bar"
    lpm = _find(r"\b(\d+(?:\.\d+)?) lpm\b", t)
    if lpm:
        a["flow_lpm"] = f"{lpm} LPM"
    for token, tag in (("mechanical", "MECH"), ("gland", "GLAND")):
        if token in t:
            a["seal_type"] = tag
            break
    # instruments
    rng = _find(r"\brange 0-(\d+)\b", t)
    if rng:
        a["range"] = f"0-{rng} kg/cm2"
    if "magnetic float" in t:
        a["gauge_type"] = "MAGFLOAT"
    if "bourdon" in t:
        a["gauge_type"] = "BOURDON"
    mm = re.findall(r"\b(\d{2,4}) mm\b", t)
    if mm and fine_type in ("thermowell", "level indicator"):
        a["length"] = f"{max(int(x) for x in mm)} mm"
    if "bsp" in t:
        a["connection"] = "BSP"
    elif "npt" in t:
        a["connection"] = "NPT"
    # standards (hard evidence: same material always cites the same standard here)
    stds = re.findall(r"\b(?:din|iso|is|astm|asme)\s?(?:a\d{3}|\d{3,5})\b", t)
    if stds:
        a["std"] = tuple(sorted(set(stds)))
    # angle (elbows)
    ang = _find(r"\b(90|45) deg\b", t)
    if ang:
        a["angle"] = f"{ang} deg"
    return a


# attributes that must match when BOTH rows have them (hard engineering facts)
VETO_ATTRS = ["thread", "designation", "class", "schedule", "inch", "material", "grade",
              "seal", "flange_type", "end", "voltage", "cable_size", "amps", "poles",
              "hp", "rpm", "mount", "nlgi", "viscosity", "pack", "range", "flow",
              "drive", "head", "pressure", "flow_lpm", "seal_type", "connection",
              "angle", "length", "insulation", "curve", "gauge_type", "phase", "coil"]

# Minimum attributes a record MUST carry to be auto-merged. When an ERP row
# is missing one of these, its identity is ambiguous vs same-family variants
# (e.g. a bolt with no grade could be 8.8 or the 10.9 trap) -> human review,
# exactly the PS's "user validation and approval workflow".
MIN_ATTRS = {
    "hex bolt": ["thread"],
    "stud bolt": ["thread", "grade"],
    "socket head cap screw": ["thread", "grade"],
    "hex nut": ["thread"],
    "flat washer": ["thread", "std"],
    "ball bearing": ["designation", "seal"],
    "roller bearing": ["designation"],
    "pipe": ["inch", "schedule", "material"],
    "elbow": ["inch", "schedule", "angle"],
    "tee": ["inch", "schedule"],
    "reducer": ["inch", "schedule"],
    "flange": ["inch", "class", "flange_type"],
    "gate valve": ["inch", "class", "material"],
    "ball valve": ["inch", "class", "material"],
    "globe valve": ["inch", "class", "material"],
    "check valve": ["inch", "class", "material"],
    "butterfly valve": ["inch", "class", "material"],
    "safety valve": ["inch", "class", "material"],
    "cable": ["cable_size", "voltage", "insulation"],
    "induction motor": ["hp", "rpm", "mount"],
    "contactor": ["amps", "poles", "coil"],
    "mcb": ["amps", "poles"],
    "grease": ["nlgi", "pack", "material"],
    "hydraulic oil": ["viscosity", "pack"],
    "turbine oil": ["viscosity", "pack"],
    "gear oil": ["viscosity", "pack"],
    "centrifugal pump": ["flow", "drive"],
    "gear pump": ["flow_lpm", "drive"],
    "pressure gauge": ["range", "connection", "inch"],
    "thermowell": ["inch", "length", "material"],
    "level indicator": ["length", "connection"],
}


def normalize_uom(uom: str) -> str:
    u = (uom or "").strip().upper().rstrip(".")
    if u in ("NOS", "EA", "NUM", "N"):
        return "NOS"
    if u in ("MTR", "MTRS", "METER", "M", "MTR."):
        return "MTR"
    if u in ("PKT", "PACK", "PKTS", "PKT-5", "PKGS"):
        return "PKT"
    if u in ("KG", "KGS", "KG5", "5KG"):
        return "KG"
    if u in ("L", "LTR", "LTR20", "20L"):
        return "L"
    return u or "NOS"
