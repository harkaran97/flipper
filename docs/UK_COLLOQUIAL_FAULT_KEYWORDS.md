# Flipper — UK Colloquial Fault Keyword Reference

**Purpose:** This document defines the expanded keyword sets for each fault type
in Dimension 3 (Mechanical Condition) of the Vehicle Assessment Matrix.

Keywords are drawn from real UK eBay Motors, Gumtree, AutoTrader, PistonHeads,
and car forum listings. They include technical terms, mechanic jargon, seller
slang, and colloquial UK phrases used in real ads.

This file is the canonical reference for:
1. The `common_faults` DB seed data
2. The AI problem detection prompt keyword context
3. The ingestion worker pre-filter keyword list

---

## HOW TO READ THIS

Each fault entry contains:
- **Formal name** — how it's stored in the DB
- **What it means** — plain English for the AI prompt
- **Severity** — low / medium / high / critical
- **UK keywords & phrases** — the actual words found in listings
- **Colloquial tells** — what sellers write when they don't know the technical term

---

## 3A. POWERTRAIN

---

### Engine Failure / Seized
**Severity:** Critical
**Formal name:** `engine_failure`

**Keywords (technical):**
`seized`, `seized engine`, `locked up`, `no compression`, `spun bearing`,
`thrown a rod`, `rod knock`, `crank gone`, `big end gone`, `bottom end gone`,
`engine gone`, `motor gone`, `blown engine`, `engine failure`

**Colloquial UK tells (real listing language):**
- "big end gone" — UK classic, means crank bearing failure
- "engine's had it"
- "bottom end noise"
- "knocking from the bottom"
- "rod through the block" / "rod through the side"
- "won't turn over by hand"
- "locked solid"
- "the motor's knackered"
- "engine seized solid"
- "spun a bearing"
- "needs a new lump" — lump = engine in UK slang
- "needs a recon engine" — recon = reconditioned
- "bare shell" — car sold with no engine
- "engine removed"
- "stripped engine included"

---

### Timing Chain / Belt Failure
**Severity:** Critical
**Formal name:** `timing_chain_failure`

**Keywords (technical):**
`timing chain`, `timing belt`, `cambelt`, `jumped timing`, `timing out`,
`stretched chain`, `timing rattle`, `tensioner failure`, `guides worn`,
`chain slap`

**Colloquial UK tells:**
- "cambelt snapped" — cambelt is the UK term for timing belt
- "cambelt gone" / "belt gone"
- "rattles on cold start" — classic timing chain wear indicator
- "rattle at startup"
- "morning rattle"
- "timing's out"
- "jumped a tooth"
- "chain's gone"
- "needs a cambelt kit"
- "cambelt overdue" — massive red flag if mileage is high
- "known cambelt issue" — seller admitting a known fault
- "N47 timing issue" — BMW N47 diesel, notorious known fault
- "chain stretch"
- "tensioner noisy"

---

### Head Gasket Failure
**Severity:** High
**Formal name:** `head_gasket_failure`

**Keywords (technical):**
`head gasket`, `HG`, `HGF`, `blown head gasket`, `overheating`, `white smoke`,
`coolant in oil`, `oil in coolant`, `mixing fluids`, `compression leak`

**Colloquial UK tells:**
- "mayo under the cap" — mayonnaise = oil/water mixing, classic HGF sign
- "mayonnaise on the dipstick"
- "milky oil"
- "white smoke from exhaust"
- "chucking out white smoke"
- "steam from exhaust"
- "blowing white"
- "running hot" / "runs hot"
- "overheating"
- "temp gauge creeping up"
- "losing water but no visible leak"
- "needs a head" — shorthand for head gasket or cylinder head
- "HGF" — abbreviation commonly used on UK forums and listings
- "head's gone"
- "coolant disappearing"
- "bubbling in the reservoir"
- "gurgling from the heater"

---

### Turbo Failure
**Severity:** High
**Formal name:** `turbo_failure`

**Keywords (technical):**
`turbo`, `turbocharger`, `wastegate`, `turbo failure`, `boost leak`,
`no boost`, `over-boost`, `turbo shaft`, `oil-fed turbo`, `variable vane`

