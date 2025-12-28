import argparse
import json
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.elsevier_client import ElsevierClient

def search_papers(client: ElsevierClient, query: str, count: int = 10, year: str | None = None) -> dict:
    scopus_query = f"TITLE-ABS-KEY({query})"
    if year:
        scopus_query += f" AND PUBYEAR = {year}"
    params = {"query": scopus_query, "count": min(max(count, 1), 25)}
    res = client.get("/content/search/scopus", params=params)
    if not res["success"]:
        return res

    entries = res["data"].get("search-results", {}).get("entry", [])
    total = int(res["data"].get("search-results", {}).get("opensearch:totalResults", 0))
    papers = []
    for e in entries:
        papers.append({
            "title": e.get("dc:title", "No title"),
            "authors": e.get("dc:creator", "Unknown"),
            "journal": e.get("prism:publicationName", "Unknown"),
            "year": e.get("prism:coverDate", "")[:4],
            "citations": int(e.get("citedby-count", 0) or 0),
            "doi": e.get("prism:doi", ""),
            "eid": e.get("eid", ""),
        })
    return {"success": True, "query": query, "year": year, "total": total, "papers": papers}

def get_paper_abstract(client: ElsevierClient, eid: str | None, doi: str | None) -> dict:
    if not eid and not doi:
        return {"success": False, "error": "Either eid or doi is required."}
    if eid:
        path = f"/content/abstract/eid/{eid}"
    else:
        path = f"/content/abstract/doi/{doi}"
    return client.get(path, params={"view": "FULL"})

def get_author_info(client: ElsevierClient, author_id: str) -> dict:
    if not author_id:
        return {"success": False, "error": "author_id is required."}
    return client.get(f"/content/author/author_id/{author_id}", params={"view": "ENHANCED"})

def analyze_research_trends(client: ElsevierClient, field: str, years: list[int]) -> dict:
    if not field:
        return {"success": False, "error": "field is required."}
    if not years:
        return {"success": False, "error": "years is required."}

    series = []
    for y in years:
        q = f"TITLE-ABS-KEY({field}) AND PUBYEAR = {y}"
        res = client.get("/content/search/scopus", params={"query": q, "count": 0})
        if not res["success"]:
            series.append({"year": y, "success": False, "error": res.get("error")})
            continue
        total = int(res["data"].get("search-results", {}).get("opensearch:totalResults", 0))
        series.append({"year": y, "success": True, "count": total})

    return {"success": True, "field": field, "series": series}

def get_institution_papers(client: ElsevierClient, institution: str, year: str | None) -> dict:
    if not institution:
        return {"success": False, "error": "institution is required."}
    q = f"AFFIL({institution})"
    if year:
        q += f" AND PUBYEAR = {year}"
    res = client.get("/content/search/scopus", params={"query": q, "count": 0})
    if not res["success"]:
        return res
    total = int(res["data"].get("search-results", {}).get("opensearch:totalResults", 0))
    return {"success": True, "institution": institution, "year": year, "count": total}

def search_open_access_papers(client: ElsevierClient, field: str, count: int = 10, year: str | None = None) -> dict:
    if not field:
        return {"success": False, "error": "field is required."}
    q = f"TITLE-ABS-KEY({field}) AND OPENACCESS(1)"
    if year:
        q += f" AND PUBYEAR = {year}"
    params = {"query": q, "count": min(max(count, 1), 25), "sort": "citedby-count"}
    res = client.get("/content/search/scopus", params=params)
    if not res["success"]:
        return res
    entries = res["data"].get("search-results", {}).get("entry", [])
    total = int(res["data"].get("search-results", {}).get("opensearch:totalResults", 0))

    papers = []
    for e in entries:
        papers.append({
            "title": e.get("dc:title", "No title"),
            "authors": e.get("dc:creator", "Unknown"),
            "journal": e.get("prism:publicationName", "Unknown"),
            "citations": int(e.get("citedby-count", 0) or 0),
            "doi": e.get("prism:doi", ""),
            "open_access": True,
        })
    return {"success": True, "field": field, "year": year, "total_open_access": total, "papers": papers}

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("search_papers")
    sp.add_argument("--query", required=True)
    sp.add_argument("--count", type=int, default=10)
    sp.add_argument("--year", default=None)

    ab = sub.add_parser("get_paper_abstract")
    ab.add_argument("--eid", default=None)
    ab.add_argument("--doi", default=None)

    au = sub.add_parser("get_author_info")
    au.add_argument("--author_id", required=True)

    tr = sub.add_parser("analyze_research_trends")
    tr.add_argument("--field", required=True)
    tr.add_argument("--years", nargs="+", type=int, required=True)

    ins = sub.add_parser("get_institution_papers")
    ins.add_argument("--institution", required=True)
    ins.add_argument("--year", default=None)

    oa = sub.add_parser("search_open_access_papers")
    oa.add_argument("--field", required=True)
    oa.add_argument("--count", type=int, default=10)
    oa.add_argument("--year", default=None)

    args = p.parse_args()
    try:
        client = ElsevierClient()
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return

    if args.cmd == "search_papers":
        out = search_papers(client, args.query, args.count, args.year)
    elif args.cmd == "get_paper_abstract":
        out = get_paper_abstract(client, args.eid, args.doi)
    elif args.cmd == "get_author_info":
        out = get_author_info(client, args.author_id)
    elif args.cmd == "analyze_research_trends":
        out = analyze_research_trends(client, args.field, args.years)
    elif args.cmd == "get_institution_papers":
        out = get_institution_papers(client, args.institution, args.year)
    elif args.cmd == "search_open_access_papers":
        out = search_open_access_papers(client, args.field, args.count, args.year)
    else:
        out = {"success": False, "error": f"Unknown cmd: {args.cmd}"}

    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
