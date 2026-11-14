"""decide() and propose_correction(). The provider is hidden behind these.

decide() is a pure function of its arguments: no retrieval, no database.
"""
import json
from functools import lru_cache

from . import config
from .prompts import render_memories

# ---------- provider plumbing ----------


@lru_cache
def _anthropic():
    import anthropic
    return anthropic.Anthropic(api_key=config.LLM_API_KEY or None)


@lru_cache
def _openai():
    import openai
    return openai.OpenAI(api_key=config.LLM_API_KEY or None)


def default_model() -> dict:
    return {"provider": config.LLM_PROVIDER, "name": config.LLM_MODEL, "params": {"temperature": 0}}


def _call_tool(system: str, user: str, tools: list[dict], model: dict, force: str | None = None) -> tuple[str, dict]:
    """One forced tool call. force=None means 'any tool'. Returns (tool_name, args)."""
    provider, name = model["provider"], model["name"]
    params = dict(model.get("params") or {})
    if provider == "anthropic":
        kwargs = dict(
            model=name, max_tokens=512, system=system,
            messages=[{"role": "user", "content": user}],
            tools=[{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools],
            tool_choice={"type": "tool", "name": force} if force else {"type": "any"},
        )
        try:
            resp = _anthropic().messages.create(**kwargs, **params)
        except Exception as e:  # some models reject temperature
            if "temperature" not in str(e):
                raise
            resp = _anthropic().messages.create(**kwargs)
        block = next(b for b in resp.content if b.type == "tool_use")
        return block.name, dict(block.input)
    if provider == "openai":
        kwargs = dict(
            model=name,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            tools=[{"type": "function", "function": t} for t in tools],
            tool_choice={"type": "function", "function": {"name": force}} if force else "required",
        )
        try:
            resp = _openai().chat.completions.create(**kwargs, **params)
        except Exception as e:
            if "temperature" not in str(e):
                raise
            resp = _openai().chat.completions.create(**kwargs)
        call = resp.choices[0].message.tool_calls[0]
        return call.function.name, json.loads(call.function.arguments or "{}")
    raise RuntimeError(f"Unsupported LLM_PROVIDER {provider!r} (use 'anthropic' or 'openai')")


# ---------- public API ----------


def decide(system_prompt: str, task: str, memories: list[dict], tools: list[dict], model: dict | None = None) -> dict:
    """memories: [{memory_id, text, ...}] in prompt order. Returns {action, action_args, rationale}."""
    model = model or default_model()
    user = f"Incident:\n{task}\n\n{render_memories(memories)}"
    action, args = _call_tool(system_prompt, user, tools, model)
    rationale = args.pop("rationale", "")
    return {"action": action, "action_args": args, "rationale": rationale}


CORRECTION_TOOL = {
    "name": "submit_review",
    "description": "Report whether the verified evidence contradicts the memory, and draft a corrected memory.",
    "parameters": {
        "type": "object",
        "properties": {
            "contradicts": {"type": "boolean"},
            "reason": {"type": "string", "description": "One or two sentences."},
            "corrected_text": {"type": "string", "description": "Replacement memory text, same style as the original."},
        },
        "required": ["contradicts", "reason", "corrected_text"],
    },
}


def propose_correction(memory_text: str, evidence_text: str, model: dict | None = None) -> dict:
    """Returns {contradicts, reason, corrected_text}. The model only drafts; a human approves."""
    model = model or default_model()
    system = ("You review an AI agent's stored memory against newer, human-verified evidence. "
              "Decide if the evidence contradicts the memory. If so, write a corrected memory.")
    user = f"Memory:\n{memory_text}\n\nVerified evidence:\n{evidence_text}"
    _, args = _call_tool(system, user, [CORRECTION_TOOL], model, force=CORRECTION_TOOL["name"])
    return {"contradicts": bool(args.get("contradicts")), "reason": args.get("reason", ""),
            "corrected_text": args.get("corrected_text", "")}
