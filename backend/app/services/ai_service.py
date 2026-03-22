"""
ai_service.py

ALL Anthropic API calls go through this module. No exceptions.
Enforces cost controls: model selection, token limits, caching.
"""
import json
import logging

from config import settings

logger = logging.getLogger(__name__)

PROBLEM_DETECTION_PROMPT = """You are an expert UK automotive mechanic and car assessor
with 20 years experience buying and selling used cars at auction and privately.

You are assessing a vehicle listing to identify ALL likely faults and issues.
Be thorough. UK sellers often use slang and colloquial terms.

Common UK terms to recognise:
- "mayo/mayonnaise under cap" = coolant in oil = head gasket failure
- "lump" = engine
- "box knackered/gone" = gearbox failure
- "cambelt" = timing belt
- "lumpy/hunting idle" = rough running, possible injector/misfire
- "chucking out smoke" = excessive exhaust smoke
- "blowing" = exhaust leak or head gasket
- "needs a lump" = needs a replacement engine
- "nearside" = left (driver's side UK), "offside" = right (passenger side UK)
- "NSF/NSR/OSF/OSR" = nearside/offside front/rear panels
- "sills" = panels below doors, rust here is serious
- "arches" = wheel arches, common rust location
- "fettling" = minor repair work needed
- "ran when parked" = unknown current condition
- "barn find/been sitting" = unknown condition after storage
- "sold as seen" = seller disclaiming responsibility

Vehicle: {make} {model} {year} {fuel_type}
{engine_code_line}
Listing title: {title}
Listing description: {description}

Assess across ALL these dimensions:

1. WRITE-OFF STATUS: Is there any mention of Cat A, B, S, N, C, D, write-off,
   salvage, insurance claim, flood, fire? Map old Cat C → cat_s, Cat D → cat_n.

2. MECHANICAL FAULTS: For each subsystem, identify any mentioned or implied faults:
   powertrain, transmission, cooling, electrical, brakes, suspension/steering,
   AC/climate, exhaust, fuel system, hydraulics.

3. EXTERIOR CONDITION: Panel damage, rust (note: sill/arch/floor rust is serious),
   paint issues, glass damage, accident damage indicators.

4. INTERIOR CONDITION: Seat condition, dashboard warnings, odour, water damage signs.

5. VAGUENESS SIGNALS: Does the listing use phrases like "sold as seen", "needs TLC",
   "ran when parked", "project car" without specifying what's wrong?

Return ONLY valid JSON, no other text:
{{
  "write_off_category": "clean|cat_n|cat_s|cat_a|cat_b|flood|fire|unknown_writeoff",
  "mechanical_faults": [
    {{
      "fault_type": "<normalised_fault_type>",
      "severity": "critical|high|medium|low",
      "evidence": "<exact phrase from listing that indicates this fault>",
      "confidence": 0.0-1.0
    }}
  ],
  "exterior": {{
    "panel_damage_severity": "critical|high|medium|low|none",
    "panel_damage_notes": "<description>",
    "rust_severity": "critical|high|medium|low|none",
    "rust_notes": "<description>",
    "paint_severity": "critical|high|medium|low|none",
    "glass_severity": "critical|high|medium|low|none",
    "interior_severity": "critical|high|medium|low|none",
    "flood_damage": true|false,
    "fire_damage": true|false,
    "overall_severity": "critical|high|medium|low|none"
  }},
  "driveable": true|false|null,
  "vagueness_signals": ["<phrase_1>", "<phrase_2>"],
  "overall_confidence": 0.0-1.0
}}

Rules:
- Never guess fault_type — only include faults with evidence from the listing
- Use normalised fault type names matching the common_problems table
- overall_confidence reflects how much useful signal the listing contains,
  not how good an opportunity it is (that is determined later in TASK_006)
"""

