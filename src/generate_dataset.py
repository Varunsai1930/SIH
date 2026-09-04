"""
SIH26099 — Synthetic multi-CPSE material master dataset generator (v2).

Simulates the real-world problem: the same physical material is described
differently by each CPSE's ERP (different code formats, description styles,
synonyms, abbreviations, UOM spellings, typos, missing attributes), plus
intra-CPSE duplicates and near-miss "trap" materials that look similar but
are NOT equivalent.

Ground truth (`true_material_id`) lets us measure matching accuracy.
T#### = canonical real material, X#### = trap variant (near-miss, distinct).

Outputs: data/raw/{cpse}_materials.csv for CPCL, IOCL, NTPC, SAIL.
"""
import csv
import random
from pathlib import Path

random.seed(42)
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Material universe: (category, family, attrs dict, [trap variants])
# Trap variants change exactly one attribute => near-miss, NOT the same item.
# ---------------------------------------------------------------------------
M = []
def mat(category, family, attrs, traps=None):
    M.append((category, family, attrs, traps or []))

# --- fasteners ---
mat("fastener", "hex bolt", {"size": "M16x60", "grade": "8.8", "std": "DIN 931", "finish": "black oxide"},
    [{"size": "M16x60", "grade": "10.9", "std": "DIN 931", "finish": "black oxide"}])          # grade trap
mat("fastener", "hex bolt", {"size": "M12x40", "grade": "8.8", "std": "IS 1364", "finish": "zinc plated"},
    [{"size": "M12x45", "grade": "8.8", "std": "IS 1364", "finish": "zinc plated"}])          # length trap
mat("fastener", "hex bolt", {"size": "M10x40", "grade": "10.9", "std": "DIN 933", "finish": "hot dip galvanized"},
    [{"size": "M10x40", "grade": "8.8", "std": "DIN 933", "finish": "hot dip galvanized"}])   # grade trap
mat("fastener", "hex bolt", {"size": "M20x80", "grade": "8.8", "std": "DIN 933", "finish": "black oxide"}, [])
mat("fastener", "hex bolt", {"size": "M10x30", "grade": "A2-70", "std": "DIN 933", "finish": "plain"},
    [{"size": "M10x30", "grade": "A4-70", "std": "DIN 933", "finish": "plain"}])               # SS304 vs SS316 trap
mat("fastener", "hex bolt", {"size": "M12x50", "grade": "A4-70", "std": "DIN 931", "finish": "plain"}, [])
for d in (14, 18, 24):
    mat("fastener", "hex bolt", {"size": f"M{d}x{d*4}", "grade": "8.8", "std": "DIN 933",
                                 "finish": "hot dip galvanized"})
mat("fastener", "hex nut", {"size": "M16", "grade": "8", "std": "DIN 934", "finish": "zinc plated"}, [])
mat("fastener", "hex nut", {"size": "M10", "grade": "A2-70", "std": "DIN 934", "finish": "plain"},
    [{"size": "M10", "grade": "A4-70", "std": "DIN 934", "finish": "plain"}])
for d in (12, 14, 18, 20):
    mat("fastener", "hex nut", {"size": f"M{d}", "grade": "8", "std": "DIN 934", "finish": "hot dip galvanized"})
mat("fastener", "flat washer", {"size": "M16", "std": "DIN 125", "finish": "zinc plated"},
    [{"size": "M16", "std": "DIN 9021", "finish": "zinc plated"}])                            # std trap
for d in (10, 12, 14, 18):
    mat("fastener", "flat washer", {"size": f"M{d}", "std": "DIN 125", "finish": "zinc plated"})
mat("fastener", "stud bolt", {"size": "M20x100", "grade": "B7", "std": "ASTM A193", "finish": "plain"},
    [{"size": "M20x100", "grade": "B16", "std": "ASTM A193", "finish": "plain"}])             # B7 vs B16 trap
