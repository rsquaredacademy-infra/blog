"""Phase 0 inventory + redirect-audit scaffold for the Quarto migration.

Reads content/post/*.Rmd, pairs each with its pre-rendered content/post/*.html
fragment, parses frontmatter (stdlib only), and writes local-only CSVs into
roadmap/ (gitignored, never committed):

  roadmap/inventory.csv       per-post flags for manual triage
  roadmap/redirect-audit.csv  legacy_url -> /posts/<slug>/ single-hop 301 map

Usage:
  python scripts/inventory.py                 # inventory + redirect audit
  python scripts/inventory.py --check         # verify outputs exist, print summary
  python scripts/inventory.py --migrate       # Phase 1 only: emit posts/<slug>/index.qmd
                                              # static bundles (eval: false)
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POST_DIR = ROOT / "content" / "post"
ROADMAP_DIR = ROOT / "roadmap"
INVENTORY_CSV = ROADMAP_DIR / "inventory.csv"
REDIRECT_CSV = ROADMAP_DIR / "redirect-audit.csv"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
FILENAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(.+)\.Rmd$")
YOUTUBE_RE = re.compile(r"""blogdown::shortcode\(\s*["']youtube["']\s*,\s*["']([^"']+)["']""")
INCLUDE_GRAPHICS_RE = re.compile(r"""knitr::include_graphics\(\s*["']([^"']+)["']""")
CHUNK_RE = re.compile(r"^```\{r\s*([^}]*)\}", re.MULTILINE)
HTTP_URL_RE = re.compile(r"https?://[^\s)'\"]+")
WIDGET_RE = re.compile(r"datatable|htmlwidget|crosstalk|kableExtra|DT::|plotly|leaflet|rmarkdown-libs", re.IGNORECASE)
LIVE_API_RE = re.compile(r"yahoo|quantmod|nse|tq_get|getSymbols|api\.|jsonplaceholder|read\.csv\(['\"]http", re.IGNORECASE)


def parse_frontmatter(text: str) -> dict:
    """Minimal YAML-subset parser for blogdown frontmatter (scalars + flat lists)."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm: dict = {}
    current_key: str | None = None
    for raw_line in m.group(1).splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith(" ") or line.startswith("\t"):
            stripped = line.strip()
            if stripped.startswith("- ") and current_key:
                fm.setdefault(current_key, []).append(stripped[2:].strip().strip("'\""))
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip("'\"")
            if value == "":
                fm[key] = []
            else:
                fm[key] = value
            current_key = key
    return fm


def as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def slug_from(filename: str, fm: dict) -> str:
    if fm.get("slug"):
        return str(fm["slug"]).strip().strip("/")
    m = FILENAME_RE.match(filename)
    if m:
        return m.group(4)
    return Path(filename).stem


def date_from(filename: str, fm: dict) -> str:
    if fm.get("date"):
        return str(fm["date"]).strip("'\"")
    m = FILENAME_RE.match(filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def iter_posts() -> list[dict]:
    rows: list[dict] = []
    rmd_files = sorted(POST_DIR.glob("*.Rmd"))
    html_names = {p.stem for p in POST_DIR.glob("*.html")}
    for rmd in rmd_files:
        text = rmd.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        body = FRONTMATTER_RE.sub("", text, count=1)
        slug = slug_from(rmd.name, fm)
        twitter_img = str(fm.get("twitterImg", ""))
        graphics = INCLUDE_GRAPHICS_RE.findall(body)
        rows.append({
            "file": rmd.name,
            "slug": slug,
            "date": date_from(rmd.name, fm),
            "title": str(fm.get("title", "")),
            "author": str(fm.get("author", "")),
            "description": str(fm.get("description", "")),
            "twitterImg": twitter_img,
            # Quarto resolves `image:` relative to the POST dir, so keep the
            # leading / (site-root). The //img double-slash was a Hugo-only bug.
            "image": twitter_img if twitter_img.startswith("/") else f"/{twitter_img}" if twitter_img else "",
            "categories": "|".join(as_list(fm.get("categories")) or as_list(fm.get("topics"))),
            "tags": "|".join(as_list(fm.get("tags"))),
            "uses_topics_key": "topics" in fm,
            "has_html_pair": rmd.stem in html_names,
            "twitterImg_leading_slash": twitter_img.startswith("/"),
            "include_graphics_absolute": "|".join(g for g in graphics if g.startswith("/")),
            "include_graphics_count": len(graphics),
            "youtube_ids": "|".join(YOUTUBE_RE.findall(body)),
            "chunk_count": len(CHUNK_RE.findall(body)),
            "has_widgets": bool(WIDGET_RE.search(body)),
            "has_live_api": bool(LIVE_API_RE.search(body)),
            "external_urls": len(set(HTTP_URL_RE.findall(body))),
        })
    # Orphan .html fragments with no .Rmd source (e.g. the 81-vs-82 mismatch).
    rmd_stems = {Path(r["file"]).stem for r in rows}
    orphans = sorted(s for s in html_names if s not in rmd_stems)
    for stem in orphans:
        rows.append({
            "file": "", "slug": stem, "date": "", "title": "ORPHAN-HTML-NO-RMD",
            "author": "", "description": "", "twitterImg": "", "image": "",
            "categories": "", "tags": "", "uses_topics_key": False,
            "has_html_pair": True, "twitterImg_leading_slash": False,
            "include_graphics_absolute": "", "include_graphics_count": 0,
            "youtube_ids": "", "chunk_count": 0, "has_widgets": False,
            "has_live_api": False, "external_urls": 0,
        })
    return rows


INVENTORY_FIELDS = ["file", "slug", "date", "title", "author", "description",
                    "twitterImg", "image", "categories", "tags", "uses_topics_key",
                    "has_html_pair", "twitterImg_leading_slash",
                    "include_graphics_absolute", "include_graphics_count",
                    "youtube_ids", "chunk_count", "has_widgets", "has_live_api",
                    "external_urls"]


def write_inventory(rows: list[dict]) -> None:
    ROADMAP_DIR.mkdir(exist_ok=True)
    with INVENTORY_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=INVENTORY_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def parse_legacy_redirects() -> list[tuple[str, str]]:
    """Return (origin, target) pairs from static/_redirects + frozen netlify.toml.

    static/netlify.toml was retired in Phase 1 (it held only redirects); its
    78 rules live on frozen in scripts/legacy-netlify.toml so regeneration
    never loses them.
    """
    pairs: list[tuple[str, str]] = []
    redirects_file = ROOT / "static" / "_redirects"
    if redirects_file.exists():
        for line in redirects_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                pairs.append((parts[0], parts[1]))
    netlify_toml = ROOT / "scripts" / "legacy-netlify.toml"
    if netlify_toml.exists():
        from_re, to_re = None, None
        for line in netlify_toml.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if s.startswith("from"):
                from_re = s.split("=", 1)[1].strip().strip("'\"")
            elif s.startswith("to"):
                to_re = s.split("=", 1)[1].strip().strip("'\"")
            if from_re and to_re:
                pairs.append((from_re, to_re))
                from_re, to_re = None, None
    return pairs


def final_slug_for_target(target: str, known_slugs: set[str]) -> str | None:
    """Map a legacy redirect target (/slug/ or absolute URL) to a known slug."""
    t = target.strip()
    for prefix in ("https://blog.rsquaredacademy.com", "http://blog.rsquaredacademy.com"):
        if t.startswith(prefix):
            t = t[len(prefix):]
    t = t.strip().strip("/")
    if "/" in t:  # hub/index targets (data-visualization/index.html) are not posts
        return None
    return t if t in known_slugs else None


def write_redirect_audit(rows: list[dict]) -> None:
    slugs: dict[str, str] = {}  # slug -> date
    for r in rows:
        if r["slug"] and r["title"] != "ORPHAN-HTML-NO-RMD" and r["slug"] not in slugs:
            slugs[r["slug"]] = r["date"]
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(legacy: str, slug: str, rtype: str) -> None:
        key = (legacy, f"/posts/{slug}/")
        if key not in seen:
            seen.add(key)
            out.append({"legacy_url": legacy, "new_url": f"/posts/{slug}/",
                        "type": rtype, "http_status": 301, "verified": ""})

    for slug, date in sorted(slugs.items()):
        add(f"/{slug}/", slug, "1:1-exact")
        add(f"/post/{slug}", slug, "1:1-exact")
        add(f"/post/{slug}/", slug, "1:1-exact")
        if re.match(r"\d{4}-\d{2}-\d{2}", date):
            y, mo, d = date.split("-")
            add(f"/{y}/{mo}/{d}/{slug}/", slug, "1:1-exact")

    # Collapse existing legacy origins directly onto final /posts/<slug>/ (no chains).
    for origin, target in parse_legacy_redirects():
        slug = final_slug_for_target(target, set(slugs))
        if slug:
            add(origin, slug, "1:1-exact")
        else:
            key = (origin, target)
            if key not in seen:
                seen.add(key)
                out.append({"legacy_url": origin, "new_url": target,
                            "type": "taxonomy-hub", "http_status": 301, "verified": ""})

    # Structural fallbacks (lowest precedence; Netlify evaluates 1:1 rules first).
    for legacy, new in [("/post/*", "/posts/:splat"),
                        ("/topics/*", "/r-programming/"),
                        ("/categories/*", "/r-programming/"),
                        ("/tags/*", "/r-programming/")]:
        out.append({"legacy_url": legacy, "new_url": new, "type": "taxonomy-hub",
                    "http_status": 301, "verified": ""})

    with REDIRECT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["legacy_url", "new_url", "type",
                                          "http_status", "verified"])
        w.writeheader()
        w.writerows(out)


def _yaml_str(value: str) -> str:
    """Quote a scalar for YAML frontmatter (handles embedded quotes)."""
    if '"' not in value:
        return f'"{value}"'
    return "'" + value.replace("'", "''") + "'"


def _yaml_list(piped: str) -> str:
    return "[" + ", ".join(_yaml_str(v) for v in piped.split("|") if v) + "]"


def _strip_host(url: str) -> str:
    url = url.strip()
    for prefix in ("https://blog.rsquaredacademy.com", "http://blog.rsquaredacademy.com"):
        if url.startswith(prefix):
            url = url[len(prefix):]
    return url.strip().rstrip("/") or "/"


def write_netlify_redirects(rows: list[dict], dest: Path) -> None:
    """Generate a Netlify _redirects file from redirect-audit.csv.

    Normalizes legacy cruft: absolute URLs stripped to paths, bare-/ targets
    remapped to hubs (never /), legacy /X/index.html hubs to /X/, malformed
    origins (whitespace/truncation) dropped, duplicate origins deduped with
    post targets winning over hubs (Netlify is first-match-wins). 1:1 exacts
    first, fallbacks last. Also rewrites redirect-audit.csv to match.
    """
    HUBS = {"/data-visualization/", "/data-wrangling/", "/r-programming/",
            "/r-packages/"}
    known = {r["slug"] for r in rows if r["title"] != "ORPHAN-HTML-NO-RMD"}
    exact: dict[str, str] = {}
    dropped: list[str] = []
    replaced: list[str] = []

    def add(legacy: str, new: str) -> None:
        if not legacy.startswith("/"):
            return
        cur = exact.get(legacy)
        if cur is None:
            exact[legacy] = new
        elif cur != new:
            # Duplicate origin (Netlify first-match-wins): a /posts/ target
            # always beats a hub target.
            if new.startswith("/posts/") and not cur.startswith("/posts/"):
                exact[legacy] = new
                replaced.append(f"{legacy}: {cur} -> {new}")
            else:
                replaced.append(f"{legacy}: kept {cur}, ignored {new}")

    with REDIRECT_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            legacy = _strip_host(row["legacy_url"])
            target = _strip_host(row["new_url"])
            if row["type"] == "taxonomy-hub" and legacy.endswith("/*"):
                continue  # fallbacks appended explicitly below
            if any(c.isspace() for c in legacy) or "..." in legacy:
                dropped.append(f"{row['legacy_url']} -> {row['new_url']}")
                continue
            flat = target.strip("/").split("/")[-1]
            if flat in known:
                add(legacy, f"/posts/{flat}/")
            elif target in HUBS or target + "/" in HUBS:
                add(legacy, target if target in HUBS else target + "/")
            elif legacy in ("/start-here", "/start-here/", "/page/4/"):
                add(legacy, "/")
            elif legacy in ("/about/", "/subscribe/"):
                add(legacy, "/about/")
            elif target == "/":
                add(legacy, "/r-programming/")
            else:
                # Explicit renames / legacy hub paths.
                rename = {
                    "/getting-help-in-r/": "getting-help-in-r-updated",
                    "/data-visualization/index.html": "/data-visualization/",
                    "/data-wrangling/index.html": "/data-wrangling/",
                    "/r-programming/index.html": "/r-programming/",
                    "/r-packages/index.html": "/r-packages/",
                }
                mapped = rename.get(target, rename.get(target + "/", ""))
                if mapped in known:
                    add(legacy, f"/posts/{mapped}/")
                elif mapped:
                    add(legacy, mapped)
                else:
                    dropped.append(f"{row['legacy_url']} -> {row['new_url']}")

    with dest.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# Generated by: python scripts/inventory.py --redirects _redirects\n")
        f.write("# Source of truth: roadmap/redirect-audit.csv (gitignored, local).\n")
        f.write("# 1:1 exacts first (Netlify matches top-down); fallbacks last.\n")
        for legacy in sorted(exact):
            f.write(f"{legacy}  {exact[legacy]}  301!\n")
        f.write("# Structural fallbacks (no bare-/ targets; hubs only).\n")
        f.write("/post/*  /posts/:splat  301!\n")
        f.write("/topics/*  /r-programming/  301\n")
        f.write("/categories/*  /r-programming/  301\n")
        f.write("/tags/*  /r-programming/  301\n")
    print(f"redirects: {len(exact)} exact + 4 fallbacks -> {dest}")
    if replaced:
        print(f"duplicate origins resolved ({len(replaced)}):")
        for r in replaced:
            print("  ", r)
    if dropped:
        print(f"dropped {len(dropped)} unmappable rows:")
        for d in dropped:
            print("  ", d)
    # Sync redirect-audit.csv to the deployed mapping (normalized targets,
    # malformed rows removed, verified reset for re-check).
    kept: list[dict] = []
    with REDIRECT_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["type"] == "taxonomy-hub" and row["legacy_url"].endswith("/*"):
                continue  # fallbacks re-appended below
            legacy = _strip_host(row["legacy_url"])
            if legacy in exact:
                row["legacy_url"] = legacy
                row["new_url"] = exact[legacy]
                row["verified"] = ""
                kept.append(row)
    # de-dupe rows that collapsed onto one origin (prefer 1:1-exact)
    deduped: dict[str, dict] = {}
    for row in kept:
        prev = deduped.get(row["legacy_url"])
        if prev is None or (prev["type"] != "1:1-exact" and row["type"] == "1:1-exact"):
            deduped[row["legacy_url"]] = row
    final_rows = [deduped[k] for k in sorted(deduped)]
    for legacy, new in [("/post/*", "/posts/:splat"), ("/topics/*", "/r-programming/"),
                        ("/categories/*", "/r-programming/"), ("/tags/*", "/r-programming/")]:
        final_rows.append({"legacy_url": legacy, "new_url": new, "type": "taxonomy-hub",
                           "http_status": 301, "verified": ""})
    with REDIRECT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["legacy_url", "new_url", "type",
                                          "http_status", "verified"])
        w.writeheader()
        w.writerows(final_rows)
    print(f"audit csv synced: {len(final_rows)} rows -> {REDIRECT_CSV}")
def migrate_bundles(rows: list[dict]) -> int:
    """Phase 1 only: emit posts/<slug>/index.qmd static bundles (eval: false).

    Body reuses the pre-rendered content/post/*.html fragment (frontmatter
    stripped). Blogdown figure dirs (static/post/<stem>_files/) are copied into
    the bundle and /post/<stem>_files/ refs rewritten bundle-relative.
    /img/..., /images/..., /rmarkdown-libs/... stay absolute (moved to root).
    """
    import shutil

    posts_dir = ROOT / "posts"
    count = 0
    # Duplicate slugs (flat Hugo permalinks kept only one): newest file wins.
    deduped: dict[str, dict] = {}
    for r in rows:
        if not r["slug"] or r["title"] == "ORPHAN-HTML-NO-RMD":
            continue
        prev = deduped.get(r["slug"])
        if prev is None or r["file"] > prev["file"]:
            deduped[r["slug"]] = r
    for r in deduped.values():
        dest = posts_dir / r["slug"] / "index.qmd"
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        body = ""
        stem = Path(r["file"]).stem if r["file"] else ""
        frag = POST_DIR / f"{stem}.html" if stem else None
        if frag is not None and frag.exists():
            body = FRONTMATTER_RE.sub("", frag.read_text(encoding="utf-8",
                                                          errors="replace"), count=1)
            files_dir = ROOT / "static" / "post" / f"{stem}_files"
            if files_dir.is_dir():
                shutil.copytree(files_dir, dest.parent / f"{stem}_files",
                                dirs_exist_ok=True)
                body = body.replace(f"/post/{stem}_files/", f"{stem}_files/")
            # Drop <img> refs whose files exist nowhere (dead on live site too).
            for dead in (r'<img\s+src\s*=\s*"data-viz\.png"[^>]*>\s*\n?(<p class="caption">data-viz</p>\s*\n?)?',
                         r'<img\s+src\s*=\s*"/post/components\.png"[^>]*>\s*\n?'):
                body, n = re.subn(dead, "", body)
                if n:
                    print(f"  dropped dead img in {r['slug']} ({n} tag(s))")
        else:
            body = "<!-- WARNING: no pre-rendered .html pair — body pending refresh. -->\n"
        dest.write_text(
            "---\n"
            f"title: {_yaml_str(r['title'])}\n"
            "author: \"Aravind Hebbali\"\n"
            f"date: {_yaml_str(r['date'])}\n"
            f"description: {_yaml_str(r['description'])}\n"
            + (f"image: {_yaml_str(r['image'])}\n" if r["image"] else "")
            + (f"categories: {_yaml_list(r['categories'])}\n" if r["categories"] else "")
            + (f"tags: {_yaml_list(r['tags'])}\n" if r["tags"] else "")
            + "execute:\n  eval: false\n  freeze: true\n"
            + "---\n\n"
            f"<!-- Migrated from content/post/{r['file']}. -->\n"
            "<!-- Day-1 static bundle: body reuses the pre-rendered .html fragment. -->\n\n"
            + body.lstrip("\n"),
            encoding="utf-8",
        )
        count += 1
    return count


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Phase 0 inventory + redirect audit")
    ap.add_argument("--check", action="store_true", help="verify outputs, print summary")
    ap.add_argument("--migrate", action="store_true", help="Phase 1 only: emit posts/ bundles")
    ap.add_argument("--redirects", metavar="PATH",
                    help="Phase 1 only: write a Netlify _redirects file to PATH")
    args = ap.parse_args(argv)

    if args.check:
        ok = INVENTORY_CSV.exists() and REDIRECT_CSV.exists()
        if not ok:
            print(f"missing: {[str(p) for p in (INVENTORY_CSV, REDIRECT_CSV) if not p.exists()]}")
            return 1
        with INVENTORY_CSV.open(encoding="utf-8") as f:
            inv = list(csv.DictReader(f))
        with REDIRECT_CSV.open(encoding="utf-8") as f:
            red = list(csv.DictReader(f))
        print(f"posts={len(inv)} redirects={len(red)} "
              f"orphans={sum(1 for r in inv if r['title'] == 'ORPHAN-HTML-NO-RMD')} "
              f"missing_html={sum(1 for r in inv if r['has_html_pair'] == 'False')} "
              f"widgets={sum(1 for r in inv if r['has_widgets'] == 'True')} "
              f"live_api={sum(1 for r in inv if r['has_live_api'] == 'True')}")
        return 0

    rows = iter_posts()
    write_inventory(rows)
    write_redirect_audit(rows)
    print(f"inventory: {len(rows)} rows -> {INVENTORY_CSV}")
    with REDIRECT_CSV.open(encoding="utf-8") as f:
        print(f"redirects: {sum(1 for _ in f) - 1} rows -> {REDIRECT_CSV}")
    if args.migrate:
        print(f"bundles: {migrate_bundles(rows)} created under posts/")
    if args.redirects:
        write_netlify_redirects(rows, Path(args.redirects))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
