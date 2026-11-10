# Atlas Kit

Build **Atlas**: a voice assistant with a 125-billion-parameter brain that runs entirely on one gaming PC. No cloud, no
subscription. He listens, talks back, remembers, and does real work on your PC: runs commands, reads and writes files,
and browses the web.

Atlas is three free, open-source programs working as one assistant, plus the small pieces in this kit that join them:

| Part | Program | Job |
| --- | --- | --- |
| Brain | [Strata](https://github.com/Niko1221/Strata) | runs the 125B model (Qwen3.8-Flash-Next) on your GPU + RAM |
| Voice and memory | [Sapphire](https://github.com/ddxfish/sapphire) | listens (Whisper), talks (Kokoro), remembers, uses tools |
| Hands | [Hermes Agent](https://hermes-agent.nousresearch.com) | its tool code: terminal, files, web browser |
| **This kit** | | the bridge that gives Sapphire Hermes's tools, the Atlas persona, and a one-click start file |

This kit goes with the video **["Build Atlas: a complete local AI assistant on your gaming PC"](https://www.youtube.com/watch?v=MpHyj0t5M2o)**. Every step below is
shown in it.

## What's in the kit

| File | What it does |
| --- | --- |
| `hermes_tools_bridge.py` | Gives Sapphire Hermes's tools (terminal, files, browser) over a local MCP connection. Atlas decides every call; Hermes itself never thinks. |
| `hermes_tools_config.json` | The bridge's settings: which tools, the guard (blocked places), password masking, log file. |
| `atlas_persona_prompt.txt` | Atlas's system prompt: who he is, how he speaks, memory, tool rules, honesty rules. |
| `Start-Atlas.bat` | One-click start in the right order: Strata, then Sapphire, then the browser. |

## What you need

- **Graphics card:** NVIDIA RTX 20, 30, 40 or 50 series (or a supported AMD Radeon), **12 GB of VRAM or more**.
- **RAM:** 64 GB runs every model size. 32-48 GB runs the smaller sizes. RAM matters more than the graphics card.
- **Disk:** about 80 GB free, on an SSD.
- **Windows 10 or 11** and a current graphics driver.

## Setup

### 1. Strata (the brain)

1. Download Strata from its GitHub page (Code, Download ZIP) and unzip it, for example to `C:\Strata`.
2. Double-click **`START-HERE.bat`**. Press Enter for the recommended answers. The choices that matter:
   - **Model size:** 64 GB of RAM: **IQ3_XXS** (what Atlas runs) or **IQ2_XS** (faster, Strata's own pick for 64 GB).
     32-48 GB: Q2_0 or IQ2_XS.
   - **Context:** keep **64K**.
3. It downloads about 75 GB. The first start can freeze your PC for 1-3 minutes. That's normal.
4. Leave room on the graphics card for Sapphire (2.5 GB). Close Strata's window, then run this once in the Strata
   folder (Strata remembers it):

   ```
   START-HERE.bat --vram-reserve-mib 2560
   ```

5. Open `C:\Strata\strata-<your size>.json` in Notepad and add this line after the first `{`, then restart Strata:

   ```
   "fit_max_tokens": true,
   ```

   It stops "context too long" errors in long chats by shortening the answer instead of failing.
6. Test it: open `http://127.0.0.1:8080` and chat with it.

Leave Strata's `parallel` setting alone. With this kit only Sapphire talks to Strata, and a second slot costs 10-25%
speed on a 12 or 16 GB card.

### 2. Sapphire (the voice)

1. Easiest: [Sapphire Launcher](https://github.com/ddxfish/sapphire-launcher/releases). Run it, click **Scan System**,
   then **Go**, then **Launch** and **Open Browser**.
2. Open `https://localhost:8073`. Your browser warns about the certificate: click **Advanced**, then **Proceed**.
3. Create a password (10+ characters) and finish the setup wizard. Skip its model step.

### 3. Connect the voice to the brain

**Settings > LLM > Add Provider > Manual: OpenAI Compatible:**

| Field | Value |
| --- | --- |
| Name | `Strata` |
| Base URL | `http://127.0.0.1:8080/v1` (the numbers, not `localhost`: faster on Windows) |
| API key | empty (unless you gave Strata a key) |
| Model | the exact name Strata shows, for example `qwen3.8-flash-next-iq3_xxs` |
| Local server | on |
| Max tokens | `8192` |
| Disable thinking | **off** |
| Extra body (Advanced) | `{"reasoning_effort": "low", "reasoning_budget_tokens": 3072}` |

Click **Add**, then **Test**. Drag Strata to the top of the list and set its health timeout to **2** seconds.
In the **General** tab set **Context limit** to **24000**.

Why low thinking, not off: a little thinking makes Atlas choose and order tools well. Too small a budget (1,024) cut
his thinking off mid-plan, and he then described planned work as done. 3,072 thinking tokens inside an 8,192 answer
fixed it. Why 24,000: Sapphire's trim counts message text, not the tool list, so 32,000 overflowed Strata's 64K window
once the tools were added.

### 4. Voice settings

| Where | Setting | Value |
| --- | --- | --- |
| Settings > TTS | Kokoro device | `cpu` (restart Sapphire after) |
| Settings > TTS | Primary and fallback TTS server | `http://127.0.0.1:5012` |
| Settings > TTS | Streaming split mode | `sentence` |
| Settings > STT | Model size | `small.en` |
| Chat sidebar > voice | Voice / speed | `bm_george` / `1.0` |
| Settings > Wakeword | Wake word | on (it listens for "Hey Sapphire") |
| Settings > Conversation | Conversation start words | `atlas, hey atlas, okay atlas` |

Voice on the CPU matters: on the GPU, Kokoro slowly grows until it pushes Strata out of video memory, and speed falls
from about 74 to 30 tokens a second. On the CPU it costs almost nothing.

### 5. Hermes (the hands)

Install Hermes with its one-line installer in PowerShell. The bridge needs this install:

```
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

You don't have to use the Hermes app itself: the bridge runs its tools inside Sapphire. If you also want the Hermes
app on the same brain, point it at Strata:

```
hermes config set model.provider custom
hermes config set model.base_url http://127.0.0.1:8080/v1
hermes config set model.default qwen3.8-flash-next-iq3_xxs
```

(Use your own model name from step 3. If you gave Strata an API key: `hermes config set model.api_key YOUR_KEY`.)

### 6. Give Atlas his hands (this kit)

1. Put this kit in **`C:\AtlasKit`**. The path must have **no spaces**: Sapphire splits the arguments on spaces.
2. Sapphire: **Settings > Plugins**, enable **MCP Client**. Then **Settings > Plugins > MCP Client > + Add Local (stdio)**:

   | Field | Value |
   | --- | --- |
   | Name | `hermes_tools` |
   | Command | `C:\Users\YOUR NAME\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe` (spaces are fine here) |
   | Arguments | `-I C:\AtlasKit\hermes_tools_bridge.py` |

3. Click **Connect**. You should see a green dot and **7 tools**: terminal, process_manage, read_file, write_file,
   patch, search_files, browser_exec.

### 7. Make him Atlas

1. **Prompts:** create a prompt named `atlas_kit` and paste in `atlas_persona_prompt.txt`.
2. **Toolsets:** create a toolset named `atlas_kit`. Turn on the 7 `mcp:hermes_tools` tools plus Sapphire's memory
   and knowledge tools (save_memory, search_memory, delete_memory, save_knowledge, search_knowledge,
   delete_knowledge), web_search, set_alarm, schedule_task and reset_chat: 17 tools in all.
3. **Personas:** create a persona named `Atlas Kit` (Sapphire stores it as `atlas_kit`): prompt `atlas_kit`, toolset
   `atlas_kit`, voice `bm_george`, LLM `Strata`, date and time on. Make it your default persona.
4. **Settings > Tools:** max tool iterations `25`. (The bridge already keeps each tool result under 8,000 characters.)

### 8. Every day

Double-click **`Start-Atlas.bat`**. It starts Strata first, waits for it, then Sapphire, then opens Atlas in your browser.
To shut down: close the Sapphire window first, then Strata's.

If it can't find Sapphire, open `Start-Atlas.bat` in Notepad and set `SAPPHIRE_DIR` (the folder with Sapphire's
`main.py`) and `SAPPHIRE_PY` (the `python.exe` of Sapphire's environment) at the top.

It opens Atlas in your default browser. To pick one, set `BROWSER` at the top of `Start-Atlas.bat` to `msedge`,
`chrome` or `firefox`. Browsers can use a lot of memory, and memory is what Strata needs most, so keep it to Atlas's
one tab.

## Safety: read this

- The **terminal** tool runs real commands on your PC with your account's rights. The guard blocks Windows system files,
  registry changes and the usual password stores, and hides password-looking lines, but it is a **safety net, not a
  sandbox**.
- Atlas's prompt tells him to ask before deleting, installing, changing settings, spending or posting anything.
- Every tool call is logged in `C:\AtlasKit\logs\hermes_tools.log`, including blocked ones.
- Don't want him running commands? Remove `terminal` and `process_manage` from `hermes_tools_config.json`, then click
  the reconnect button in MCP Client.
- Add your own folders with passwords or keys to the `stored passwords and keys` list in `hermes_tools_config.json`.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| The Hermes app says the model can't do tool calls | Run the three `hermes config set` commands in step 5. Then check `curl.exe http://127.0.0.1:8080/props` (add `-H "Authorization: Bearer YOUR_KEY"` if you set a key): under `chat_template_caps`, `supports_tools` and `supports_tool_calls` must be `true`. If not, run Strata's `UPDATE.bat`. |
| The model writes a tool call as text instead of running it | Add `"tool_call_recovery": true,` to `strata-<size>.json` and restart Strata. |
| hermes_tools shows a red dot | Check the Command path to Hermes's `python.exe`, and that the kit is in a folder with no spaces. Click reconnect. |
| Atlas doesn't use his tools | **Toolsets:** turn the `mcp:hermes_tools` tools on in the `atlas_kit` toolset, and check the Atlas Kit persona uses it. |
| A tool "is still running" | Sapphire stops every tool after 30 seconds. Ask Atlas to run long jobs in the background. |
| Speed drops to ~30 tokens a second | Something else is using the graphics card: Kokoro on the GPU (set it to cpu), or a game. |
| Strata stops, or "out of memory" | Close your browser, Discord and games: RAM is the real limit. Set the Windows page file to a fixed size, such as 64 GB. |
| Context too long errors | Sapphire context limit 24000, and `"fit_max_tokens": true` in Strata's config. |

## Credits and license

Strata, Sapphire and Hermes Agent belong to their authors; this kit only connects them. The kit itself is MIT
licensed: see `LICENSE`.
