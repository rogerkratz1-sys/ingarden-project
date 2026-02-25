import io, re, sys
fn = "motif_discovery_test.py"
with io.open(fn, "r", encoding="utf8") as fh:
    src = fh.read()

# find consecutive from __future__ import lines at top
m = re.match(r"^(?:\s*#.*\n|\s*\n|(?:from\s+__future__\s+import\s+[^\n]+\n)+)", src, flags=re.MULTILINE)
insert_after = 0
if m:
    insert_after = m.end()
else:
    # if no future imports, try to keep shebang or encoding comment at top
    m2 = re.match(r"^(?:#![^\n]*\n|#.*coding[:=]\s*[-\w.]+\s*\n)?", src)
    insert_after = m2.end() if m2 else 0

# prepare insertion text
insertion = "outdir = None\\n"

# avoid double-inserting if already present near top
top_snippet = src[insert_after:insert_after+200]
if "outdir = None" not in top_snippet:
    new_src = src[:insert_after] + insertion + src[insert_after:]
    with io.open(fn, "w", encoding="utf8") as fh:
        fh.write(new_src)
    print("Inserted outdir = None after top imports/comments.")
else:
    print("outdir = None already present near top; no change made.")
