import sys

import httpx

from app.scrapers import elempleo as e

query = sys.argv[1] if len(sys.argv) > 1 else "analista de datos"
city = sys.argv[2] if len(sys.argv) > 2 else "Bogotá"

for url in e.candidate_urls(query, city):
    try:
        r = httpx.get(url, headers=e.HEADERS, timeout=20, follow_redirects=True)
    except httpx.HTTPError as ex:
        print(url, "-> error de red:", ex)
        continue
    jobs = e.parse(r.text) if r.status_code == 200 else []
    print(f"{url} -> código {r.status_code}, {len(jobs)} ofertas\n")
    for j in jobs[:6]:
        print(j.title)
        print(f"   empresa:   {j.company or '(no detectada)'}")
        print(f"   ubicación: {j.location or '(no detectada)'}")
        print(f"   texto:     {j.text[:150]}\n")
    if jobs:
        break