mat("fastener", "stud bolt", {"size": "M16x80", "grade": "B7", "std": "ASTM A193", "finish": "plain"}, [])
mat("fastener", "socket screw", {"size": "M8x25", "grade": "12.9", "std": "DIN 912", "finish": "black oxide"}, [])
mat("fastener", "socket screw", {"size": "M10x30", "grade": "12.9", "std": "DIN 912", "finish": "zinc plated"},
    [{"size": "M10x35", "grade": "12.9", "std": "DIN 912", "finish": "zinc plated"}])

# --- bearings ---
mat("bearing", "ball bearing", {"type": "deep groove", "designation": "6205", "bore": "25 mm", "seal": "2RS"},
    [{"type": "deep groove", "designation": "6205", "bore": "25 mm", "seal": "ZZ"}])          # seal trap
mat("bearing", "ball bearing", {"type": "deep groove", "designation": "6204", "bore": "20 mm", "seal": "open"}, [])
for n in (7, 8, 9):
    mat("bearing", "ball bearing", {"type": "deep groove", "designation": f"62{n}",
                                    "bore": f"{10*n-35} mm", "seal": "2RS"})
mat("bearing", "ball bearing", {"type": "deep groove", "designation": "6210", "bore": "50 mm", "seal": "open"}, [])
mat("bearing", "ball bearing", {"type": "deep groove", "designation": "6305", "bore": "25 mm", "seal": "2RS"},
    [{"type": "deep groove", "designation": "6305", "bore": "25 mm", "seal": "ZZ"}])
mat("bearing", "roller bearing", {"type": "spherical", "designation": "22206", "bore": "30 mm", "seal": "open"}, [])
mat("bearing", "roller bearing", {"type": "spherical", "designation": "22217", "bore": "85 mm", "seal": "CC W33"}, [])
mat("bearing", "roller bearing", {"type": "cylindrical", "designation": "NU310", "bore": "50 mm", "seal": "open"},
    [{"type": "cylindrical", "designation": "NU310 E", "bore": "50 mm", "seal": "open"}])    # E-suffix nuance

# --- valves ---
mat("valve", "gate valve", {"size": '2"', "class": "150", "body": "cast steel", "end": "flanged"},
    [{"size": '2"', "class": "300", "body": "cast steel", "end": "flanged"}])                 # class trap
mat("valve", "gate valve", {"size": '3"', "class": "150", "body": "cast steel", "end": "flanged"}, [])
mat("valve", "gate valve", {"size": '4"', "class": "300", "body": "cast steel", "end": "flanged"}, [])
mat("valve", "gate valve", {"size": '1.5"', "class": "800", "body": "forged steel", "end": "socket weld"}, [])
mat("valve", "ball valve", {"size": '1"', "class": "150", "body": "SS 316", "end": "screwed"},
    [{"size": '1"', "class": "150", "body": "SS 304", "end": "screwed"}])                     # 316 vs 304 trap
mat("valve", "ball valve", {"size": '2"', "class": "800", "body": "SS 316", "end": "flanged"}, [])
mat("valve", "globe valve", {"size": '1.5"', "class": "800", "body": "forged steel", "end": "socket weld"},
    [{"size": '2"', "class": "800", "body": "forged steel", "end": "socket weld"}])           # size trap
mat("valve", "globe valve", {"size": '2"', "class": "150", "body": "cast steel", "end": "flanged"}, [])
mat("valve", "check valve", {"size": '2"', "class": "150", "body": "cast iron", "end": "flanged"}, [])
mat("valve", "check valve", {"size": '3"', "class": "150", "body": "cast steel", "end": "flanged"}, [])
mat("valve", "butterfly valve", {"size": '6"', "class": "150", "body": "cast iron", "end": "wafer"}, [])
mat("valve", "safety valve", {"size": '1"x1.5"', "class": "150", "body": "bronze", "end": "screwed"}, [])

# --- pipes ---
mat("pipe", "seamless pipe", {"size": '2" NPS', "schedule": "SCH 40", "mat": "ASTM A106 Gr B", "type": "seamless"},
    [{"size": '2" NPS', "schedule": "SCH 80", "mat": "ASTM A106 Gr B", "type": "seamless"}])  # schedule trap
