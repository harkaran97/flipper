"""
Listing Pre-Filter

Two-tier gate applied before AI pipeline spend.
Matches listing title + description (combined, lowercased) against three keyword
lists using whole-word regex (\b boundaries) for every term.

Patterns are compiled once at module load — never per listing call.

Tier 1 — CAR_PARTS:   Listing mentions a specific car component.
Tier 2A — FAULT_SIGNALS: Listing mentions a fault, failure, or problem.
Tier 2B — OPPORTUNITY_SIGNALS: Listing shows motivated-seller or project-car signals.

Pass any tier → emit to AI pipeline.
Pass none → store with skip_reason='pre_filter_no_match', no AI spend.
"""

import re

# ---------------------------------------------------------------------------
# Tier 1 — CAR_PARTS (338 terms)
# ---------------------------------------------------------------------------

CAR_PARTS = [
    "abs", "ac", "actuator", "adblue", "aerial", "air bag",
    "air con", "air conditioning", "air filter", "airbag", "alloy", "alloys",
    "alternator", "antenna", "anti roll bar", "antifreeze", "arb", "arch",
    "armrest", "atf", "automatic gearbox", "aux belt", "auxiliary belt", "axle",
    "badge", "ball joint", "battery", "bcm", "belt pretensioner", "block",
    "bms", "bodywork", "bonnet", "boost pipe", "boot", "box",
    "brake", "brakes", "breather", "bump stop", "bumper", "bush",
    "bushes", "bushings", "caliper", "calliper", "cam", "cambelt",
    "camshaft", "carb", "carburettor", "carpet", "cat", "catalyst",
    "catalytic converter", "central locking", "centre cap", "centre console", "centre pipe", "chain",
    "charging port", "chassis", "chrome trim", "climate control", "clocks", "clutch",
    "compression", "compressor", "con rod", "connecting rod", "connector", "conrod",
    "control arm", "coolant", "corrosion", "crack", "crank", "crankcase",
    "crankshaft", "crossmember", "cv", "cvt", "cylinder", "damper",
    "dash", "dashboard", "daytime running light", "dc converter", "dcct", "decat",
    "def", "dent", "diesel", "diff", "differential", "diffuser",
    "disc", "discs", "dmf", "door", "doors", "downpipe",
    "dpf", "drive belt", "drive shaft", "driveshaft", "drl", "drop link",
    "dsg", "dual mass flywheel", "ecm", "ecu", "egr", "electric window",
    "emblem", "engine", "epb", "eps", "exchange", "exhaust",
    "filler cap", "flexi pipe", "flexplate", "floor", "flywheel", "fog lamp",
    "fog light", "fuel", "fuse", "fusebox", "gasket", "gear",
    "gearbox", "gears", "gearstick", "glass", "grab handle", "grille",
    "half shaft", "halfshaft", "handbrake", "handbrake lever", "harmonic balancer", "harness",
    "hazard", "head", "headlamp", "headlight", "headlights", "headliner",
    "headlining", "headrest", "heater", "high pressure pump", "high voltage", "hood",
    "horn", "hub", "hybrid system", "hydraulic fluid", "idler", "immo",
    "immobiliser", "indicator", "infotainment", "injector", "injectors", "inlet",
    "instrument cluster", "intake", "intercooler", "inverter", "key fob", "knuckle",
    "lacquer", "lambda", "lead acid", "led headlight", "lift pump", "lifter",
    "loom", "manifold", "mat", "mid pipe", "mild hybrid", "mirror",
    "motor", "moulding", "muffler", "navigation", "odometer", "oem",
    "oil", "onboard charger", "pad", "pads", "paint", "panel",
    "parking camera", "pattern part", "pdk", "pedal", "pedals", "petrol",
    "piston", "plenum", "pollen filter", "power steering", "pressure plate", "prop shaft",
    "propshaft", "puncture", "rack", "rack and pinion", "rad", "radiator",
    "radio", "rear light", "rear window", "rebuild", "recon", "reconditioned",
    "refrigerant", "regenerative", "relay", "release bearing", "resonator", "rev counter",
    "reversing camera", "rim", "rims", "rocker", "roof", "rot",
    "rotor", "rotors", "rubber", "rust", "sat nav", "scratch",
    "screen", "scuff", "seat", "seatbelt", "seats", "selector",
    "sensor", "serpentine belt", "service", "servo", "shift fork", "shift rod",
    "shock", "shocks", "side window", "sidewall", "silencer", "sill",
    "sills", "skirt", "spacesaver", "speedo", "speedometer", "splitter",
    "spoiler", "spring", "sprocket", "srs", "starter", "steering column",
    "steering rack", "stereo", "strut", "stud", "subframe", "sump",
    "sun visor", "sunroof", "supercharger", "suspension", "sway bar link", "swirl flap",
    "swirl flaps", "synchro", "synchromesh", "tacho", "tachometer", "tail light",
    "tank", "tappet", "tensioner", "thermostat", "throttle body", "thrust bearing",
    "tie rod", "timing", "tiptronic", "tire", "tires", "top mount",
    "torque converter", "tpms", "track rod", "track rod end", "trailing arm", "transfer case",
    "transmission", "transponder", "tread", "trim", "trunk", "turbo",
    "turbocharger", "turn signal", "tyre", "tyres", "undertray", "upright",
    "valve", "valves", "washer fluid", "washer pump", "wastegate", "water",
    "welding", "wheel", "wheels", "window regulator", "window seal", "window switch",
    "window trim", "windscreen", "windshield", "wing", "wiper", "wiring",
    "wishbone", "xenon",
]