**Colloquial UK tells:**
- "turbo's gone"
- "no power" — vague but common with turbo failure
- "boost gone"
- "in limp mode" / "limp home mode" — ECU protecting engine after turbo fault
- "blowing blue smoke"
- "smoking under load"
- "chucking out smoke on boost"
- "whistling noise"
- "screeching turbo"
- "turbo surging"
- "turbo lag really bad"
- "oil in the intercooler" — sign of turbo seal failure
- "oily intake"
- "turbo needs replacing"
- "actuator stuck"
- "VNT fault" — variable nozzle turbo, common on VAG diesels

---

### Injector Failure
**Severity:** Medium
**Formal name:** `injector_failure`

**Keywords (technical):**
`injector`, `fuel injector`, `injector seal`, `injector leak`, `diesel injector`,
`injector coding`, `injector return pipe`

**Colloquial UK tells:**
- "rough idle"
- "lumpy idle" — very common UK phrase for rough engine running
- "hunting idle"
- "misfiring"
- "misfire on startup"
- "missing on one cylinder"
- "stuttering"
- "juddering"
- "shaking at idle"
- "diesel knock" — can indicate injector timing issue
- "clattering diesel"
- "blowing black smoke" — rich mixture from failed injector
- "smell of diesel inside"
- "fuel leak from top of engine"
- "damp injectors"
- "leaking injector seals"

---

### EGR Valve
**Severity:** Low-Medium
**Formal name:** `egr_fault`

**Keywords (technical):**
`EGR`, `EGR valve`, `exhaust gas recirculation`, `EGR blocked`, `EGR delete`

**Colloquial UK tells:**
- "in limp mode"
- "won't rev past 3000"
- "black smoke"
- "loss of power on motorway"
- "EGR light on"
- "engine management light on" / "EML on"
- "needs an EGR clean"
- "EGR deleted" — sometimes seller's done this as a fix
- "coked up intake"
- "sticky throttle"

---

### DPF (Diesel Particulate Filter)
**Severity:** Low-Medium
**Formal name:** `dpf_fault`

**Keywords (technical):**
`DPF`, `diesel particulate filter`, `DPF blocked`, `DPF regen`, `DPF regeneration`,
`DPF warning`, `DPF removed`, `DPF delete`

**Colloquial UK tells:**
- "DPF light on"
- "clogged DPF"
- "DPF gone into regen"
- "keeps going into limp mode"
- "needs a DPF clean"
- "DPF removed" — seller may have already deleted it
- "failed emissions"
- "smells of soot"
- "excessive smoke on start"

---

### Dual Mass Flywheel (DMF)
**Severity:** Medium-High
**Formal name:** `dmf_failure`

**Keywords (technical):**
`DMF`, `dual mass flywheel`, `flywheel`, `single mass conversion`

**Colloquial UK tells:**
- "juddering on pull away"
- "shuddering when setting off"
- "vibration when pulling away"
- "clutch judder" — often confused with DMF
- "rattling on idle"
- "transmission rattle"
- "clunky gearchange"
- "feel the vibration through the floor"

---

### Fuel Pump Failure
**Severity:** Medium
**Formal name:** `fuel_pump_failure`

**Keywords (technical):**
`fuel pump`, `HPFP`, `high pressure fuel pump`, `lift pump`, `fuel delivery`

**Colloquial UK tells:**
- "cuts out at speed"
- "dies on motorway"
- "splutters then cuts out"
- "hard to start when warm"
- "cranks but won't fire"
- "takes ages to start"
- "fuel starvation"
- "losing prime"

---

## 3B. TRANSMISSION

---

### Gearbox Failure
**Severity:** Critical
**Formal name:** `gearbox_failure`

**Keywords (technical):**
`gearbox`, `transmission`, `gearbox failure`, `synchromesh`, `gear selector`,
`gear linkage`, `transfer box`

**Colloquial UK tells:**
- "box is knackered" / "gearbox knackered"
- "box is gone"
- "won't select gears"
- "grinds going into gear"
- "crunches on 2nd" — synchromesh wear
- "won't go into reverse"
- "jumps out of gear"
- "pops out of 3rd"
- "baulking on gear changes"
- "clunks when changing"
- "gearbox oil leak"
- "rattling in neutral"
- "noisy box"
- "box needs a rebuild"

---

### Clutch Worn / Failed
**Severity:** Medium
**Formal name:** `clutch_failure`

**Keywords (technical):**
`clutch`, `clutch slip`, `clutch failure`, `clutch kit`, `pressure plate`,
`thrust bearing`, `release bearing`

