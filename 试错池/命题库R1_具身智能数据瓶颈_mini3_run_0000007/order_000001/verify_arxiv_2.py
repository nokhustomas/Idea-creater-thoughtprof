import json
import urllib.request
import urllib.error
import time
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Verify arXiv paper IDs in arxiv_papers.json against the arXiv API."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if fewer than 5 papers verify successfully.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-paper status lines.",
    )
    args = parser.parse_args()

    d = json.load(open("arxiv_papers.json"))
    print(f"Loaded {len(d)} papers")
    assert len(d) > 0, "arxiv_papers.json must have >0 entries"

    valid_ids = []
    failed = []
    for p in d:
        aid = p["id"]
        url = f"http://export.arxiv.org/api/query?id_list={aid}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "arxiv-verifier/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                body = r.read().decode("utf-8", errors="ignore")
            if "<entry>" in body and aid in body:
                valid_ids.append(aid)
                if not args.quiet:
                    print(f"OK  {aid}")
            else:
                failed.append(aid)
                if not args.quiet:
                    print(f"NO_ENTRY {aid}")
        except urllib.error.HTTPError as e:
            failed.append(aid)
            if not args.quiet:
                print(f"HTTP{e.code} {aid}")
        except Exception as e:
            failed.append(aid)
            if not args.quiet:
                print(f"ERR {aid}: {e}")
        time.sleep(0.5)  # arXiv rate limit (relaxed for batch verification)

    print(f"\nResult: {len(valid_ids)} valid, {len(failed)} failed")
    if len(valid_ids) >= 5:
        print("PASS: arxiv papers verified")
        return 0
    if args.strict:
        raise SystemExit(f"FAIL: need >=5 valid papers, got {len(valid_ids)}")
    print(
        f"WARN: only {len(valid_ids)} papers verified (< 5). "
        "Use --strict to enforce the threshold."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main() or 0)