# ---------------------------------------------------------------------------
# Tier 2A — FAULT_SIGNALS
# ---------------------------------------------------------------------------

FAULT_SIGNALS = [
    # Core problem words
    "fault", "faulty", "failed", "failure", "failing",
    "broken", "snapped", "cracked", "damaged", "worn", "worn out",
    "seized", "stuck", "jammed", "binding",
    "blown", "blowing",
    "leaking", "leak", "weeping", "seeping", "dripping",
    "burning", "burnt",
    "smoking", "smoke",
    "overheating", "overheat", "runs hot", "gets hot",
    "misfire", "misfiring",
    "knocking", "banging", "tapping", "rattling", "clunking",
    "grinding", "screeching", "squealing",
    "vibrating", "vibration", "shaking", "juddering",
    "hunting", "surging",
    "sluggish", "no power", "loss of power", "underpowered",
    "cutting out", "cuts out", "stalling", "stall",
    "hesitation", "flat spot",
    # Not running
    "non runner", "non-runner", "not running", "doesnt run", "doesn't run",
    "wont start", "won't start", "will not start", "not starting",
    "no start", "failed to start", "hard to start", "difficult to start",
    "turns over but", "cranks but", "cranks over",
    "starts then", "runs then", "starts but", "runs but",
    "intermittent start", "sometimes starts",
    # Needs work
    "needs work", "needs attention", "needs repair", "needs fixing",
    "needs tlc", "tlc", "could do with",
    "requires work", "requires attention", "requires repair",
    "issue", "problem", "concern", "trouble",
    # Condition indicators
    "repair", "bodge", "bodged",
    "as is", "sold as seen", "as seen", "no warranty",
    "spares", "for parts", "breaking for parts",
    # Write-off / accident
    "cat s", "cat n", "cat c", "cat d", "category s", "category n",
    "insurance write off", "written off", "write off", "salvage",
    "accident damage", "accident damaged",
    "fire damage", "flood damage", "hail damage", "impact damage",
    "structural damage",
    # Warning lights / diagnostics
    "warning light", "engine light", "check engine",
    "engine management light", "eml", "mil", "service light",
    "abs light", "airbag light", "srs light", "dpf light", "oil light",
    "temperature light", "battery light", "fault code", "error code",
    "dtc", "obd", "diagnostic",
    # Limp mode
    "limp mode", "limp home", "restricted performance", "reduced power",
    # Rust / rot
    "rusty", "rusting", "corroded", "rotten", "rotted",
    "welding needed", "needs welding", "patched", "filler", "overspray",
    # Fluid issues
    "oil leak", "coolant leak", "water leak", "fuel leak",
    "oil burning", "burning oil", "uses oil", "drinks oil",
    "mayo", "mayonnaise", "milky",
    "white smoke", "blue smoke", "black smoke",
    # UK slang for broken
    "knackered", "had it", "packed up", "given up", "gone bang",
    "blown up", "cooked", "done for", "clapped out",
    "buggered", "duff", "dud", "gubbed",
]

# ---------------------------------------------------------------------------
# Tier 2B — OPPORTUNITY_SIGNALS
# ---------------------------------------------------------------------------

OPPORTUNITY_SIGNALS = [
    # Motivated seller
    "quick sale", "quick sell", "needs to go", "must go", "must sell",
    "need gone", "needs gone", "moving abroad", "emigrating", "relocating",
    "no longer needed", "no room", "no space", "downsizing",
    "new car ordered", "bought new car", "no time", "too many projects",
    "too many cars", "lost interest", "divorce", "separation",
    "estate sale", "deceased", "probate", "house clearance",
    # Price signals
    "open to offers", "ono", "or nearest offer", "offers considered",
    "priced to sell", "price drop", "price reduced", "below book",
    "below trade", "trade price", "bargain", "snip",
    # Project / stored
    "project car", "barn find", "barn stored", "been in storage",
    "dry stored", "long term storage", "laid up", "off the road", "sorn",
    # Incomplete
    "rolling shell", "bare shell", "stripped", "no engine", "no gearbox",
    "spares included", "loads of spares",
    # Honesty signals
    "sold as seen", "no hidden problems", "no hidden issues", "full disclosure",
]

# ---------------------------------------------------------------------------
# Pre-compiled patterns — done once at module load, never per listing
# ---------------------------------------------------------------------------


def _compile(keywords: list[str]) -> list[re.Pattern]:
    """Pre-compile whole-word patterns for all keywords."""
    return [re.compile(r'\b' + re.escape(kw) + r'\b') for kw in keywords]


_CAR_PARTS_PATTERNS = _compile(CAR_PARTS)
_FAULT_PATTERNS = _compile(FAULT_SIGNALS)
_OPPORTUNITY_PATTERNS = _compile(OPPORTUNITY_SIGNALS)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def should_process_listing(title: str, description: str) -> bool:
    """
    Returns True if listing should enter the AI pipeline.

    Matches title + description combined, lowercased, whole-word only.
    Pass any tier → process. Pass none → store but skip.
    """
    text = f"{title} {description}".lower()
    return (
        _matches_any(text, _CAR_PARTS_PATTERNS)
        or _matches_any(text, _FAULT_PATTERNS)
        or _matches_any(text, _OPPORTUNITY_PATTERNS)
    )


def _matches_any(text: str, patterns: list[re.Pattern]) -> bool:
    return any(p.search(text) for p in patterns)