**Colloquial UK tells:**
- "clutch slipping"
- "slipping in high gear"
- "biting point at the top"
- "biting point very high"
- "biting point near the floor" — different issue, spring failure
- "clutch gone"
- "clutch judder" — often worn friction plate
- "smell of clutch"
- "clutch dragging"
- "stiff clutch pedal"
- "heavy clutch"
- "squealing when pressing clutch"
- "throwout bearing noise"
- "release bearing"

---

### Automatic Gearbox Issues
**Severity:** High
**Formal name:** `auto_gearbox_fault`

**Keywords (technical):**
`automatic gearbox`, `auto box`, `DSG`, `CVT`, `torque converter`,
`gearbox control module`, `TCM`, `transmission fluid`

**Colloquial UK tells:**
- "auto box slipping"
- "jerky auto"
- "harsh gearchanges"
- "shuddering auto"
- "bangs into gear"
- "clunks when selecting drive"
- "won't come out of limp mode"
- "stuck in 3rd" — limp mode symptom
- "DSG judder" — notorious on early VW 7-speed dry clutch DSG
- "DSG shudder"
- "auto box hunting"
- "won't kick down"
- "revs but doesn't go"
- "slipping between gears"

---

### CV Joint / Driveshaft
**Severity:** Low-Medium
**Formal name:** `cv_joint_failure`

**Keywords (technical):**
`CV joint`, `constant velocity joint`, `driveshaft`, `CV boot`, `gaiter`,
`inner CV`, `outer CV`

**Colloquial UK tells:**
- "clicking on full lock"
- "clicking when turning"
- "clunking driveshaft"
- "split CV boot"
- "grease everywhere" — split gaiter
- "clicking front end"
- "clonking on turns"

---

## 3C. COOLING SYSTEM

---

### Overheating
**Severity:** High
**Formal name:** `overheating`

**Keywords (technical):**
`overheating`, `overheat`, `coolant loss`, `temperature warning`

**Colloquial UK tells:**
- "runs hot"
- "temp gauge goes up"
- "red temperature light"
- "steam coming from bonnet"
- "boils over"
- "losing water"
- "needs to be watched"
- "temp creeps up on motorway"

---

### Coolant Leak
**Severity:** Medium
**Formal name:** `coolant_leak`

**Keywords (technical):**
`coolant leak`, `antifreeze leak`, `coolant hose`, `jubilee clip`, `radiator hose`

**Colloquial UK tells:**
- "losing water" / "losing coolant"
- "pink puddle under the car"
- "sweet smell"
- "green puddle" — older antifreeze
- "weeping from the rad"
- "dripping from below"
- "low coolant light keeps coming on"
- "topped up regularly"

---

### Water Pump
**Severity:** Medium
**Formal name:** `water_pump_failure`

**Keywords (technical):**
`water pump`, `impeller`, `coolant pump`

**Colloquial UK tells:**
- "weeping water pump"
- "dripping from the pump"
- "noisy water pump"
- "bearing noise from front of engine"
- "coolant loss from front of engine"

---

## 3D. ELECTRICAL SYSTEMS

---

### ECU / Engine Management Failure
**Severity:** High
**Formal name:** `ecu_failure`

**Keywords (technical):**
`ECU`, `ECM`, `engine management unit`, `BCM`, `body control module`,
`immobiliser fault`, `IMMO`

**Colloquial UK tells:**
- "engine management light on" / "EML on"
- "engine warning light on"
- "won't start, no fault found"
- "immobiliser on"
- "IMMO light flashing"
- "key not recognised"
- "transponder fault"
- "needs ECU remap"
- "ECU fault codes"
- "won't communicate with diagnostics"
- "starts then cuts out immediately"

---

### Wiring / Electrical Faults
**Severity:** High (if widespread), Low (if isolated)
**Formal name:** `wiring_fault`

**Keywords (technical):**
`wiring loom`, `wiring fault`, `short circuit`, `earth fault`, `corroded terminals`

**Colloquial UK tells:**
- "electrical gremlin"
- "random electrical faults"
- "intermittent fault"
- "keeps blowing fuses"
- "all sorts of warning lights"
- "dash lights up like a Christmas tree"
- "multiple warning lights"
- "rodent damage" / "mice got at the wiring"
- "rats chewed the loom"
- "burnt wiring smell"
- "previous fire"

---

### Battery / Alternator
**Severity:** Low
**Formal name:** `battery_alternator_fault`

