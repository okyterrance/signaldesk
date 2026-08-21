"""List the models your TokenRouter key can actually reach.

A 403 saying "this token has no access to model X" means the key is fine
and the slug is not. Guessing replacements wastes runs; the provider will
just tell you. TokenRouter is OpenAI-compatible, so GET /v1/models
returns the list this key is entitled to.

    python scripts/list_models.py

Copy a couple of ids into .env as a comma-separated fallback chain:

    LLM_MODEL_CHAIN=<first choice>,<fallback from a different vendor>
"""
from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("TOKENROUTER_API_KEY", "").strip()
base = os.getenv("TOKENROUTER_BASE_URL", "https://api.tokenrouter.com/v1").rstrip("/")

if not key:
    sys.exit("TOKENROUTER_API_KEY is not set. Put it in .env first.")

try:
    response = httpx.get(
        f"{base}/models",
        headers={"Authorization": f"Bearer {key}"},
        timeout=30,
    )
    response.raise_for_status()
except httpx.HTTPStatusError as exc:
    sys.exit(
        f"HTTP {exc.response.status_code} from {base}/models\n"
        f"{exc.response.text[:600]}"
    )
except Exception as exc:
    sys.exit(f"Could not reach {base}/models — {type(exc).__name__}: {exc}")

payload = response.json()
rows = payload.get("data") or payload.get("models") or []
if not rows:
    print("The endpoint answered but listed no models. Raw response:\n")
    print(str(payload)[:2000])
    sys.exit()

ids = sorted(
    str(row.get("id") or row.get("name") or row)
    for row in rows
)

print(f"\n{len(ids)} models available to this key:\n")
for model_id in ids:
    print(f"  {model_id}")

# Surface the families worth chaining across. A fallback chain is only a
# fallback if the two entries come from different vendors -- two models
# from one provider go down together.
families = {"anthropic": [], "openai": [], "google": [], "deepseek": [], "other": []}
for model_id in ids:
    low = model_id.lower()
    for family in ("anthropic", "openai", "google", "deepseek"):
        if family in low or (family == "anthropic" and "claude" in low) \
                or (family == "openai" and ("gpt" in low or low.startswith("o1"))) \
                or (family == "google" and "gemini" in low):
            families[family].append(model_id)
            break
    else:
        families["other"].append(model_id)

print("\nSuggested cross-family chain for .env:\n")
picks = [v[-1] for v in (families["anthropic"], families["openai"]) if v]
if len(picks) < 2:
    picks = ids[:2]
print(f"  LLM_MODEL_CHAIN={','.join(picks)}\n")
