"""Gera os cards de estatísticas do perfil usando a API GraphQL do GitHub."""
import json, os, sys, urllib.request
from html import escape

USER = os.environ.get("GH_USER", "rafaelsanoli")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"

C = dict(accent="#7aa2f7", cyan="#7dcfff", purple="#bb9af7", text="#c9d1d9", muted="#8b949e", line="#30363d")
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
  }
}"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(body["errors"])
    return body["data"]["user"]


def card(w, h, title, inner):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<style>
  .t {{ font: 600 17px {FONT}; fill: {C["accent"]}; }}
  .l {{ font: 400 14px {FONT}; fill: {C["text"]}; }}
  .v {{ font: 700 14px {FONT}; fill: #e6edf3; }}
  .m {{ font: 400 11px {FONT}; fill: {C["muted"]}; }}
  .f {{ opacity: 0; animation: in .6s ease forwards; }}
  @keyframes in {{ from {{ opacity: 0; transform: translateX(-6px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
</style>
<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="10" fill="none" stroke="{C["line"]}"/>
<text x="24" y="36" class="t">{escape(title)}</text>
{inner}
</svg>'''


def stats_card(u):
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    rows = [
        ("Commits (último ano)", u["contributionsCollection"]["totalCommitContributions"]),
        ("Contribuições (último ano)", u["contributionsCollection"]["contributionCalendar"]["totalContributions"]),
        ("Repositórios públicos", u["repositories"]["totalCount"]),
        ("Pull requests", u["pullRequests"]["totalCount"]),
        ("Stars recebidas", stars),
        ("Seguidores", u["followers"]["totalCount"]),
    ]
    icons = [C["accent"], C["cyan"], C["purple"], C["accent"], C["cyan"], C["purple"]]
    inner = ""
    for i, ((label, val), col) in enumerate(zip(rows, icons)):
        y = 70 + i * 26
        inner += (f'<g class="f" style="animation-delay:{i*120}ms">'
                  f'<circle cx="30" cy="{y-5}" r="4" fill="{col}"/>'
                  f'<text x="44" y="{y}" class="l">{label}</text>'
                  f'<text x="330" y="{y}" class="v" text-anchor="end">{val}</text></g>')
    return card(360, 230, "~/stats", inner)


def langs_card(u):
    totals = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            t = totals.setdefault(n, [0, e["node"]["color"] or C["accent"]])
            t[0] += e["size"]
    top = sorted(totals.items(), key=lambda kv: -kv[1][0])[:6]
    total = sum(v[0] for _, v in top) or 1
    inner, x = "", 24
    bar_w = 312
    inner += f'<mask id="bm"><rect x="24" y="56" width="{bar_w}" height="10" rx="5" fill="#fff"/></mask><g mask="url(#bm)" style="transform-origin:24px 0;animation:grow 1s ease forwards">'
    for name, (size, color) in top:
        w = bar_w * size / total
        inner += f'<rect x="{x:.1f}" y="56" width="{w+0.5:.1f}" height="10" fill="{color}"/>'
        x += w
    inner += "</g>"
    for i, (name, (size, color)) in enumerate(top):
        col, row = i % 2, i // 2
        cx, cy = 30 + col * 160, 100 + row * 30
        pct = 100 * size / total
        inner += (f'<g class="f" style="animation-delay:{300+i*100}ms">'
                  f'<circle cx="{cx}" cy="{cy-4}" r="5" fill="{color}"/>'
                  f'<text x="{cx+12}" y="{cy}" class="l">{escape(name)} <tspan class="m">{pct:.1f}%</tspan></text></g>')
    if not top:
        inner += '<text x="24" y="100" class="m">sem dados ainda</text>'
    return card(360, 230, "~/langs", inner)


def activity_card(u):
    days = [d for w in u["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]][-60:]
    W, H = 760, 230
    left, right, top, bottom = 44, 24, 60, 190
    mx = max([d["contributionCount"] for d in days] + [1])
    step = (W - left - right) / max(len(days) - 1, 1)
    pts = [(left + i * step, bottom - (bottom - top) * d["contributionCount"] / mx) for i, d in enumerate(days)]
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = path + f" L{pts[-1][0]:.1f},{bottom} L{pts[0][0]:.1f},{bottom} Z"
    grid = "".join(f'<line x1="{left}" x2="{W-right}" y1="{bottom-(bottom-top)*k/4:.1f}" y2="{bottom-(bottom-top)*k/4:.1f}" stroke="{C["line"]}" stroke-dasharray="3 4"/>'
                   f'<text x="{left-8}" y="{bottom-(bottom-top)*k/4+4:.1f}" class="m" text-anchor="end">{round(mx*k/4)}</text>' for k in range(5))
    labels = "".join(f'<text x="{pts[i][0]:.1f}" y="{bottom+20}" class="m" text-anchor="middle">{days[i]["date"][8:]}/{days[i]["date"][5:7]}</text>'
                     for i in range(0, len(days), 10))
    length = sum(((pts[i][0]-pts[i-1][0])**2 + (pts[i][1]-pts[i-1][1])**2) ** .5 for i in range(1, len(pts))) + 1
    inner = f'''<defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{C["accent"]}" stop-opacity=".45"/><stop offset="1" stop-color="{C["accent"]}" stop-opacity="0"/></linearGradient>
<linearGradient id="lg" x1="0" x2="1"><stop offset="0" stop-color="{C["cyan"]}"/><stop offset=".5" stop-color="{C["accent"]}"/><stop offset="1" stop-color="{C["purple"]}"/></linearGradient></defs>
{grid}{labels}
<path d="{area}" fill="url(#ag)" class="f" style="animation-delay:.8s"/>
<path d="{path}" fill="none" stroke="url(#lg)" stroke-width="2.5" stroke-linejoin="round" stroke-dasharray="{length:.0f}" stroke-dashoffset="{length:.0f}">
<animate attributeName="stroke-dashoffset" to="0" dur="1.6s" fill="freeze"/></path>
<text x="{W-24}" y="36" class="m" text-anchor="end">últimos 60 dias</text>'''
    return card(W, H, "~/activity", inner)


def main():
    u = fetch() if TOKEN else json.load(open(os.environ["MOCK"]))
    os.makedirs(OUT, exist_ok=True)
    for name, fn in [("stats", stats_card), ("langs", langs_card), ("activity", activity_card)]:
        with open(os.path.join(OUT, f"{name}.svg"), "w", encoding="utf-8") as f:
            f.write(fn(u))
    print("cards gerados em", OUT)


if __name__ == "__main__":
    main()