**Colloquial UK tells:**
- "flat battery"
- "won't hold a charge"
- "battery light on"
- "keeps going flat"
- "needs jump start"
- "alternator warning light"
- "charging system fault"
- "needs a new battery"

---

### ABS System
**Severity:** Medium
**Formal name:** `abs_fault`

**Colloquial UK tells:**
- "ABS light on"
- "ABS fault"
- "ABS sensor"
- "wheel speed sensor"
- "brakes feel odd"
- "ABS kicks in at low speed" — sign of faulty sensor

---

### Airbag / SRS
**Severity:** Medium
**Formal name:** `airbag_fault`

**Colloquial UK tells:**
- "airbag light on"
- "SRS light on"
- "airbag deployed" — serious, needs full replacement
- "clock spring fault"
- "steering wheel airbag replaced"
- "curtain airbag gone off"

---

## 3E. BRAKES

---

### Brake Discs / Pads Worn
**Severity:** Low-Medium
**Formal name:** `brakes_worn`

**Colloquial UK tells:**
- "brakes need doing"
- "grinding brakes"
- "squealing brakes"
- "scored discs"
- "low pads"
- "metal to metal"
- "brakes down to the metal"
- "worn through"
- "discs lipped" — lipped = worn edge lip on disc

---

### Brake Caliper Seized
**Severity:** Medium
**Formal name:** `caliper_seized`

**Colloquial UK tells:**
- "binding brakes"
- "pulling to one side"
- "hot wheel after driving"
- "one wheel heating up"
- "seized rear caliper" — very common on older UK cars
- "handbrake cable stuck"

---

### Electric Parking Brake
**Severity:** Low-Medium
**Formal name:** `epb_fault`

**Colloquial UK tells:**
- "EPB fault"
- "electric handbrake fault"
- "parking brake warning light"
- "won't release"
- "stuck on"

---

## 3F. SUSPENSION & STEERING

---

### Shock Absorbers / Springs
**Severity:** Medium
**Formal name:** `suspension_failure`

**Colloquial UK tells:**
- "bouncy suspension"
- "wallowing"
- "bottoming out"
- "corner sitting low"
- "one corner down"
- "knocking from suspension"
- "clonking over bumps"
- "broken spring"
- "coilover seized"
- "strut top bearing gone"
- "top mount worn"

---

### Wishbone / Control Arm
**Severity:** Medium
**Formal name:** `wishbone_failure`

**Colloquial UK tells:**
- "knocking front end"
- "clunking over bumps"
- "wishbone bush worn"
- "ball joint worn"
- "needs front end work"
- "clonking nearside front"
- "offside front knocking"
- nearside = driver's side UK, offside = passenger's side UK

---

### Wheel Bearing
**Severity:** Low-Medium
**Formal name:** `wheel_bearing_failure`

**Colloquial UK tells:**
- "humming noise"
- "wheel bearing noise"
- "droning at speed"
- "humming from nearside rear"
- "rumbling wheel"
- "changes with steering input" — classic bearing test

---

### Power Steering
**Severity:** Medium
**Formal name:** `power_steering_fault`

**Colloquial UK tells:**
- "heavy steering"
- "stiff steering"
- "no power assistance"
- "PAS light on" — Power Assisted Steering
- "EPS fault" — Electric Power Steering
- "EPAS fault"
- "power steering leak"
- "groaning on full lock"
- "steering fluid low"
- "jerky steering"

---

### Air Suspension
**Severity:** High
**Formal name:** `air_suspension_fault`

**Colloquial UK tells:**
- "air suspension warning"
- "corner down"
- "sitting low at rear"
- "compressor fault"
- "air bag gone"
- "suspension fault light"
- "self-levelling not working"
- "drops overnight"
- "sags on one corner"
- Common on: Range Rover, BMW 7 Series, Mercedes S-Class, Audi A8

---

## 3G. AIR CONDITIONING & CLIMATE

---

### AC Not Working
**Severity:** Low-Medium
**Formal name:** `ac_fault`

**Colloquial UK tells:**
- "AC not cold"
- "air con not working"
- "aircon not cold"
- "AC gassed up but still not cold"
- "needs regassing"
- "AC light flashing"
- "compressor cutting in and out"
- "no cold air"
- "AC blows warm"

---

### Heater Matrix
**Severity:** Medium
**Formal name:** `heater_matrix_fault`

