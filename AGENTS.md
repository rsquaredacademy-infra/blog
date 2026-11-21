# AGENTS.md

## Workflow

0. Always ensure `roadmap/` is added to `.gitignore`.
1. Work on one phase at a time.
2. Fix one issue at a time.
3. Commit changes using single line short commit messages.
4. Use conventional commit style for commit messages.
5. Push changes only at the end of each phase.

## R-only feed (index-r.xml), from 2026-11-21
- `index-r.qmd` publishes `/index-r.xml`, the feed for R-Bloggers. It includes only posts whose categories contain **"R"**.
- **Every R post (tutorials, R package posts) must list "R" in `categories`.** Python, SQL-only, bash, platform or course posts must NOT, because R-Bloggers accepts R content only (no platform marketing on aggregators).
- Don't run a full local `quarto render` on Windows: posts/binning-data-with-rbin (1.9 MB embedded HTML) makes pandoc use about 18 GB. Test listing/feed changes in a small copy with a few posts; CI does the full render.
