#!/usr/bin/env python3
"""lint-agents.py — check .claude/agents/**/*.md against the Claude Code subagent spec.

Source of the rules: https://code.claude.com/docs/en/sub-agents ("Frontmatter reference",
"Subagent files Claude Code skips", "Preload skills into subagents", "Choose a model").
Claude Code silently ignores unknown fields and silently skips some malformed files, so
this lint makes those failures loud.

Usage: lint-agents.py [AGENTS_DIR] [--gitnexus-version X.Y.Z]
Exit 1 on any ERROR; WARNINGs do not fail. Standard library only.
"""
import re
import sys
from pathlib import Path

FIELDS = {
    "name", "description", "tools", "disallowedTools", "model", "permissionMode",
    "maxTurns", "autoCompactWindow", "skills", "mcpServers", "hooks", "memory",
    "background", "omitClaudeMd", "effort", "isolation", "color", "initialPrompt",
    "experimental",
}
MODELS = {"sonnet", "opus", "haiku", "fable", "inherit"}
COLORS = {"red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"}
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
PERMISSION_MODES = {"default", "manual", "acceptEdits", "auto", "dontAsk", "bypassPermissions", "plan"}
MEMORY = {"user", "project", "local"}
BOOLS = {"true", "false"}
MAX_PRELOADED_SKILLS = 32
DESC_WARN_CHARS = 450  # combined descriptions over 15k tokens trigger a startup warning


def parse_frontmatter(text):
    """Return (dict of top-level key -> scalar str | list[str] | None) or None if no frontmatter.

    Handles the subset agent files use: `key: value`, `key:` followed by `  - item` lists,
    and nested blocks (kept as None, i.e. "present, structured")."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None
    data, key = {}, None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", raw)
        if m and not raw.startswith((" ", "\t")):
            key, val = m.group(1), m.group(2).strip()
            data[key] = val if val else None
            continue
        item = re.match(r"^\s+-\s+(.*)$", raw)
        if key and item and (data[key] is None or isinstance(data[key], list)):
            top = item.group(1).strip()
            if data[key] is None:
                data[key] = []
            # nested mapping items (e.g. mcpServers inline defs) keep only their key
            data[key].append(top[:-1] if top.endswith(":") else top)
    return data


def as_list(val):
    if val is None:
        return []
    if isinstance(val, list):
        return val
    v = val.strip()
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1]
    return [x.strip().strip("'\"") for x in v.split(",") if x.strip()]


def main(argv):
    args = [a for a in argv[1:]]
    gn_version = None
    if "--gitnexus-version" in args:
        i = args.index("--gitnexus-version")
        gn_version = args[i + 1]
        del args[i:i + 2]
    agents_dir = Path(args[0] if args else ".claude/agents")
    skills_dir = agents_dir.parent / "skills"
    errors, warnings, names = [], [], {}

    files = sorted(agents_dir.rglob("*.md")) if agents_dir.is_dir() else []
    for f in files:
        rel = f.as_posix()
        text = f.read_text(errors="ignore")
        fm = parse_frontmatter(text)
        if fm is None:
            if text.lstrip().startswith("---"):
                errors.append(f"{rel}: opening '---' is not the first line, or frontmatter never closes (Claude Code treats the file as documentation)")
            continue  # documentation file: allowed by the spec
        name = (fm.get("name") or "").strip().strip("'\"")
        if not name:
            warnings.append(f"{rel}: no `name` — Claude Code treats this as documentation, not an agent")
            continue
        if name.startswith("-") or ":" in name or len(name) > 256:
            errors.append(f"{rel}: invalid name {name!r} (no leading '-', no ':', <= 256 chars)")
        if name in names:
            errors.append(f"{rel}: duplicate name {name!r} (also {names[name]}); only one loads, in undefined order")
        names[name] = rel
        desc = fm.get("description")
        if not desc:
            errors.append(f"{rel}: `description` missing — Claude Code skips the file")
        elif isinstance(desc, str) and len(desc) > DESC_WARN_CHARS:
            warnings.append(f"{rel}: description is {len(desc)} chars; keep it trigger-focused and move detail into the body")
        for k in fm:
            if k not in FIELDS:
                errors.append(f"{rel}: unknown field `{k}` — Claude Code ignores it silently (fields are camelCase)")
        model = fm.get("model")
        if isinstance(model, str) and model not in MODELS and not model.startswith("claude-"):
            errors.append(f"{rel}: model {model!r} is not an alias ({', '.join(sorted(MODELS))}) or a claude-* ID")
        for field, allowed in (("color", COLORS), ("effort", EFFORTS), ("permissionMode", PERMISSION_MODES), ("memory", MEMORY)):
            v = fm.get(field)
            if isinstance(v, str) and v not in allowed:
                errors.append(f"{rel}: {field} {v!r} not in {sorted(allowed)}")
        for field in ("background", "omitClaudeMd"):
            v = fm.get(field)
            if isinstance(v, str) and v not in BOOLS:
                errors.append(f"{rel}: {field} must be true or false")
        if isinstance(fm.get("isolation"), str) and fm["isolation"] != "worktree":
            errors.append(f"{rel}: isolation must be `worktree`")
        for field in ("maxTurns", "autoCompactWindow"):
            v = fm.get(field)
            if isinstance(v, str) and not v.isdigit():
                errors.append(f"{rel}: {field} must be an integer")
        if "tools" in fm and not as_list(fm.get("tools")):
            errors.append(f"{rel}: `tools` is present but empty — the agent would launch with zero tools")
        skills = as_list(fm.get("skills"))
        if len(skills) > MAX_PRELOADED_SKILLS:
            warnings.append(f"{rel}: {len(skills)} skills listed; only the first {MAX_PRELOADED_SKILLS} preload")
        for s in skills:
            if ":" in s:
                continue  # plugin skill (e.g. modularity:design): resolved by Claude Code at runtime
            sk = skills_dir / s / "SKILL.md"
            if sk.is_file() and re.search(r"^disable-model-invocation:\s*true\s*$", sk.read_text(errors="ignore"), re.M):
                errors.append(f"{rel}: skill `{s}` sets disable-model-invocation: true and cannot be preloaded")
        if gn_version:
            for pin in re.findall(r"gitnexus@([0-9][^\s\"'\]]*)", text):
                if pin != gn_version:
                    errors.append(f"{rel}: gitnexus@{pin} does not match the locked gitnexus_version {gn_version}")

    for w in warnings:
        print("WARNING " + w)
    for e in errors:
        print("ERROR " + e)
    print(f"lint-agents: {len(names)} agent(s) in {agents_dir}: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
