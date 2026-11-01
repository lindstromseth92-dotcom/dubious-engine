import datetime
import json
import re
from pathlib import Path

from .resolve import chain, domain

REG = json.loads((Path(__file__).parent.parent / "ontology" / "registry.json").read_text())
HEARSAY = re.compile(r"\b(sources?|officials?|experts?|people familiar|insiders?|critics)\b", re.IGNORECASE)


def tier_of(dom: str) -> str:
    for tier, doms in REG["tiers"].items():
        if any(dom == d or dom.endswith("." + d) for d in doms):
            return tier
    return "unknown"


def score_claim(claim, origin_url: str | None) -> dict:
    reasons: list[str] = []
    chains: list[list[str]] = []

    if not claim.cited_urls:
        if claim.attributed_to and HEARSAY.search(claim.attributed_to):
            reasons.append("HEARSAY")
            s = 0.75
        else:
            reasons.append("SRC-NONE")
            s = REG["tier_scores"]["none"]
    else:
        chains = [chain(u) for u in claim.cited_urls[:3]]
        tiers = [tier_of(c[0]) for c in chains]
        best = min(tiers, key=lambda t: REG["tier_scores"][t])
        s = REG["tier_scores"][best]
        reasons.append(f"SRC-TIER:{best}")
        if "disinfo" in tiers:
            reasons.append("SRC-DISINFO")
            s = max(s, REG["tier_scores"]["disinfo"])
        if origin_url and any(c[0] == domain(origin_url) for c in chains):
            reasons.append("CHAIN-CIRC")  # the page cites itself
            s = max(s, 0.6)
        if best in ("secondary", "tertiary", "commentary", "unknown"):
            terminal = {tier_of(d) for c in chains for d in c[1:]}
            if "primary" in terminal:
                reasons.append("CHAIN-TERM:primary")
                s -= 0.1
            else:
                reasons.append("CHAIN-TERM:none")
                s += 0.1

    year = datetime.date.today().year
    if claim.cites_data_year and claim.cites_data_year < year - REG["stale_years"]:
        reasons.append("DATA-STALE")
        s += 0.1

    s = round(min(max(s, 0.0), 1.0), 2)
    if "SRC-DISINFO" in reasons:
        level = "red"
    elif "SRC-NONE" in reasons or "HEARSAY" in reasons:
        level = "gray"
    elif s >= 0.45:
        level = "yellow"
    else:
        level = "clear"
    return {"claim": claim.text, "score": s, "level": level, "reasons": reasons, "chains": chains}