"""
The Judge — receives all four view arguments and synthesises them
into a single calibrated prediction with structured JSON output.
"""

import json
import re
from typing import Optional

from .api import ApiCallResult, call_chat_completion
from .config import Config, FIREWORKS_BASE_URL


def _extract_json(text: str) -> Optional[dict]:
    """
    Try to pull valid JSON out of the model's response.
    Handles markdown code fences, leading/trailing text, and broken JSON.
    """
    # Step 1: Try parsing the entire string
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Step 2: Look for ```json ... ``` blocks
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Step 3: Look for { ... } at top level (greedy)
    brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass

    return None


_DEFAULT_JUDGE_OUTPUT = {
    "failure_probability": -1.0,
    "confidence": 0.0,
    "rationale": "[ERROR] Judge output could not be parsed.",
    "disagreement_flag": True,
}


def call_judge(
    view1_text: str,
    view2_text: str,
    view3_text: str,
    view4_text: str,
    cfg: Config,
) -> dict:
    """
    Send the four view arguments to the Judge model (Fireworks AI, stronger model).
    Returns a dict with keys: failure_probability, confidence, rationale, disagreement_flag.
    """
    system_prompt = (
        "You are a Senior Reliability Engineer acting as a Judge. "
        "You have received four expert analyses about whether a piece of industrial "
        "equipment is at risk of imminent failure. Your job is to weigh these arguments "
        "carefully and produce a single, calibrated prediction.\n\n"
        "Consider:\n"
        "- The strength and specificity of each argument.\n"
        "- How much the arguments agree or disagree with each other.\n"
        "- The credibility of each perspective for this type of data.\n"
        "- When there is strong disagreement, flag it.\n\n"
        "You MUST output ONLY valid JSON with no preamble, no explanation, and no "
        "markdown formatting. Use exactly this structure:\n\n"
        '{\n'
        '  "failure_probability": <float 0.0–1.0>,\n'
        '  "confidence": <float 0.0–1.0>,\n'
        '  "rationale": "<a concise, human-readable explanation of your reasoning>",\n'
        '  "disagreement_flag": <true or false>\n'
        '}\n\n'
        "Failure probability: 0.0 = no chance of failure, 1.0 = certain imminent failure. "
        "Confidence: how sure you are in your probability estimate. "
        "Disagreement flag: true if the four views significantly disagreed."
    )

    user_prompt = (
        "Here are the four expert analyses of the same sensor data:\n\n"
        f"--- [Signal Analyst] ---\n{view1_text}\n\n"
        f"--- [Domain Expert] ---\n{view2_text}\n\n"
        f"--- [Risk Assessor] ---\n{view3_text}\n\n"
        f"--- [Skeptic] ---\n{view4_text}\n\n"
        "What is your final calibrated prediction? Output ONLY valid JSON."
    )

    result = call_chat_completion(
        endpoint_url=FIREWORKS_BASE_URL,
        api_key=cfg.fireworks_api_key,
        model=cfg.fireworks_judge_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,  # lower temperature for more deterministic/calibrated output
        max_tokens=1024,
        max_retries=cfg.max_retries,
        backoff_base=cfg.backoff_base,
        role_label="Judge",
    )

    # Parse the JSON from the response
    parsed = _extract_json(result.text)
    if parsed is None:
        print(f"  [Judge] WARNING — could not parse JSON from response. "
              f"Raw text preview: {result.text[:200]}…")
        # Retry once with an even stronger instruction
        retry_prompt = (
            f"Your previous response was not valid JSON. Please output ONLY valid JSON "
            f"with no other text. Use this exact structure:\n\n"
            f'{{\n  "failure_probability": 0.0–1.0,\n  "confidence": 0.0–1.0,\n'
            f'  "rationale": "string",\n  "disagreement_flag": true/false\n}}\n\n'
            f"Here are the analyses again:\n\n{user_prompt}"
        )
        retry_result = call_chat_completion(
            endpoint_url=FIREWORKS_BASE_URL,
            api_key=cfg.fireworks_api_key,
            model=cfg.fireworks_judge_model,
            messages=[{"role": "user", "content": retry_prompt}],
            temperature=0.2,
            max_tokens=1024,
            max_retries=1,
            backoff_base=2.0,
            role_label="Judge (retry)",
        )
        parsed = _extract_json(retry_result.text)
        if parsed is None:
            print(f"  [Judge] CRITICAL — retry also failed. Using sentinel values.")
            return dict(_DEFAULT_JUDGE_OUTPUT)

    # Validate required keys
    expected_keys = {"failure_probability", "confidence", "rationale", "disagreement_flag"}
    missing_keys = expected_keys - set(parsed.keys())
    if missing_keys:
        print(f"  [Judge] WARNING — missing keys: {missing_keys}. Filling defaults.")
        for key in missing_keys:
            parsed[key] = _DEFAULT_JUDGE_OUTPUT.get(key)

    # Type-check / clamp values
    try:
        parsed["failure_probability"] = max(0.0, min(1.0, float(parsed["failure_probability"])))
    except (ValueError, TypeError):
        parsed["failure_probability"] = -1.0

    try:
        parsed["confidence"] = max(0.0, min(1.0, float(parsed["confidence"])))
    except (ValueError, TypeError):
        parsed["confidence"] = 0.0

    parsed["disagreement_flag"] = bool(parsed.get("disagreement_flag", False))
    parsed["rationale"] = str(parsed.get("rationale", ""))

    return parsed