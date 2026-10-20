"""Writing saved on Windows must reach the fish intact.

Every reader used ``read_text(encoding="utf-8", errors="replace")``. Found on a
fresh Windows 11 box by following docs/getting-started.md in PowerShell:

- a UTF-8 BOM (Notepad, PowerShell ``>``) rode into every crystal as U+FEFF;
- UTF-16 (Notepad "Unicode", PowerShell 5.1's default redirection) was eaten
  as NUL-interleaved noise;
- cp1252 punctuation and accents became U+FFFD;
- the MCP server decoded stdin with the locale codec (cp1252), so non-ASCII
  from the client arrived as mojibake, and a BOM-prefixed first line made it
  silently drop ``initialize``.
"""

import codecs
import json
import os
import subprocess
import sys

from linafish.ingest import ingest_file, read_user_text

TEXT = "Café talk — it didn’t land, but I like work where you can see the result."


def _write(tmp_path, name, data: bytes):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_plain_utf8(tmp_path):
    assert read_user_text(_write(tmp_path, "a.txt", TEXT.encode("utf-8"))) == TEXT


def test_utf8_bom_is_stripped(tmp_path):
    p = _write(tmp_path, "a.txt", codecs.BOM_UTF8 + TEXT.encode("utf-8"))
    assert read_user_text(p) == TEXT


def test_utf16_le_and_be(tmp_path):
    for i, enc in enumerate(("utf-16-le", "utf-16-be")):
        bom = codecs.BOM_UTF16_LE if enc.endswith("le") else codecs.BOM_UTF16_BE
        p = _write(tmp_path, f"u{i}.txt", bom + TEXT.encode(enc))
        assert read_user_text(p) == TEXT


def test_cp1252_fallback(tmp_path):
    p = _write(tmp_path, "a.txt", TEXT.encode("cp1252"))
    assert read_user_text(p) == TEXT


def test_ingest_utf16_txt_has_no_nuls_or_bom(tmp_path):
    p = _write(tmp_path, "entry.txt", codecs.BOM_UTF16_LE + (TEXT * 3).encode("utf-16-le"))
    chunks = ingest_file(p)
    assert chunks
    joined = "".join(c.text for c in chunks)
    assert "\x00" not in joined and "﻿" not in joined
    assert "didn’t land" in joined


def test_mcp_stdio_utf8_and_leading_bom(tmp_path):
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "t", "version": "0"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "café—tool", "arguments": {}}},
    ]
    data = codecs.BOM_UTF8 + b"\n".join(
        json.dumps(m, ensure_ascii=False).encode("utf-8") for m in msgs) + b"\n"
    env = dict(os.environ, PYTHONPATH=repo)
    out = subprocess.run(
        [sys.executable, "-m", "linafish", "serve", "-n", "enc",
         "--state-dir", str(tmp_path)],
        input=data, capture_output=True, timeout=180, env=env, cwd=repo,
    ).stdout.decode("utf-8")
    replies = {r["id"]: r for r in map(json.loads, filter(str.strip, out.splitlines()))}
    assert 1 in replies, "initialize was dropped"
    assert replies[2]["result"]["content"][0]["text"] == "Unknown tool: café—tool"


# --- the fallback must not be all-or-nothing (Olorina's review of #104) ------

def test_utf8_with_one_stray_byte_stays_utf8(tmp_path):
    # One cp1252 byte dropped into otherwise-UTF-8 writing: before, the whole
    # file became cp1252 and every curly quote/dash/accent was mojibake.
    raw = TEXT.encode("utf-8") + b" stray:\xe9 end"
    out = read_user_text(_write(tmp_path, "a.txt", raw))
    assert "didn’t land" in out and "Café talk —" in out
    assert out.endswith(" stray:� end")


def test_mid_character_truncation_keeps_everything_before_the_cut(tmp_path):
    # listen_folder / watch read files still being appended to; a read that
    # lands mid-write cuts a multibyte character.
    full = "done — café".encode("utf-8")
    cut = full[:-1]  # inside the two bytes of "é"
    assert read_user_text(_write(tmp_path, "a.txt", cut)) == "done — caf"


def test_short_cp1252_ending_in_accent_still_decodes(tmp_path):
    # cp1252 "é" at EOF is byte-identical to a UTF-8 lead byte at EOF; with no
    # real UTF-8 anywhere before it, it is cp1252, not a cut.
    assert read_user_text(_write(tmp_path, "a.txt", "café".encode("cp1252"))) == "café"
    # ...but a two-byte tail (lead + continuation) after ASCII is a cut.
    assert read_user_text(_write(tmp_path, "b.txt", b"done \xe2\x80")) == "done "


def test_jsonl_streams_in_every_encoding(tmp_path):
    from linafish.ingest import read_jsonl
    recs = [{"text": TEXT, "n": i} for i in range(3)]
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n"
    cases = {
        "u8.jsonl": body.encode("utf-8"),
        "bom.jsonl": codecs.BOM_UTF8 + body.encode("utf-8"),
        "u16.jsonl": codecs.BOM_UTF16_LE + body.encode("utf-16-le"),
        "cp.jsonl": body.encode("cp1252"),
    }
    for name, raw in cases.items():
        chunks = read_jsonl(_write(tmp_path, name, raw))
        assert len(chunks) == 3, name
        # read_jsonl re-dumps each record (ensure_ascii), so parse it back.
        assert [json.loads(c.text)["text"] for c in chunks] == [TEXT] * 3, name


def test_csv_streams_with_bom(tmp_path):
    from linafish.ingest import read_csv
    raw = codecs.BOM_UTF8 + ("name,note\nLina,{}\n".format(TEXT)).encode("utf-8")
    chunks = read_csv(_write(tmp_path, "a.csv", raw))
    joined = "".join(c.text for c in chunks)
    assert "didn’t land" in joined and "﻿" not in joined