mat("pipe", "seamless pipe", {"size": '3" NPS', "schedule": "SCH 40", "mat": "ASTM A106 Gr B", "type": "seamless"}, [])
mat("pipe", "seamless pipe", {"size": '6" NPS', "schedule": "SCH 40", "mat": "ASTM A106 Gr B", "type": "seamless"}, [])
mat("pipe", "seamless pipe", {"size": '1" NPS', "schedule": "SCH 80", "mat": "ASTM A106 Gr B", "type": "seamless"}, [])
mat("pipe", "erw pipe", {"size": '4" NPS', "schedule": "SCH 40", "mat": "IS 1239", "type": "ERW"}, [])
mat("pipe", "ss pipe", {"size": '2" NPS', "schedule": "SCH 10", "mat": "A312 TP316", "type": "seamless"},
    [{"size": '2" NPS', "schedule": "SCH 10", "mat": "A312 TP304", "type": "seamless"}])      # TP316 vs TP304

# --- fittings ---
mat("fitting", "elbow", {"size": '2"', "schedule": "SCH 40", "mat": "ASTM A234 WPB", "angle": "90 deg"},
    [{"size": '2"', "schedule": "SCH 40", "mat": "ASTM A234 WPB", "angle": "45 deg"}])        # angle trap
mat("fitting", "elbow", {"size": '3"', "schedule": "SCH 40", "mat": "ASTM A234 WPB", "angle": "90 deg"}, [])
mat("fitting", "tee", {"size": '2"', "schedule": "SCH 40", "mat": "ASTM A234 WPB"}, [])
mat("fitting", "tee", {"size": '1"', "schedule": "SCH 80", "mat": "ASTM A234 WPB"},
    [{"size": '1"', "schedule": "SCH 40", "mat": "ASTM A234 WPB"}])
mat("fitting", "reducer", {"size": '2"x1"', "schedule": "SCH 40", "mat": "ASTM A234 WPB"}, [])
mat("fitting", "flange", {"size": '2"', "class": "150", "face": "RF", "mat": "ASTM A105", "type": "slip-on"},
    [{"size": '2"', "class": "150", "face": "RF", "mat": "ASTM A105", "type": "weld neck"}])  # SO vs WN trap
mat("fitting", "flange", {"size": '3"', "class": "300", "face": "RF", "mat": "ASTM A105", "type": "weld neck"}, [])
mat("fitting", "flange", {"size": '1"', "class": "150", "face": "RF", "mat": "ASTM A105", "type": "slip-on"}, [])

# --- electrical ---
mat("electrical", "cable", {"type": "XLPE", "size": "3C x 2.5 sqmm", "voltage": "1.1 kV"},
    [{"type": "XLPE", "size": "3C x 4.0 sqmm", "voltage": "1.1 kV"}])                         # size trap
mat("electrical", "cable", {"type": "PVC", "size": "2C x 1.5 sqmm", "voltage": "1.1 kV"}, [])
mat("electrical", "cable", {"type": "XLPE", "size": "4C x 10 sqmm", "voltage": "1.1 kV"}, [])
mat("electrical", "motor", {"rating": "5 HP", "speed": "1440 RPM", "mount": "B3", "phase": "3 phase"},
    [{"rating": "5 HP", "speed": "1440 RPM", "mount": "B5", "phase": "3 phase"}])             # mount trap
mat("electrical", "motor", {"rating": "10 HP", "speed": "1440 RPM", "mount": "B3", "phase": "3 phase"}, [])
mat("electrical", "contactor", {"rating": "32 A", "poles": "4 pole", "coil": "230 V AC"}, [])
mat("electrical", "contactor", {"rating": "65 A", "poles": "3 pole", "coil": "230 V AC"},
    [{"rating": "65 A", "poles": "4 pole", "coil": "230 V AC"}])
mat("electrical", "mcb", {"rating": "32 A", "poles": "4P", "curve": "C curve", "voltage": "415 V"}, [])
mat("electrical", "mcb", {"rating": "63 A", "poles": "4P", "curve": "C curve", "voltage": "415 V"},
    [{"rating": "63 A", "poles": "2P", "curve": "C curve", "voltage": "415 V"}])

