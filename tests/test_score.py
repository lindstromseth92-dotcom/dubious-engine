from dubious.extract import Claim
from dubious.score import score_claim, tier_of


def test_tiers():
    assert tier_of("sec.gov") == "primary"
    assert tier_of("data.sec.gov") == "primary"
    assert tier_of("example.org") == "unknown"


def test_unsourced_is_gray():
    r = score_claim(Claim(text="The sky is green."), None)
    assert r["level"] == "gray" and "SRC-NONE" in r["reasons"]


def test_hearsay():
    r = score_claim(Claim(text="X happened.", attributed_to="sources say"), None)
    assert "HEARSAY" in r["reasons"]