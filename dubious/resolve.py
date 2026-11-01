from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

UA = {"User-Agent": "dubious-engine/0.1 (+https://github.com/<you>/dubious-engine)"}


def fetch(url: str, timeout: float = 10) -> tuple[str, list[str]]:
    """Return (visible text, outbound http links) for a page."""
    r = httpx.get(url, headers=UA, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    links = [a["href"] for a in soup.find_all("a", href=True) if a["href"].startswith("http")]
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("http"):
            a.replace_with(f"{a.get_text(strip=True)} [{a['href']}]")
    return soup.get_text(" ", strip=True), links


def domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def chain(url: str) -> list[str]:
    """One-hop citation chain: [domain of url, *domains it links out to]."""
    out = [domain(url)]
    try:
        _, links = fetch(url)
        out += sorted({domain(l) for l in links} - {out[0]})[:20]
    except Exception:
        pass  # dead link: chain ends here, and the scorer treats that as CHAIN-TERM:none
    return out