# --- lubricants ---
mat("lubricant", "grease", {"grade": "NLGI 2", "base": "lithium", "pack": "5 kg"},
    [{"grade": "NLGI 3", "base": "lithium", "pack": "5 kg"}])                                 # NLGI trap
mat("lubricant", "grease", {"grade": "NLGI 2", "base": "lithium EP", "pack": "18 kg"},
    [{"grade": "NLGI 2", "base": "lithium EP", "pack": "5 kg"}])                              # pack trap
mat("lubricant", "hydraulic oil", {"viscosity": "ISO VG 46", "type": "mineral", "pack": "20 L"}, [])
mat("lubricant", "turbine oil", {"viscosity": "ISO VG 46", "type": "mineral", "pack": "20 L"}, [])  # same VG, diff type!
mat("lubricant", "gear oil", {"viscosity": "ISO VG 220", "type": "EP", "pack": "20 L"},
    [{"viscosity": "ISO VG 320", "type": "EP", "pack": "20 L"}])
mat("lubricant", "turbine oil", {"viscosity": "ISO VG 32", "type": "mineral", "pack": "20 L"}, [])

# --- pumps ---
mat("pump", "centrifugal pump", {"head": "32 m", "flow": "25 m3/hr", "seal": "mechanical", "drive": "3.7 kW"},
    [{"head": "32 m", "flow": "25 m3/hr", "seal": "mechanical", "drive": "5.5 kW"}])          # drive trap
mat("pump", "centrifugal pump", {"head": "50 m", "flow": "45 m3/hr", "seal": "mechanical", "drive": "7.5 kW"}, [])
mat("pump", "gear pump", {"head": "10 bar", "flow": "0.5 LPM", "seal": "gland", "drive": "1.5 kW"}, [])

# --- instruments ---
mat("instrument", "pressure gauge", {"range": "0-10 kg/cm2", "size": '4"', "connection": "1/2 BSP", "type": "bourdon"},
    [{"range": "0-16 kg/cm2", "size": '4"', "connection": "1/2 BSP", "type": "bourdon"}])     # range trap
mat("instrument", "pressure gauge", {"range": "0-10 kg/cm2", "size": '6"', "connection": "1/2 BSP", "type": "bourdon"}, [])
mat("instrument", "thermowell", {"size": '1/2"', "length": "150 mm", "mat": "SS 316"},
    [{"size": '1/2"', "length": "150 mm", "mat": "SS 304"}])
mat("instrument", "level indicator", {"range": "0-2000 mm", "type": "magnetic float", "connection": '1" NPT'}, [])

# ---------------------------------------------------------------------------
# Per-CPSE house styles
# ---------------------------------------------------------------------------
CPSES = ["CPCL", "IOCL", "NTPC", "SAIL"]

FAMILY_UPPER = {
    "hex bolt": "HEX BOLT", "hex nut": "HEX NUT", "flat washer": "FLAT WASHER",
    "stud bolt": "STUD BOLT", "socket screw": "SOCKET HEAD CAP SCREW",
    "ball bearing": "BALL BEARING", "roller bearing": "ROLLER BEARING",
    "gate valve": "GATE VALVE", "ball valve": "BALL VALVE", "globe valve": "GLOBE VALVE",
    "check valve": "CHECK VALVE", "butterfly valve": "BUTTERFLY VALVE", "safety valve": "SAFETY VALVE",
    "seamless pipe": "PIPE SEAMLESS", "erw pipe": "PIPE ERW", "ss pipe": "PIPE SS",
    "elbow": "ELBOW", "tee": "TEE", "reducer": "REDUCER", "flange": "FLANGE",
    "cable": "CABLE", "motor": "INDUCTION MOTOR", "contactor": "CONTACTOR", "mcb": "MCB",
    "grease": "GREASE", "hydraulic oil": "HYDRAULIC OIL", "turbine oil": "TURBINE OIL",
    "gear oil": "GEAR OIL", "centrifugal pump": "CENTRIFUGAL PUMP", "gear pump": "GEAR PUMP",
    "pressure gauge": "PRESSURE GAUGE", "thermowell": "THERMOWELL", "level indicator": "LEVEL INDICATOR",
}

