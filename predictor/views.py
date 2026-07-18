"""
Four AI persona "View" functions that each analyse a feature row
and return a natural-language argument for or against imminent failure.
"""

from typing import Optional

from .api import ApiCallResult, call_chat_completion
from .config import Config, FIREWORKS_BASE_URL


def _features_text(row: dict) -> str:
    """Build the feature-description text sent to every view."""
    spectral = row.get("spectral_features", "[]")
    # If spectral_features is a JSON string, pretty-print it concisely
    import json as _json
    try:
        parsed = _json.loads(spectral) if isinstance(spectral, str) else spectral
        if isinstance(parsed, list) and len(parsed) > 8:
            spectral_fmt = (
                f"[{', '.join(f'{v:.4f}' for v in parsed[:4])}, "
                f"..., {', '.join(f'{v:.4f}' for v in parsed[-2:])}]"
            )
        else:
            spectral_fmt = str(parsed)
    except (ValueError, TypeError):
        spectral_fmt = str(spectral)

    return (
        f"Asset ID: {row.get('asset_id', 'N/A')}\n"
        f"Timestamp: {row.get('timestamp', 'N/A')}\n"
        f"RMS (Root Mean Square): {row.get('rms', 'N/A')}\n"
        f"Kurtosis: {row.get('kurtosis', 'N/A')}\n"
        f"Spectral Features (first 4 … last 2): {spectral_fmt}\n"
    )


def call_signal_analyst(
    row: dict, cfg: Config
) -> ApiCallResult:
    """
    The Signal Analyst examines raw numeric patterns in the sensor data
    and argues for or against imminent failure based purely on the numbers.
    """
    system_prompt = (
        "You are a Signal Analyst specialising in vibration and sensor-data analysis. "
        "Given the extracted sensor features below, evaluate whether the equipment shows "
        "a pattern consistent with imminent failure. "
        "Focus ONLY on the numerical evidence: RMS amplitude, kurtosis (peakedness of the "
        "distribution), and the spectral feature profile.\n\n"
        "Guidelines:\n"
        "- High RMS + high kurtosis (>3.5) often indicates early-stage bearing defects.\n"
        "- Spectral energy concentrated in high-frequency bands suggests developing faults.\n"
        "- If values are within normal operating ranges, say so.\n\n"
        "Provide a concise analysis (3–5 sentences). Conclude with either "
        "'ARGUMENT FOR FAILURE' or 'ARGUMENT AGAINST FAILURE'."
    )
    user_prompt = f"Here are the sensor readings:\n\n{_features_text(row)}\n\nAnalyse these readings and give your conclusion."

    return call_chat_completion(
        endpoint_url=FIREWORKS_BASE_URL,
        api_key=cfg.fireworks_api_key,
        model=cfg.fireworks_view_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=1024,
        max_retries=cfg.max_retries,
        backoff_base=cfg.backoff_base,
        role_label="Signal Analyst",
    )


def call_domain_expert(
    row: dict, cfg: Config
) -> ApiCallResult:
    """
    The Domain Expert reasons from general knowledge of mechanical failure modes:
    bearing faults, imbalance, misalignment, lubrication issues, etc.
    """
    system_prompt = (
        "You are a Domain Expert in industrial rotating machinery with 20+ years of "
        "experience maintaining bearings, motors, pumps, and gearboxes. "
        "Given the sensor readings below, reason from your mechanical/domain expertise "
        "about whether the equipment is approaching failure.\n\n"
        "Consider:\n"
        "- Bearing failure modes (spalling, brinelling, contamination).\n"
        "- Operating context (sustained high loads, speed fluctuations).\n"
        "- Typical warning signs in vibration data for each failure mode.\n"
        "- Alternative explanations (e.g., normal load variation, temperature effects).\n\n"
        "Provide a concise domain-grounded analysis (3–5 sentences). Conclude with "
        "'ARGUMENT FOR FAILURE' or 'ARGUMENT AGAINST FAILURE'."
    )
    user_prompt = f"Here are the sensor readings:\n\n{_features_text(row)}\n\nWhat does your mechanical expertise say about this equipment?"

    return call_chat_completion(
        endpoint_url=FIREWORKS_BASE_URL,
        api_key=cfg.fireworks_api_key,
        model=cfg.fireworks_view_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=1024,
        max_retries=cfg.max_retries,
        backoff_base=cfg.backoff_base,
        role_label="Domain Expert",
    )


def call_risk_assessor(
    row: dict, cfg: Config
) -> ApiCallResult:
    """
    The Risk Assessor reasons about cost, safety, and urgency if the failure is real.
    """
    system_prompt = (
        "You are a Risk Assessor for an industrial plant. Your role is to evaluate the "
        "potential consequences if this equipment were to fail. "
        "Given the sensor readings below, assess:\n\n"
        "- What is the worst-case scenario if failure is imminent?\n"
        "- What is the cost of acting now vs. the cost of inaction?\n"
        "- Are there safety implications?\n"
        "- How urgent is this situation?\n\n"
        "Be pragmatic — not every abnormal reading warrants a shutdown. "
        "Provide a concise risk assessment (3–5 sentences). Conclude with "
        "'ARGUMENT FOR FAILURE' (high risk, act now) or 'ARGUMENT AGAINST FAILURE' "
        "(low risk, monitor)."
    )
    user_prompt = f"Here are the sensor readings:\n\n{_features_text(row)}\n\nAssess the risk level and urgency."

    return call_chat_completion(
        endpoint_url=FIREWORKS_BASE_URL,
        api_key=cfg.fireworks_api_key,
        model=cfg.fireworks_view_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=1024,
        max_retries=cfg.max_retries,
        backoff_base=cfg.backoff_base,
        role_label="Risk Assessor",
    )


def call_skeptic(
    row: dict, cfg: Config
) -> ApiCallResult:
    """
    The Skeptic actively argues AGAINST the failure hypothesis,
    looking for alternative explanations: sensor noise, normal wear, etc.
    """
    system_prompt = (
        "You are a Professional Skeptic with deep expertise in sensor reliability, "
        "data quality, and statistical false positives. Your JOB is to argue AGAINST "
        "the hypothesis of imminent equipment failure.\n\n"
        "Find every possible alternative explanation:\n"
        "- Could this be sensor noise or calibration drift?\n"
        "- Are the readings within normal operational variance?\n"
        "- Could environmental factors (temperature, humidity) explain the data?\n"
        "- Is this just normal wear that does NOT indicate imminent failure?\n"
        "- Are there known benign patterns that mimic failure signatures?\n\n"
        "You must provide a counterargument. Do NOT concede to the failure hypothesis. "
        "Provide a concise skeptical analysis (3–5 sentences). Conclude with "
        "'ARGUMENT AGAINST FAILURE'."
    )
    user_prompt = (
        f"Here are the sensor readings:\n\n{_features_text(row)}\n\n"
        f"Why is this NOT a sign of imminent failure? Provide alternative explanations."
    )

    return call_chat_completion(
        endpoint_url=FIREWORKS_BASE_URL,
        api_key=cfg.fireworks_api_key,
        model=cfg.fireworks_view_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=1024,
        max_retries=cfg.max_retries,
        backoff_base=cfg.backoff_base,
        role_label="Skeptic",
    )