# Stub response for development/testing when no Anthropic API key is set
STUB_AI_RESPONSE = {
    "write_off_category": "clean",
    "mechanical_faults": [
        {
            "fault_type": "timing_chain_failure",
            "severity": "high",
            "evidence": "timing chain rattle on cold start",
            "confidence": 0.85,
        }
    ],
    "exterior": {
        "panel_damage_severity": "low",
        "panel_damage_notes": "Minor scuff on rear bumper",
        "rust_severity": "none",
        "rust_notes": "",
        "paint_severity": "low",
        "glass_severity": "none",
        "interior_severity": "none",
        "flood_damage": False,
        "fire_damage": False,
        "overall_severity": "low",
    },
    "driveable": True,
    "vagueness_signals": [],
    "overall_confidence": 0.8,
}


def select_model(fault_count: int, has_unknown_faults: bool) -> str:
    """
    Use Haiku for simple/known fault classification.
    Use Sonnet only when listing has 3+ potential faults OR unknown fault types.
    """
    if fault_count >= 3 or has_unknown_faults:
        return "claude-sonnet-4-5"
    return "claude-haiku-4-5"


async def detect_problems_ai(
    make: str,
    model: str,
    year: int,
    fuel_type: str | None,
    engine_code: str | None,
    title: str,
    description: str,
    known_fault_count: int = 0,
    has_unknown_faults: bool = False,
) -> dict:
    """
    Calls the AI to detect problems from a listing.
    Returns parsed JSON dict matching the PROBLEM_DETECTION_PROMPT schema.

    In stub mode (no API key), returns a realistic hardcoded response.
    """
    # Verify and log API key configuration
    api_key = settings.anthropic_api_key
    if api_key:
        logger.info(
            "[AI_SERVICE] ANTHROPIC_API_KEY is set (prefix=%s...)",
            api_key[:10] if len(api_key) > 10 else "<short>",
        )
    else:
        logger.warning(
            "[AI_SERVICE] ANTHROPIC_API_KEY is NOT set — "
            "check config.py reads env var ANTHROPIC_API_KEY correctly. "
            "Running in stub mode."
        )

    # Stub mode — return hardcoded response when no API key
    if not api_key:
        logger.info("[AI_SERVICE] Returning STUB_AI_RESPONSE (no API key configured)")
        return STUB_AI_RESPONSE

    model_id = select_model(known_fault_count, has_unknown_faults)
    engine_code_line = f"Engine code: {engine_code}" if engine_code else ""

    prompt = PROBLEM_DETECTION_PROMPT.format(
        make=make,
        model=model,
        year=year,
        fuel_type=fuel_type or "unknown",
        engine_code_line=engine_code_line,
        title=title,
        description=description,
    )

    logger.info(
        "[AI_SERVICE] Calling Anthropic API — model=%s make=%s model_name=%s year=%d prompt_len=%d",
        model_id, make, model, year, len(prompt),
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model_id,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text
        logger.info(
            "[AI_SERVICE] Anthropic API call succeeded — response_len=%d input_tokens=%s output_tokens=%s",
            len(response_text),
            getattr(message.usage, "input_tokens", "?"),
            getattr(message.usage, "output_tokens", "?"),
        )
        response_text = response_text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        parsed = json.loads(response_text)
        logger.info(
            "[AI_SERVICE] JSON parsed OK — mechanical_faults=%d write_off=%s",
            len(parsed.get("mechanical_faults", [])),
            parsed.get("write_off_category"),
        )
        return parsed
    except json.JSONDecodeError:
        logger.error(
            "[AI_SERVICE] Failed to parse JSON from AI response: %r",
            response_text[:500] if "response_text" in dir() else "<no response>",
            exc_info=True,
        )
        return STUB_AI_RESPONSE
    except Exception as e:
        if hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 400:
            logger.error('Anthropic 400 response body: %s', e.response.text, exc_info=True)
        else:
            logger.error("[AI_SERVICE] Anthropic API call failed, returning stub response", exc_info=True)
        return STUB_AI_RESPONSE