# canonical value -> per-CPSE rendering (how each ERP spells the same attribute)
SYN = {
    "hot dip galvanized": {"CPCL": "HDG", "IOCL": "Hot Dip Galvanised", "NTPC": "H.D.G.", "SAIL": "GALVANIZED"},
    "zinc plated":        {"CPCL": "ZN",  "IOCL": "Zinc Plated",        "NTPC": "Zinc Pltd",  "SAIL": "ZP"},
    "black oxide":        {"CPCL": "BLK OX", "IOCL": "Black Oxide",      "NTPC": "Blk Oxide",  "SAIL": "BLACK"},
    "plain":              {"CPCL": "PLN", "IOCL": "Plain",              "NTPC": "Plain Finish", "SAIL": "PLAIN"},
    "cast steel":        {"CPCL": "CS", "IOCL": "Cast Steel",            "NTPC": "C.S.",       "SAIL": "CAST STEEL"},
    "forged steel":      {"CPCL": "FS", "IOCL": "Forged Steel",         "NTPC": "F.S.",       "SAIL": "FORGED STEEL"},
    "cast iron":         {"CPCL": "CI", "IOCL": "Cast Iron",             "NTPC": "C.I.",       "SAIL": "CAST IRON"},
    "bronze":            {"CPCL": "BRZ", "IOCL": "Bronze",               "NTPC": "Bronze",     "SAIL": "BRONZE"},
    "SS 316":            {"CPCL": "SS 316", "IOCL": "Stainless Steel 316", "NTPC": "S.S. 316", "SAIL": "SS-316"},
    "SS 304":            {"CPCL": "SS 304", "IOCL": "Stainless Steel 304", "NTPC": "S.S. 304", "SAIL": "SS-304"},
    "flanged":           {"CPCL": "FLG", "IOCL": "Flanged",              "NTPC": "Flanged",    "SAIL": "FLANGED"},
    "screwed":           {"CPCL": "SCR", "IOCL": "Screwed",              "NTPC": "Screwed",    "SAIL": "SCREWED"},
    "socket weld":       {"CPCL": "SW",  "IOCL": "Socket Weld",         "NTPC": "S.W.",       "SAIL": "SOCKET WELD"},
    "wafer":             {"CPCL": "WAFER", "IOCL": "Wafer Type",         "NTPC": "Wafer",      "SAIL": "WAFER"},
    "deep groove":       {"CPCL": "DG",  "IOCL": "Deep Groove",         "NTPC": "D.G.",       "SAIL": "DEEP GROOVE"},
    "spherical":         {"CPCL": "SPH", "IOCL": "Spherical",            "NTPC": "Spherical",  "SAIL": "SPHERICAL"},
    "cylindrical":       {"CPCL": "CYL", "IOCL": "Cylindrical",          "NTPC": "Cylindrical", "SAIL": "CYLINDRICAL"},
    "mechanical":        {"CPCL": "MECH", "IOCL": "Mechanical Seal",     "NTPC": "Mech.",      "SAIL": "MECH"},
    "gland":             {"CPCL": "GLAND", "IOCL": "Gland Packing",      "NTPC": "Gland",      "SAIL": "GLAND"},
    "3 phase":           {"CPCL": "3 PH", "IOCL": "3 Phase",             "NTPC": "3-Phase",    "SAIL": "3 PHASE"},
    "seamless":          {"CPCL": "SMLS", "IOCL": "Seamless",            "NTPC": "SMLS",       "SAIL": "SEAMLESS"},
    "ERW":               {"CPCL": "ERW", "IOCL": "ERW",                  "NTPC": "E.R.W.",     "SAIL": "ERW"},
    "weld neck":         {"CPCL": "WN",  "IOCL": "Weld Neck",            "NTPC": "W-N",        "SAIL": "WELD NECK"},
    "slip-on":           {"CPCL": "SO",  "IOCL": "Slip-On",              "NTPC": "S-O",        "SAIL": "SLIP ON"},
    "RF":                {"CPCL": "RF",  "IOCL": "Raised Face",         "NTPC": "R.F.",       "SAIL": "RF"},
    "bourdon":           {"CPCL": "BOURDON", "IOCL": "Bourdon Tube",     "NTPC": "Bourdon",    "SAIL": "BOURDON"},
    "magnetic float":    {"CPCL": "MAG FLOAT", "IOCL": "Magnetic Float", "NTPC": "Mag Float",  "SAIL": "MAGNETIC"},
    "lithium":           {"CPCL": "LI",   "IOCL": "Lithium",             "NTPC": "Lithium",    "SAIL": "LITHIUM"},
    "lithium EP":        {"CPCL": "LI-EP", "IOCL": "Lithium EP",         "NTPC": "Lithium-EP", "SAIL": "LITHIUM EP"},
    "mineral":           {"CPCL": "MIN", "IOCL": "Mineral",              "NTPC": "Mineral",    "SAIL": "MINERAL"},
    "EP":                {"CPCL": "EP",  "IOCL": "EP",                   "NTPC": "E.P.",      "SAIL": "EP"},
    "XLPE":              {"CPCL": "XLPE", "IOCL": "XLPE",                "NTPC": "XLPE",      "SAIL": "XLPE"},
    "PVC":               {"CPCL": "PVC",  "IOCL": "PVC",                 "NTPC": "P.V.C.",     "SAIL": "PVC"},
    "2RS":               {"CPCL": "2RS", "IOCL": "2RS",                  "NTPC": "2RS",        "SAIL": "2 RS"},
    "ZZ":                {"CPCL": "ZZ",  "IOCL": "ZZ",                  "NTPC": "ZZ",         "SAIL": "ZZ"},
    "open":              {"CPCL": "OPEN", "IOCL": "Open Type",           "NTPC": "Open",       "SAIL": "OPEN"},
    "CC W33":            {"CPCL": "CCW33", "IOCL": "CC W33",             "NTPC": "C.C. W33",   "SAIL": "CC-W33"},
    "B3":                {"CPCL": "B3",  "IOCL": "Foot Mounted B3",     "NTPC": "B-3",        "SAIL": "B3"},
    "B5":                {"CPCL": "B5",  "IOCL": "Flange Mounted B5",    "NTPC": "B-5",        "SAIL": "B5"},
}

