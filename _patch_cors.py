from pathlib import Path
p = Path("main.py")
t = p.read_text(encoding="utf-8")
old = """app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5174','https://designate-donated-subsoil.ngrok-free.dev'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)"""
new = """app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or [
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    # Explicit list so preflight always echoes custom FE headers (incl. ngrok).
    # Starlette also accepts "*" but we keep named headers for clarity.
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "ngrok-skip-browser-warning",
    ],
)"""
if old not in t:
    # try double-quote variant / spacing
    import re
    m = re.search(r"app\.add_middleware\(\s*CORSMiddleware,.*?\)\n", t, re.S)
    if not m:
        raise SystemExit("CORS block not found")
    print("FOUND_VIA_REGEX")
    print(repr(m.group(0)[:300]))
    t2 = t[:m.start()] + new + "\n" + t[m.end():]
else:
    print("FOUND_EXACT")
    t2 = t.replace(old, new, 1)
p.write_text(t2, encoding="utf-8")
print("patched")
