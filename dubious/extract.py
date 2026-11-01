import os

from google import genai
from google.genai import types
from pydantic import BaseModel


class Claim(BaseModel):
    text: str
    cited_urls: list[str] = []
    attributed_to: str | None = None   # named person/org, or phrases like "officials say"
    cites_data_year: int | None = None # year of any statistic the claim leans on


class Extraction(BaseModel):
    claims: list[Claim]


PROMPT = """Extract the checkable factual claims from the text below.
A checkable claim is a statement about the world that could in principle be verified: an event, a number, a quote, an attribution.
Skip opinions, predictions, and rhetorical questions.
For each claim record any URLs the text cites in direct support of it, who the claim is attributed to (a named source, or a vague one like "sources say"), and the year of any statistic it relies on if stated.
URLs appear in square brackets right after the text they link from. Return at most 10 claims."""

_client: genai.Client | None = None


def client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def extract(text: str, model: str = "gemini-3.8-flash") -> tuple[list[Claim], dict]:
    resp = client().models.generate_content(
        model=model,
        contents=f"{PROMPT}\n\nTEXT:\n{text[:20000]}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Extraction,
            temperature=0,
        ),
    )
    usage = resp.usage_metadata
    return resp.parsed.claims, {"in": usage.prompt_token_count, "out": usage.candidates_token_count}