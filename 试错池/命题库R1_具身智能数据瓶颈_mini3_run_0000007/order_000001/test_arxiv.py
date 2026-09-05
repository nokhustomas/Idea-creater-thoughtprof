import urllib.request
try:
    req = urllib.request.Request('http://export.arxiv.org/api/query?id_list=2310.03100', headers={'User-Agent':'test/1.0'})
    body = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
    print('LEN:', len(body))
    print('HAS_ENTRY:', '<entry>' in body)
    print('HAS_ID:', '2310.03100' in body)
    print(body[:300])
except Exception as e:
    print('ERR:', type(e).__name__, e)