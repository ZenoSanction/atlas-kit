"""Atlas Kit - Hermes tools bridge.

Gives Sapphire (the voice) Hermes's own tool code - terminal, files, browser - as its own tools, over a local stdio MCP
connection. Sapphire's model decides every call; Hermes never thinks and never talks to the model itself.

A guard blocks Windows system files, registry changes and credential stores, and hides password-looking lines in
results. The guard is a safety net, NOT a sandbox: the terminal tool runs real commands with your account's rights.
Settings: hermes_tools_config.json next to this file. Run it with Hermes's own Python (it imports Hermes's code):

    Sapphire > Settings > Plugins > MCP Client > + Add Local (stdio)
      Name:      hermes_tools
      Command:   %LOCALAPPDATA%\\hermes\\hermes-agent\\venv\\Scripts\\python.exe   (the full path, typed out)
      Arguments: -I C:\\AtlasKit\\hermes_tools_bridge.py                          (a folder with NO spaces)

MIT License - see LICENSE. Built for the Atlas setup video (Strata + Sapphire + Hermes)."""
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "hermes_tools_config.json"
REDACTED = "[REDACTED]"

# MCP talks over stdout and Hermes's tools print status lines, so everything except MCP goes to stderr.
_mcp_stdout = sys.stdout
sys.stdout = sys.stderr
os.environ.pop("HERMES_INTERACTIVE", None)

CFG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
HERMES = (CFG.get("hermes_dir") or os.environ.get("HERMES_AGENT_DIR")
          or os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", "hermes-agent"))
if not os.path.isdir(HERMES):
    sys.exit(f"Atlas Kit: Hermes not found at {HERMES}. Install Hermes, or set hermes_dir in {CONFIG_PATH.name}.")

# Hermes's own launcher FIRST: its current libraries are built for Hermes's managed Python, not the venv shim Sapphire
# starts us with. hermes_bootstrap relaunches this script on the right Python (stdin/stdout pass straight through) and
# switches Hermes's libraries on. Imported later, mid tool call, it relaunches a half-started server and the tool hangs.
sys.path.insert(0, HERMES)
import hermes_bootstrap  # noqa: E402,F401

import anyio  # noqa: E402
import mcp.types as types  # noqa: E402
from mcp.server.lowlevel import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402

import model_tools  # noqa: E402

os.chdir(os.path.expandvars(CFG.get("start_dir") or str(Path.home() / "Documents")))
# skip_tool_search_assembly: newer Hermes hides less-used tools behind a tool_search helper; we want the full list.
_defs = {d["function"]["name"]: d["function"]
         for d in model_tools.get_tool_definitions(quiet_mode=True, skip_tool_search_assembly=True)}


def _tool(name: str) -> "types.Tool":
    """MCP 2.x names the field input_schema (alias inputSchema); 1.x names it inputSchema."""
    d = _defs[name]
    try:
        return types.Tool(name=name, description=d.get("description", ""), input_schema=d["parameters"])
    except Exception:
        return types.Tool(name=name, description=d.get("description", ""), inputSchema=d["parameters"])


TOOLS = [_tool(n) for n in CFG["tools"] if n in _defs]      # tools this Hermes version doesn't have are skipped
missing = [n for n in CFG["tools"] if n not in _defs]
if missing:
    print(f"Atlas Kit: this Hermes version has no {', '.join(missing)} - skipped", file=sys.stderr)


def _cfg() -> dict:
    global CFG
    try:
        CFG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass  # keep the last good settings if the file is mid-edit
    return CFG


def _log(cfg: dict, tool: str, outcome: str, detail: str):
    try:
        p = Path(os.path.expandvars(cfg.get("log_file") or str(HERE / "logs" / "hermes_tools.log")))
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": datetime.now().isoformat(timespec="seconds"), "tool": tool,
                                "outcome": outcome, "detail": detail[:400]}) + "\n")
    except Exception:
        pass


def _strings(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _strings(v)
    elif value is not None:
        yield str(value)


def _blocked(cfg: dict, args: dict):
    text = re.sub(r"/+", "/", "\n".join(_strings(args)).replace("\\", "/")).lower()
    for group in cfg["blocked"]:
        if any(c.lower() in text for c in group.get("contains", [])):
            return group["why"]
        if any(re.search(r, text, re.I) for r in group.get("regex", [])):
            return group["why"]
    return None


def _mask_text(rx, text: str) -> str:
    out = []
    for line in text.split("\n"):
        m = rx.search(line)
        if not m:
            out.append(line)
            continue
        sep = re.search(r"[=:]", line[m.end():])
        out.append(line[:m.end() + sep.end()] + " " + REDACTED if sep else REDACTED + " (line hidden: looks like a password)")
    return "\n".join(out)


def _mask_value(rx, value):
    if isinstance(value, str):
        return _mask_text(rx, value)
    if isinstance(value, dict):
        return {k: _mask_value(rx, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_value(rx, v) for v in value]
    return value


def _mask(cfg: dict, text: str) -> str:
    """Hide password lines. Hermes returns JSON whose text fields hold many lines, so mask inside each field."""
    rx = re.compile(cfg["secret_line_pattern"])
    try:
        return json.dumps(_mask_value(rx, json.loads(text)), ensure_ascii=False)
    except (ValueError, TypeError):
        return _mask_text(rx, text)


async def run_tool(name: str, arguments: dict) -> list[types.TextContent]:
    cfg = _cfg()
    args = arguments or {}
    why = _blocked(cfg, args)
    if why:
        _log(cfg, name, "blocked", f"{why}: " + json.dumps(args, ensure_ascii=False, default=str))
        return [types.TextContent(type="text", text=f"BLOCKED: that touches {why}, which is off-limits.")]
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(model_tools.handle_function_call, name, args, task_id=cfg.get("task_id", "atlas")),
            timeout=float(cfg["call_timeout_sec"]))
    except asyncio.TimeoutError:
        result = (f"Still running after {cfg['call_timeout_sec']} seconds. For long jobs run the command with "
                  "background=true, then check it with process_manage.")
    except Exception as e:
        result = f"Tool error: {e}"
    text = _mask(cfg, str(result))
    cap = int(cfg["max_result_chars"])
    if len(text) > cap:
        text = text[:cap] + "\n[...cut short]"
    _log(cfg, name, "ran", json.dumps(args, ensure_ascii=False, default=str))
    return [types.TextContent(type="text", text=text)]


# Register the handlers the way the installed MCP library expects: 1.x decorates them onto the server, 2.x passes them
# in when the server is created. Hermes updates its libraries on its own, so support both.
if hasattr(Server, "list_tools"):
    server = Server("hermes_tools")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        return await run_tool(name, arguments)
else:
    async def _on_list_tools(ctx, params) -> "types.ListToolsResult":
        return types.ListToolsResult(tools=TOOLS)

    async def _on_call_tool(ctx, params) -> "types.CallToolResult":
        return types.CallToolResult(content=await run_tool(params.name, params.arguments or {}))

    server = Server("hermes_tools", on_list_tools=_on_list_tools, on_call_tool=_on_call_tool)


async def main():
    from io import TextIOWrapper
    stdin = anyio.wrap_file(TextIOWrapper(sys.stdin.buffer, encoding="utf-8"))
    stdout = anyio.wrap_file(TextIOWrapper(_mcp_stdout.buffer, encoding="utf-8"))
    async with stdio_server(stdin=stdin, stdout=stdout) as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    anyio.run(main)