UOM_BY_CATEGORY = {"fastener": "NOS", "bearing": "NOS", "valve": "NOS", "pipe": "MTR",
                   "fitting": "NOS", "electrical": "NOS", "lubricant": "PKT",
                   "pump": "NOS", "instrument": "NOS"}
UOM_VARIANT = {"CPCL": {"NOS": "NOS", "MTR": "MTR", "PKT": "PKT"},
               "IOCL": {"NOS": "EA", "MTR": "METER", "PKT": "PKT"},
               "NTPC": {"NOS": "NOS.", "MTR": "MTRS", "PKT": "PACK"},
               "SAIL": {"NOS": "NUM", "MTR": "MTR.", "PKT": "PKTS"}}

# category code systems — each CPSE classifies differently (and sometimes wrong)
CAT_CODES = {
    "CPCL": {"fastener": "FST", "bearing": "BRG", "valve": "VLV", "pipe": "PIP",
             "fitting": "FIT", "electrical": "ELE", "lubricant": "LUB", "pump": "PMP", "instrument": "INS"},
    "IOCL": {"fastener": "110", "bearing": "220", "valve": "310", "pipe": "340",
             "fitting": "350", "electrical": "410", "lubricant": "520", "pump": "630", "instrument": "740"},
    "NTPC": {"fastener": "MC-F", "bearing": "MC-B", "valve": "MC-V", "pipe": "MC-P",
             "fitting": "MC-PF", "electrical": "MC-E", "lubricant": "MC-L", "pump": "MC-PM", "instrument": "MC-I"},
    "SAIL": {"fastener": "A1", "bearing": "B2", "valve": "C3", "pipe": "D4",
             "fitting": "D5", "electrical": "E6", "lubricant": "F7", "pump": "G8", "instrument": "H9"},
}

