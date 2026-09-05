import json
import urllib.request
import urllib.error
import time

d = json.load(open('arxiv_papers.json'))
print(f"Loaded {len(d)} papers")
assert len(d) > 0, "arxiv_papers.json must have >0 entries"

valid_ids = []
failed = []
for p in d:
    aid = p['id']
    url = f"http://export.arxiv.org/api/query?id_list={aid}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'arxiv-verifier/1.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read().decode('utf-8', errors='ignore')
        if '<entry>' in body and aid in body:
            valid_ids.append(aid)
            print(f"OK  {aid}")
        else:
            failed.append(aid)
            print(f"NO_ENTRY {aid}")
    except urllib.error.HTTPError as e:
        failed.append(aid)
        print(f"HTTP{e.code} {aid}")
    except Exception as e:
        failed.append(aid)
        print(f"ERR {aid}: {e}")
    time.sleep(3.0)  # arXiv rate limit

print(f"\nResult: {len(valid_ids)} valid, {len(failed)} failed")
assert len(valid_ids) >= 5, f"need >=5 valid papers, got {len(valid_ids)}"
print("PASS: arxiv papers verified")