**Colloquial UK tells:**
- "no heat"
- "heater not working"
- "heater matrix gone"
- "sweet smell inside"
- "windows fog up inside"
- "damp carpets" — classic heater matrix leak
- "wet passenger footwell"
- "coolant smell inside"
- "no demist"

---

## 3H. EXHAUST SYSTEM

---

### Catalytic Converter
**Severity:** Medium
**Formal name:** `cat_fault`

**Colloquial UK tells:**
- "rattling exhaust"
- "cat rattle"
- "cat light on"
- "failed emissions"
- "P0420 code"
- "cat gone"
- "cat stolen" — increasingly common, especially Toyota Prius, Honda Jazz

---

### Exhaust Leak / Blowing
**Severity:** Low
**Formal name:** `exhaust_leak`

**Colloquial UK tells:**
- "blowing exhaust"
- "blowing manifold"
- "exhaust blowing"
- "hole in the exhaust"
- "blowing at the downpipe"
- "loud exhaust"
- "manifold gasket blowing"
- "ticking on startup" — can indicate manifold blow

---

## 3I. BODYWORK — UK COLLOQUIAL

---

### Rust
**Severity:** Low (surface) to Critical (structural/chassis)
**Formal name:** `rust`

**Colloquial UK tells:**
- "bit of surface rust"
- "tidy underneath" — seller claiming no structural rust
- "rusty arches" / "wheel arch rust"
- "sill rust" / "rusty sills"
- "floor rust" / "rusty floor"
- "chassis rust" — serious
- "subframe rust"
- "rear beam rusty"
- "needs a bit of tidying"
- "patchy"
- "bubbling" — paint bubbling over rust
- "starting to go"
- "needs the arches doing"
- "jacking point gone" — structural rust, serious
- "rotten sills"

---

### Accident Damage / Bodywork
**Severity:** Low (minor) to High (structural)
**Formal name:** `accident_damage`

**Colloquial UK tells:**
- "needs a respray"
- "had a bump"
- "parking dent"
- "scuff on the bumper"
- "cat N" / "cat s" / "previously written off"
- "light damage to nearside"
- "minor damage to front"
- "crumple zone damage"
- "bonnet doesn't sit right" — sign of prior front end collision
- "door gap uneven" — sign of structural damage or poor repair
- "filler on the door" — bodywork filler hiding dents
- "previous repair visible"
- "been repainted" — potential accident history
- "non-standard colour" — respray

---

### Flood Damage
**Severity:** Critical
**Formal name:** `flood_damage`

**Colloquial UK tells:**
- "flood damaged"
- "water ingress"
- "damp carpets"
- "wet interior"
- "musty smell"
- "tidemark inside"
- "electrics playing up after getting wet"
- "recovered from flood"
- "submerged"

---

## 3J. SELLER VAGUENESS / UNCERTAINTY SIGNALS

These phrases indicate the seller doesn't know what's wrong — trigger
"worth a look" bucket if price is low enough.

- "needs some TLC"
- "bit of a project"
- "needs attention"
- "sold as seen"
- "as is"
- "not sure what's wrong"
- "ran when parked"
- "stood for a while"
- "been sitting"
- "been off the road a year"
- "not used recently"
- "barn find"
- "been in storage"
- "project car"
- "ideal for someone mechanically minded"
- "for the mechanically inclined"
- "needs work"
- "needs fettling" — fettling = tinkering / fixing
- "needs finishing"
- "part finished restoration"
- "someone else's project"
- "tidy apart from a couple of things"
- "drives but..."

---

## 3K. UK LOCATION TERMS FOR BODY PANELS

These appear in listings when describing damage location.
Our AI needs to understand them.

| UK Term | Meaning |
|---|---|
| Nearside (NS) | Left side of car (driver's side in UK) |
| Offside (OS) | Right side of car (passenger side in UK) |
| NSF | Nearside Front |
| NSR | Nearside Rear |
| OSF | Offside Front |
| OSR | Offside Rear |
| O/S | Offside |
| N/S | Nearside |
| Sill | The panel beneath the doors, between front and rear arches |
| Arch | Wheel arch |
| Scuttle | Panel between bonnet and windscreen |
| A-pillar, B-pillar, C-pillar | Roof support pillars front to back |
| Boot | Trunk |
| Bonnet | Hood |
| Wing | Fender |

---

*Last updated: March 2026*
*This document should be reviewed and expanded as new listing patterns are observed.*
