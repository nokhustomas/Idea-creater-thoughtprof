from app import app
print('URL map:')
for r in app.url_map.iter_rules():
    print(f'  {r.rule!r} -> {r.endpoint} methods={sorted(r.methods)}')