HSN = {"fastener": "7318", "bearing": "8482", "valve": "8481", "pipe": "7304",
       "fitting": "7307", "electrical": "8544", "lubricant": "2710", "pump": "8413", "instrument": "9026"}

# indicative base price (INR) per family — used for the price-variance story
BASE_PRICE = {"hex bolt": 18, "hex nut": 6, "flat washer": 3, "stud bolt": 95, "socket screw": 22,
              "ball bearing": 260, "roller bearing": 1850, "gate valve": 4800, "ball valve": 1350,
              "globe valve": 3600, "check valve": 2900, "butterfly valve": 3200, "safety valve": 4200,
              "seamless pipe": 310, "erw pipe": 240, "ss pipe": 890, "elbow": 380, "tee": 420,
              "reducer": 510, "flange": 640, "cable": 95, "motor": 18500, "contactor": 1900,
              "mcb": 450, "grease": 420, "hydraulic oil": 310, "turbine oil": 340, "gear oil": 290,
              "centrifugal pump": 28500, "gear pump": 15400, "pressure gauge": 1450,
              "thermowell": 890, "level indicator": 12500}
CPSE_PRICE_FACTOR = {"CPCL": 1.00, "IOCL": 1.06, "NTPC": 1.14, "SAIL": 0.94}


def render_value(v, cpse):
    v = str(v)
    if v in SYN:
        return SYN[v][cpse]
    # grades: 8.8 / 8 / 10.9 / 12.9 / A2-70 / A4-70 / B7 / B16
    if v in ("8.8", "8", "10.9", "12.9"):
        return {"CPCL": v, "IOCL": v, "NTPC": f"Gr.{v}", "SAIL": f"{v} GR"}[cpse]
    if v in ("A2-70", "A4-70"):
        return {"CPCL": v, "IOCL": v, "NTPC": f"Gr.{v}", "SAIL": v.replace("-", "")}[cpse]
    if v in ("B7", "B16"):
        return {"CPCL": v, "IOCL": v, "NTPC": f"B-{v[1:]}", "SAIL": v}[cpse]
    # metric thread sizes: M16x60
    if v.startswith("M") and "x" in v:
        d, L = v[1:].split("x")
        return {"CPCL": v, "IOCL": f"M{d} X {L}", "NTPC": f"M{d} x {L} mm", "SAIL": f"{v}MM"}[cpse]
    # cable sizes: 3C x 2.5 sqmm
    if " sqmm" in v:
        return {"CPCL": v.replace(" sqmm", ""), "IOCL": v, "NTPC": v.replace(" x ", " X ").replace("sqmm", "Sq mm"),
                "SAIL": v.replace(" x ", "-").replace(" sqmm", "SQMM")}[cpse]
    # pressure classes: 150 / 300 / 800
    if v in ("150", "300", "800") and v not in ("8",):
        return {"CPCL": f"CL {v}", "IOCL": f"Class {v}", "NTPC": f"Class {v}", "SAIL": f"{v}#"}[cpse]
    # sizes like 2" / 2" NPS / 1"x1.5" / 2"x1"
    if '"' in v:
        out = v
        if cpse == "IOCL":
            out = v.replace('"', '"')
        if cpse == "NTPC":
            out = v.replace(" NPS", " NB").replace('"', '"')
        if cpse == "SAIL":
            out = v.replace(" NPS", " NB").replace('"', " INCH")
        return out
    # standards: IS 1364 -> IS:1364 (IOCL), DIN-931 (SAIL)
    if v[:3] in ("DIN", "ASTM", "A193") or v.startswith("ASTM") or v.split(" ")[0] in ("IS", "ISO"):
        if cpse == "IOCL" and v.startswith("IS "):
            return v.replace("IS ", "IS:")
        if cpse == "SAIL":
            return v.replace(" ", "-")
        return v
    return v


