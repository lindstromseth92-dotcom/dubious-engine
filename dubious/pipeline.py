import time

from .extract import extract
from .resolve import fetch
from .score import score_claim

# USD per 1M tokens (input, output). Check ai.google.dev/pricing before you quote these.
PRICE = {"gemini-3.8-flash": (0.75, 3.75)}


def run(source: str, model: str = "gemini-3.8-flash") -> dict:
    t0 = time.perf_counter()
    origin = source if source.startswith("http") else None
    text = fetch(source)[0] if origin else source
    claims, usage = extract(text, model)
    results = [score_claim(c, origin) for c in claims]
    p_in, p_out = PRICE[model]
    cost = (usage["in"] * p_in + usage["out"] * p_out) / 1e6
    return {
        "source": origin or "text",
        "claims": results,
        "meta": {
            "model": model,
            "tokens_in": usage["in"],
            "tokens_out": usage["out"],
            "cost_usd": round(cost, 6),
            "cost_per_claim_usd": round(cost / max(len(results), 1), 6),
            "latency_s": round(time.perf_counter() - t0, 2),
        },
    }