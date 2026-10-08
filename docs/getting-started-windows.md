# Your First Ten Minutes — Windows

The same walk as [Getting Started](getting-started.md), in PowerShell, with
the places where Windows differs called out. Every command below was run, in
this order, on a fresh Windows 11 Pro machine with Windows PowerShell 5.1.

## 1. Install

You need a real Python 3.10+. A fresh Windows has a `python.exe` that is only
a Microsoft Store shortcut: running it prints *"Python was not found; run
without arguments to install from the Microsoft Store"*. Install Python
first:

```powershell
winget install --id Python.Python.3.12 -e --source winget
```

`--source winget` matters on some machines: if the Microsoft Store source is
unreachable (a certificate error, `0x8a15005e`), winget refuses to pick a
package until you name a source.

Open a **new** terminal so the new `PATH` takes effect, then:

```powershell
python -m pip install linafish
linafish --version
```

If `linafish` is not found but `python -m linafish --version` works, Python's
`Scripts` folder is not on your `PATH`; see
[Install](../README.md#if-linafish-isnt-found-after-install).

If you use [uv](https://docs.astral.sh/uv/), `uv tool install linafish` puts
`linafish.exe` in `%USERPROFILE%\.local\bin` in its own environment; run
`uv tool update-shell` once and open a new terminal.

## 2. Make a folder of writing

```powershell
mkdir ~\my-writing
Set-Content ~\my-writing\monday.txt -Encoding utf8 "I spent the morning fixing the garden fence. The posts had rotted at the base, so I dug them out and set new ones in gravel. It took longer than I planned, but I like work where you can see the result."
Set-Content ~\my-writing\tuesday.txt -Encoding utf8 "Called my sister about the trip. We keep circling the same question: go in spring when it is cheap, or wait for summer. I want to decide by Friday so we can book the cabin before it fills up."
Set-Content ~\my-writing\wednesday.txt -Encoding utf8 "Read two chapters on river ecology. The part about how floods rebuild the riverbank stayed with me. Damage and repair are the same process seen from different ends."
Set-Content ~\my-writing\thursday.txt -Encoding utf8 "Long day at work. I tried to explain the new schedule to the team and it did not land. Next time I will draw it on the board first and talk second."
```

**Encodings.** Windows tools write text in several encodings: Notepad's
"UTF-8" and PowerShell's `-Encoding utf8` add a byte-order mark, Notepad's
"Unicode" and Windows PowerShell 5.1's `>` write UTF-16, and older files are
often cp1252. LiNafish reads all of these (UTF-8 with or without a BOM,
UTF-16, and cp1252 as the fallback), so files you already have — old
journals, exported notes — can go in as they are.

## 3. Build the fish

```powershell
linafish go ~\my-writing --no-serve
```

The fish is named after the folder (`my-writing`) and lives in
`%USERPROFILE%\.linafish\`. `--no-serve` keeps `go` from starting a server
that holds the terminal until Ctrl+C.

## 4. Ask it things

```powershell
linafish ask "how do I handle things that break" -n my-writing
linafish recall "garden"
linafish check -n my-writing
```

## 5. Feed it one more file

```powershell
Set-Content friday.txt -Encoding utf8 "Booked the cabin for June. Once the decision was made the whole week felt lighter. I notice I carry open questions like weight."
linafish eat friday.txt -n my-writing
```

## 6. Where the fish lives

`%USERPROFILE%\.linafish\` — the same files as listed in
[Getting Started](getting-started.md#6-where-the-fish-lives). `.git` in that
folder is hidden; `Get-ChildItem -Force` shows it.

## 7. Serve it to an AI

```powershell
linafish http -n my-writing
```

From another terminal. In Windows PowerShell 5.1, `curl` is an alias for
`Invoke-WebRequest` and does not take curl's flags, and the real `curl.exe`
mangles the JSON quoting from the bash example. Use PowerShell's own client:

```powershell
Invoke-RestMethod http://127.0.0.1:8900/pfc
Invoke-RestMethod -Method Post http://127.0.0.1:8900/taste -ContentType 'application/json' -Body (@{ text = 'how do I handle things that break'; top = 3 } | ConvertTo-Json)
```

**MCP** (Claude Code): the configuration in
[Getting Started](getting-started.md#7-serve-it-to-an-ai) works unchanged if
`linafish` is on your `PATH`. If the client cannot find it, give the full
path, with forward slashes or doubled backslashes in JSON:

```json
{
  "mcpServers": {
    "linafish": {
      "command": "C:/Users/you/.local/bin/linafish.exe",
      "args": ["serve", "-n", "my-writing"]
    }
  }
}
```

Or register it from the command line: `claude mcp add linafish -- linafish serve -n my-writing`.

## Serving to other machines on your network

`http` binds to `127.0.0.1` only. `converse --bind lan` listens on your LAN
address; Windows Firewall will block it until you allow the port (an
administrator step — Windows asks the first time, or add a rule in
*Windows Defender Firewall → Advanced settings → Inbound Rules*).
