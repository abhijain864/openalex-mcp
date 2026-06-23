"""OpenAlex MCP Server.

Searches scholarly works and authors via the OpenAlex REST API (https://openalex.org).
Fully open API: no key required. Optionally send a `mailto` for the polite pool.
"""

import os

import httpx
from mcp.server.fastmcp import FastMCP

BASE = "https://api.openalex.org"
# Polite-pool contact. Set the OPENALEX_MAILTO env var to your email to get
# faster, friendlier service from OpenAlex. Falls back to the common pool.
MAILTO = os.environ.get("OPENALEX_MAILTO", "")

mcp = FastMCP("openalex")


def _client() -> httpx.Client:
    params = {"mailto": MAILTO} if MAILTO else {}
    user_agent = f"openalex-mcp (mailto:{MAILTO})" if MAILTO else "openalex-mcp"
    return httpx.Client(
        base_url=BASE,
        params=params,
        timeout=30.0,
        headers={"User-Agent": user_agent},
    )


def _fmt_work(w: dict) -> dict:
    """Trim a raw OpenAlex work down to the fields worth reading."""
    authors = [
        a.get("author", {}).get("display_name")
        for a in w.get("authorships", [])
    ]
    loc = (w.get("primary_location") or {})
    source = (loc.get("source") or {})
    oa = (w.get("open_access") or {})
    return {
        "id": w.get("id"),
        "title": w.get("display_name"),
        "year": w.get("publication_year"),
        "authors": [a for a in authors if a],
        "venue": source.get("display_name"),
        "cited_by_count": w.get("cited_by_count"),
        "doi": w.get("doi"),
        "is_open_access": oa.get("is_oa"),
        "open_access_pdf": oa.get("oa_url"),
        "type": w.get("type"),
    }


@mcp.tool()
def search_works(
    query: str,
    per_page: int = 10,
    year_from: int | None = None,
    year_to: int | None = None,
    open_access_only: bool = False,
    sort_by_citations: bool = False,
) -> list[dict]:
    """Search scholarly papers/works on OpenAlex.

    Args:
        query: Free-text search over title, abstract, and fulltext.
        per_page: Number of results to return (1-50).
        year_from: Only works published in or after this year.
        year_to: Only works published in or before this year.
        open_access_only: If True, restrict to open-access works (free PDFs).
        sort_by_citations: If True, sort by citation count (most cited first)
            instead of relevance.
    """
    filters = []
    if year_from is not None:
        filters.append(f"from_publication_date:{year_from}-01-01")
    if year_to is not None:
        filters.append(f"to_publication_date:{year_to}-12-31")
    if open_access_only:
        filters.append("is_oa:true")

    params: dict = {"search": query, "per_page": max(1, min(per_page, 50))}
    if filters:
        params["filter"] = ",".join(filters)
    if sort_by_citations:
        params["sort"] = "cited_by_count:desc"

    with _client() as c:
        r = c.get("/works", params=params)
        r.raise_for_status()
        data = r.json()

    return [_fmt_work(w) for w in data.get("results", [])]


@mcp.tool()
def get_work(work_id: str) -> dict:
    """Fetch one work by OpenAlex ID (e.g. 'W2741809807') or DOI (e.g.
    '10.1038/nature12373' or a full doi.org URL). Returns full details
    including the reconstructed abstract."""
    ident = work_id.strip()
    if ident.lower().startswith("10.") or "doi.org" in ident.lower():
        doi = ident.split("doi.org/")[-1]
        path = f"/works/doi:{doi}"
    else:
        path = f"/works/{ident}"

    with _client() as c:
        r = c.get(path)
        r.raise_for_status()
        w = r.json()

    out = _fmt_work(w)
    # Reconstruct abstract from OpenAlex's inverted index.
    inv = w.get("abstract_inverted_index")
    if inv:
        positions: dict[int, str] = {}
        for word, idxs in inv.items():
            for i in idxs:
                positions[i] = word
        out["abstract"] = " ".join(positions[i] for i in sorted(positions))
    out["referenced_works_count"] = len(w.get("referenced_works", []))
    return out


@mcp.tool()
def search_authors(name: str, per_page: int = 5) -> list[dict]:
    """Search for authors by name. Returns their OpenAlex ID, affiliation,
    works count, citation count, and top concepts."""
    with _client() as c:
        r = c.get(
            "/authors",
            params={"search": name, "per_page": max(1, min(per_page, 25))},
        )
        r.raise_for_status()
        data = r.json()

    out = []
    for a in data.get("results", []):
        inst = (a.get("last_known_institution") or {})
        out.append({
            "id": a.get("id"),
            "name": a.get("display_name"),
            "affiliation": inst.get("display_name"),
            "works_count": a.get("works_count"),
            "cited_by_count": a.get("cited_by_count"),
            "orcid": a.get("orcid"),
            "top_concepts": [
                x.get("display_name") for x in a.get("x_concepts", [])[:5]
            ],
        })
    return out


@mcp.tool()
def get_author_works(author_id: str, per_page: int = 10) -> list[dict]:
    """List an author's works (most-cited first) by their OpenAlex author ID
    (e.g. 'A5023888391')."""
    aid = author_id.strip().split("/")[-1]
    with _client() as c:
        r = c.get(
            "/works",
            params={
                "filter": f"author.id:{aid}",
                "sort": "cited_by_count:desc",
                "per_page": max(1, min(per_page, 50)),
            },
        )
        r.raise_for_status()
        data = r.json()
    return [_fmt_work(w) for w in data.get("results", [])]


if __name__ == "__main__":
    mcp.run()
