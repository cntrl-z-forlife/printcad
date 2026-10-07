# printcad

CLI harness: natural language → **build123d** script + named parameters → **STEP** for Fusion 360.

The solid is not the source of truth. `params.json` and `model.py` are. Second-take edits change those and rebuild.

## Prompt-only runs

Paste an OpenRouter key into `printcad.toml` (gitignored; start from `printcad.toml.example`). That file also lists the free models a run will try, in order.

```bash
chmod +x printcad.sh
./printcad.sh "FDM L-bracket 80x60 mm, 5 mm thick, two M4 clearance holes per leg"
./printcad.sh "make the holes 3.5 mm and add a 1 mm fillet on the inner corner"
```

The first prompt creates `session/` and generates a part. A later prompt edits that same session. No provider flags. If a model rate-limits, times out, returns an upstream overload, or never calls a tool, the next model in `printcad.toml` is tried. A previous inspect does not count as success for the failed model. Session files are restored before the next try.

Models shipped in the example (OpenRouter catalog, 2026-10-07, tool calling, free):

- `nvidia/nemotron-3-ultra-550b-a55b:free`
- `nvidia/nemotron-3-super-120b-a12b:free`
- `cohere/north-mini-code:free`
- `poolside/laguna-s-2.1:free`
- `google/gemma-4-31b-it:free`
- `openrouter/free` (last; routes to whatever free tool-capable model is up)

`assume_defaults = true` so `ask_user` does not stop a script run. Set it false in the toml if you want the prompts.

## Run (conda, no package install)

Dependencies live in the env. The CLI is this folder, not a pip console script.

```bash
conda activate printcad
pip install 'build123d>=0.8' 'httpx>=0.27' 'pydantic>=2'   # once per env

chmod +x printcad.sh
./printcad.sh doctor          # must print this folder's printcad/__init__.py
./printcad.sh "FDM plate 80x50x4 mm with 4x M4 holes"
```

`printcad.sh` prepends its own directory to `PYTHONPATH` and runs `python -m printcad`. A bare prompt becomes `run`. Replacing the folder is the update. Do not `pip install printcad`.

If an old `printcad` command is still on PATH:

```bash
pip uninstall printcad
hash -r
which printcad || true
```

Optional alias in `~/.bashrc` / `~/.zshrc`:

```bash
alias printcad="$HOME/Downloads/printcad/printcad.sh"
```

Override the interpreter with `PRINTCAD_PYTHON=/path/to/python` if needed.

## Providers

```bash
printcad providers
```

| Flag | Env | Default model |
|---|---|---|
| `--provider openai` | `OPENAI_API_KEY` | `gpt-4.1` |
| `--provider anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-5` |
| `--provider google` | `GEMINI_API_KEY` | `gemini-2.5-pro` |
| `--provider xai` | `XAI_API_KEY` | `grok-4` |
| `--provider openrouter` | `OPENROUTER_API_KEY` or `printcad.toml` | models listed in the toml |
| `--provider ollama` | optional `OLLAMA_HOST` | `llama3.1` |
| `--provider compatible --base-url URL` | `PRINTCAD_API_KEY`, `PRINTCAD_BASE_URL` | any OpenAI-compatible server |

Aliases: `claude`, `gemini`, `grok`.

```bash
export PRINTCAD_PROVIDER=anthropic
export ANTHROPIC_API_KEY=...
# or
printcad new "..." --provider openai --model gpt-4.1
```

## Use

```bash
mkdir my-bracket && cd my-bracket
printcad init

printcad new "FDM L-bracket 80x60 mm, 5 mm thick, two M4 clearance holes per leg"

printcad status
# open out/part.step in Fusion

printcad edit "make the holes 3.5 mm and add a 1 mm fillet on the inner corner"
printcad rebuild          # no LLM, just rerun model.py
printcad preview          # out/preview.svg and out/preview.html from the STEP
printcad revert           # last inspect-ok snapshot
```

`out/preview.svg` is top / front / right. `out/preview.html` is a drag-to-orbit mesh in the browser. Both are written next to `out/part.step` on a successful export.

Session files:

```
printcad.json
prompt.txt        # last new/edit request; inspect compares STEP to this
spec.json
params.json
model.py          # must define build(params)
history.jsonl
out/part.step
out/report.json   # includes extras.prompt_check
out/last_good/    # revert target
```

`inspect` is not only “is it a solid.” It also diffs the STEP against the prompt: expected through-hole count and diameter, thickness, envelope, and named plan sizes in `params.json`. A watertight L-bracket with two holes fails if the request said two holes *per leg*.

`model.py` contract:

```python
from build123d import *

def build(params: dict):
    length = params["length"]
    ...
    return part.part
```

Every dimension belongs in `params.json`. The agent is instructed to use `set_params` for size tweaks and `apply_patch` for small feature changes.

## Notes

- STEP only. Use Fusion for 3MF/STL and finishing.
- Generated scripts run in a subprocess with a timeout.
- Default envelope / wall rules are prompt-level, not a full DFM solver.
- Tool-calling models work best. Local models on `ollama` need a tool-capable tag.