def render_desc(category, family, attrs, cpse, rng):
    cfg_typo = {"CPCL": 0.10, "IOCL": 0.08, "NTPC": 0.12, "SAIL": 0.06}[cpse]
    cfg_drop = {"CPCL": 0.15, "IOCL": 0.10, "NTPC": 0.22, "SAIL": 0.12}[cpse]
    parts = []
    for k, v in attrs.items():
        if rng.random() < cfg_drop:
            continue
        parts.append(render_value(v, cpse))
    if not parts:
        parts = [render_value(list(attrs.values())[0], cpse)]
    rng.shuffle(parts)
    head = FAMILY_UPPER[family] if cpse in ("CPCL", "SAIL") else family.title()
    if cpse == "CPCL":
        desc = f"{head} " + ", ".join(parts)
    elif cpse == "IOCL":
        desc = f"{head} – " + " – ".join(parts)
    elif cpse == "NTPC":
        desc = f"{head}, " + ", ".join(parts)
    else:  # SAIL — block caps, slash separated
        desc = f"{head} / " + " / ".join(parts)
    # occasional realistic typos
    if rng.random() < cfg_typo:
        chars = list(desc)
        i = rng.randrange(len(chars))
        if chars[i].isalpha():
            chars[i] = rng.choice("abcdefghkmnoprstuvwxz")
        desc = "".join(chars)
    return desc


def material_code(cpse, seq, rng):
    """Each CPSE formats codes differently — codes are meaningless globally."""
    if cpse == "CPCL":
        return f"MAT{100000 + seq}"
    if cpse == "IOCL":
        return f"RM-{seq:05d}"
    if cpse == "NTPC":
        return f"EGW{seq:06d}"
    return f"S{100000 + seq * 7}"  # SAIL non-contiguous


def main():
    rng = random.Random(2026)
    rows = []
    seq = {c: 1 for c in CPSES}
    tid = 0
    xid = 5000

    universe = []
    for category, family, attrs, traps in M:
        tid += 1
        universe.append((category, family, attrs, f"T{tid:04d}"))
        for trap in traps:
            xid += 1
            universe.append((category, family, trap, f"X{xid:04d}"))

    for cpse in CPSES:
        for category, family, attrs, true_id in universe:
            is_trap = true_id.startswith("X")
            if rng.random() > (0.60 if is_trap else 0.85):
                continue
            for _ in range(2):  # first appearance + possible intra-CPSE duplicate
                if _ == 1 and (is_trap or rng.random() > 0.18):
                    break
                desc = render_desc(category, family, attrs, cpse, rng)
                code = material_code(cpse, seq[cpse], rng)
                seq[cpse] += 1
                uom = UOM_VARIANT[cpse][UOM_BY_CATEGORY[category]]
                # category hint: 15% blank, 8% wrong code (dirty ERP data)
                hint = CAT_CODES[cpse][category]
                r = rng.random()
                if r < 0.15:
                    hint = ""
                elif r < 0.23:
                    hint = rng.choice([c for k, c in CAT_CODES[cpse].items() if k != category])
                # HSN: mostly correct, sometimes blank
                hsn = HSN[category] if rng.random() > 0.12 else ""
                base = BASE_PRICE[family]
                price = round(base * CPSE_PRICE_FACTOR[cpse] * rng.uniform(0.92, 1.08))
                rows.append({
                    "cpse": cpse,
                    "material_code": code,
                    "description": desc,
                    "uom": uom,
                    "category_hint": hint,
                    "hsn_code": hsn,
                    "last_rate_inr": price,
                    "true_material_id": true_id,
                })

    for cpse in CPSES:
        out = OUT_DIR / f"{cpse.lower()}_materials.csv"
        cpse_rows = [r for r in rows if r["cpse"] == cpse]
        rng.shuffle(cpse_rows)
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["cpse", "material_code", "description", "uom",
                                              "category_hint", "hsn_code", "last_rate_inr",
                                              "true_material_id"])
            w.writeheader()
            w.writerows(cpse_rows)
        print(f"{cpse:>5}: {len(cpse_rows):4d} materials -> {out.name}")

    uniq = {r["true_material_id"] for r in rows}
    print(f"\nTotal rows: {len(rows)} | unique real materials (incl. traps): {len(uniq)}")


if __name__ == "__main__":
    main()
