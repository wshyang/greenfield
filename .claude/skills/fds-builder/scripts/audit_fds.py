#!/usr/bin/env python3
"""Deterministic static auditor and PostToolUse validator for the fds-builder skill.

Modes:
  1. Hook Mode (no CLI args; JSON piped on stdin by Claude Code PostToolUse on Edit|Write):
     Runs <40ms phase-invariant checks on FDS markdown files:
       - D15: Zero diagrams (mermaid/plantuml/graphviz/d2 fences, Unicode box-drawing, ASCII box-arrows)
       - D16: Zero language-specific implementation code fences (python/ts/js/go/rust/sql/java/etc.)
       - D1:  No bare [DRAFT] tags missing provenance source ('[DRAFT — <source>]' required)
       - D7:  No [CUSTOM: ...] tags missing 'because <reason>' rationale

  2. CLI Gate Mode (`audit-fds.sh <spec.md> --phase <intake|scaffold|deep-dive-plan|r5-parity|review|finalize>`):
       - intake:         Inventory anchors, objects, surfaces, features, and [DRAFT] count
       - scaffold:       Verify lineup sections, D3 6-col attributes, D4 state/forbidden tables,
                         D5 relationship map, R1 pass 1, D20 empty states, P5 single-phase features,
                         BDD Given/When/Then, SEC/PERF/LOG archetypes, and R4 Day-Zero bootstrap draft
       - deep-dive-plan: Compute deterministic Weakness Scores (DRAFT_count * section_weight)
       - r5-parity:      Verify R1 4-surface junction coverage, R2 IFF authz chains, R3 on_delete rules,
                         R4 bootstrap surface resolution, 6-category + R8 object sweeps,
                         0 [BLOCKED], and 0 [ORPHAN-CAPABILITY] against Section 8 Surface Inventory
       - review:         Emit filtered Draft-Only Sweep report (§4.4)
       - finalize:       Full 16-section canonical order, 0 raw [DRAFT], 0 <placeholders>,
                         0 broken #anchors, SCALE numeric check (§7.3), PRIV-2+ PII table (§7.4),
                         OBS-2+ component table (§7.4), TOC/Metadata/Changelog checks, and banned fluff scan
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

DIAGRAM_FENCES = {"mermaid", "plantuml", "puml", "graphviz", "dot", "d2", "nomnoml", "pikchr", "kroki"}

CODE_LANG_FENCES = {
    "python",
    "py",
    "javascript",
    "js",
    "typescript",
    "ts",
    "tsx",
    "jsx",
    "go",
    "golang",
    "rust",
    "rs",
    "java",
    "kotlin",
    "swift",
    "csharp",
    "cs",
    "c",
    "cpp",
    "ruby",
    "php",
    "sql",
    "bash",
    "sh",
    "zsh",
    "scala",
    "elixir",
}

CANONICAL_H2_ORDER = [
    ("metadata", "Document Metadata"),
    ("toc", "Table of Contents"),
    ("executive-summary", "Executive Summary"),
    ("phase-scope", "Phase Scope"),
    ("core-objects", "Core Objects"),
    ("relationship-map", "Relationship Map"),
    ("cross-object-constraints", "Cross-Object Constraints"),
    ("surface-inventory", "Surface Inventory"),
    ("features", "Features"),
    ("user-flows", "User Flows"),
    ("day-zero-bootstrap", "Day-Zero Bootstrap"),
    ("integrations", "Integrations"),
    ("nfr", "Non-Functional Requirements"),
    ("anti-patterns", "Anti-Pattern"),
    ("changelog", "Changelog"),
    ("appendices", "Appendices"),
]

BANNED_FLUFF_PATTERNS = [
    (r"\bmust\s+scale\b", "Banned vague scalability phrase 'must scale' (§7.3); use numeric RPS/TPS, burst, and concurrency targets."),
    (r"\bhighly\s+scalable\b", "Banned vague phrase 'highly scalable' (§7.3); specify quantitative SCALE-1..5 metrics."),
    (r"\b(?:stays|remains)\s+logged\s+in\b", "Banned vague phrase 'stays/remains logged in' (§6.7); specify R7 Session Continuity contract."),
    (r"\b(?:handle|fail)\s+gracefully\b", "Banned vague phrase 'handle/fail gracefully' (MUST NOT #6); specify exact status, rollback, and user error copy."),
    (r"\bappropriate\s+error(?:\s+message)?\b", "Banned vague phrase 'appropriate error message' (D3); provide verbatim user-facing error copy."),
    (r"\bseamless(?:ly)?\b", "Banned marketing fluff 'seamless' (MUST NOT #6); specify deterministic steps or latency targets."),
    (r"\buser-friendly\b", "Banned marketing fluff 'user-friendly' (MUST NOT #6); specify concrete A11Y or UX behavior."),
    (r"\bintuitive(?:\s+interface|\s+ui)?\b", "Banned marketing fluff 'intuitive' (MUST NOT #6); specify explicit controls and states."),
    (r"\bas\s+needed\b", "Banned ambiguous condition 'as needed' (MUST NOT #6); state an explicit IF/WHEN predicate."),
]

SEMANTIC_ANCHOR_RE = re.compile(r"#(?:obj|feat|surf|flow|int|nfr|boot|cstr|ap)-[a-z0-9][a-z0-9-]*")
LINK_ANCHOR_RE = re.compile(r"\]\((#[a-z0-9][a-z0-9-]*)\)")
EXPLICIT_HEADER_ANCHOR_RE = re.compile(r"\{#(sec-[a-z0-9-]+|(?:obj|feat|surf|flow|int|nfr|boot|cstr|ap)-[a-z0-9-]+|[a-z0-9-]+)\}")
HTML_ANCHOR_RE = re.compile(r'<a\s+(?:id|name)=["\']([a-z0-9-]+)["\']', re.I)


def strip_inline_backticks(line: str) -> str:
    return re.sub(r"`[^`]*`", "", line)


def slugify_heading(title: str) -> str:
    cleaned = re.sub(r"\{#[^}]+\}", "", title).strip().lower()
    cleaned = re.sub(r"[^\w\s-]", "", cleaned)
    cleaned = re.sub(r"[\s]+", "-", cleaned).strip("-")
    return f"#{cleaned}" if cleaned else ""


def classify_h2_key(heading_text: str) -> Optional[str]:
    low = heading_text.lower()
    if "metadata" in low:
        return "metadata"
    if "table of contents" in low or re.search(r"\btoc\b", low):
        return "toc"
    if "executive summary" in low:
        return "executive-summary"
    if "phase scope" in low:
        return "phase-scope"
    if "core object" in low:
        return "core-objects"
    if "relationship map" in low:
        return "relationship-map"
    if "cross-object" in low:
        return "cross-object-constraints"
    if "surface inventory" in low:
        return "surface-inventory"
    if re.search(r"\bfeatures\b", low):
        return "features"
    if "user flow" in low:
        return "user-flows"
    if "bootstrap" in low:
        return "day-zero-bootstrap"
    if "integration" in low or "migration" in low:
        return "integrations"
    if "non-functional" in low or re.search(r"\bnfr\b", low):
        return "nfr"
    if "anti-pattern" in low:
        return "anti-patterns"
    if "changelog" in low:
        return "changelog"
    if "appendices" in low or "appendix" in low:
        return "appendices"
    return None


def parse_markdown_tables(lines: List[str], start_line: int = 1) -> List[Dict[str, Any]]:
    """Extract pipe tables with header cells, rows, and 1-based line numbers."""
    tables: List[Dict[str, Any]] = []
    in_fence = False
    i = 0
    n = len(lines)
    while i < n:
        stripped = lines[i].strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence:
            i += 1
            continue
        if stripped.startswith("|") and stripped.endswith("|") and i + 1 < n:
            sep = lines[i + 1].strip()
            if sep.startswith("|") and re.match(r"^\|[\s:\-\|]+\|$", sep):
                headers = [c.strip() for c in stripped.strip("|").split("|")]
                rows = []
                j = i + 2
                while j < n:
                    row_str = lines[j].strip()
                    if row_str.startswith("|") and row_str.endswith("|"):
                        cells = [c.strip() for c in row_str.strip("|").split("|")]
                        rows.append({"line": start_line + j, "cells": cells, "raw": lines[j]})
                        j += 1
                    else:
                        break
                tables.append({"header_line": start_line + i, "headers": headers, "rows": rows})
                i = j
                continue
        i += 1
    return tables


def check_fast_invariants(lines: List[str], rel: str) -> List[str]:
    """Phase-invariant checks safe for both PostToolUse hook and CLI gates."""
    issues: List[str] = []
    in_fence = False
    in_conventions = False
    ascii_box_lines = 0

    for idx, raw_line in enumerate(lines, 1):
        stripped = raw_line.strip()
        if stripped.startswith("## ") or stripped.startswith("### "):
            low_h = stripped.lower()
            in_conventions = "tag & anchor conventions" in low_h or "document tag conventions" in low_h

        if stripped.startswith("```"):
            if not in_fence:
                in_fence = True
                lang = stripped[3:].strip().split()[0].lower() if stripped[3:].strip() else ""
                if lang in DIAGRAM_FENCES:
                    issues.append(f"{rel}:{idx}: Diagram block '```{lang}' violates D15 (zero diagrams of any kind).")
                elif lang in CODE_LANG_FENCES:
                    issues.append(
                        f"{rel}:{idx}: Language-specific code block '```{lang}' violates D16 / MUST NOT #5 "
                        "(use prose, tables, or '```pseudocode' only)."
                    )
            else:
                in_fence = False
            continue

        # Check Unicode box-drawing art (D15)
        if re.search(r"[\u2500-\u257f]", raw_line):
            issues.append(f"{rel}:{idx}: Unicode box-drawing character violates D15 (no ASCII/Unicode visual diagrams).")

        # Check multi-line ASCII box-and-arrow diagrams like +----+ and --->
        if re.search(r"\+-\-+.*\+", raw_line) or (re.search(r"\|[^|]+\|", raw_line) and ("-->" in raw_line or "<--" in raw_line)):
            if not stripped.startswith("|"):
                ascii_box_lines += 1
                if ascii_box_lines >= 2:
                    issues.append(f"{rel}:{idx}: ASCII box-and-arrow diagram violates D15 (use tables or numbered steps).")
                    ascii_box_lines = -100  # report once

        if in_fence or in_conventions:
            continue

        unquoted = strip_inline_backticks(raw_line)

        # Bare [DRAFT] without '— <source>' or 'ACCEPTED-AS-DRAFT'
        for m in re.finditer(r"\[DRAFT(?:\s*([^\]]*))?\]", unquoted):
            suffix = (m.group(1) or "").strip()
            if not (suffix.startswith("—") or suffix.startswith("-") or suffix.startswith(":")):
                issues.append(
                    f"{rel}:{idx}: Bare '[DRAFT]' tag violates D1; include provenance source as '[DRAFT — {{source}}]'."
                )

        # [CUSTOM: ...] without 'because'
        for m in re.finditer(r"\[CUSTOM\s*:([^\]]+)\]", unquoted):
            body = m.group(1)
            if "because" not in body.lower():
                issues.append(
                    f"{rel}:{idx}: '[CUSTOM: ...]' tag is missing mandatory 'because <rationale>' clause (MUST #13, D7)."
                )

    return issues


def split_h2_sections(lines: List[str]) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    cur: Optional[Dict[str, Any]] = None
    in_fence = False
    for idx, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            if cur is not None:
                cur["end_line"] = idx - 1
                sections.append(cur)
            heading = line[3:].strip()
            cur = {
                "heading": heading,
                "key": classify_h2_key(heading),
                "start_line": idx,
                "end_line": len(lines),
                "lines": [line],
            }
        elif cur is not None:
            cur["lines"].append(line)
    if cur is not None:
        sections.append(cur)
    return sections


def split_h3_blocks(sec_lines: List[str], sec_start_line: int) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    cur: Optional[Dict[str, Any]] = None
    in_fence = False
    for offset, line in enumerate(sec_lines):
        lineno = sec_start_line + offset
        if line.strip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("### "):
            if cur is not None:
                blocks.append(cur)
            heading = line[4:].strip()
            anc_m = EXPLICIT_HEADER_ANCHOR_RE.search(heading)
            anchor = f"#{anc_m.group(1)}" if anc_m else None
            cur = {"heading": heading, "anchor": anchor, "start_line": lineno, "lines": [line]}
        elif cur is not None:
            cur["lines"].append(line)
    if cur is not None:
        blocks.append(cur)
    return blocks


def extract_defined_and_referenced_anchors(lines: List[str], sections_by_key: Dict[str, Dict[str, Any]]) -> Tuple[Set[str], List[Tuple[int, str]]]:
    defined: Set[str] = set()
    referenced: List[Tuple[int, str]] = []
    in_fence = False
    in_conventions = False

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if re.match(r"^#{1,6}\s+", stripped):
            low_h = stripped.lower()
            in_conventions = "tag & anchor conventions" in low_h or "document tag conventions" in low_h
            for m in EXPLICIT_HEADER_ANCHOR_RE.finditer(stripped):
                defined.add(f"#{m.group(1)}")
            slug = slugify_heading(re.sub(r"^#+\s+", "", stripped))
            if slug:
                defined.add(slug)

        for m in HTML_ANCHOR_RE.finditer(line):
            defined.add(f"#{m.group(1)}")

        if in_conventions:
            continue

        for m in LINK_ANCHOR_RE.finditer(line):
            referenced.append((idx, m.group(1)))

        for m in SEMANTIC_ANCHOR_RE.finditer(line):
            referenced.append((idx, m.group(0)))

    # Table-defined anchors in Surface Inventory (#surf-*), Day-Zero Bootstrap (#boot-*), Anti-Patterns (#ap-*)
    for sec_key, prefix in (
        ("surface-inventory", "#surf-"),
        ("day-zero-bootstrap", "#boot-"),
        ("anti-patterns", "#ap-"),
    ):
        sec = sections_by_key.get(sec_key)
        if not sec:
            continue
        for tbl in parse_markdown_tables(sec["lines"], sec["start_line"]):
            for row in tbl["rows"]:
                for cell in row["cells"]:
                    for m in SEMANTIC_ANCHOR_RE.finditer(cell):
                        if m.group(0).startswith(prefix):
                            defined.add(m.group(0))

    return defined, referenced


def extract_active_tags(lines: List[str]) -> Dict[str, List[Tuple[int, str]]]:
    tags: Dict[str, List[Tuple[int, str]]] = {
        "draft": [],
        "accepted_draft": [],
        "blocked": [],
        "orphan": [],
        "custom": [],
    }
    in_fence = False
    in_conventions = False
    for idx, raw_line in enumerate(lines, 1):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("## ") or stripped.startswith("### "):
            low_h = stripped.lower()
            in_conventions = "tag & anchor conventions" in low_h or "document tag conventions" in low_h
        if in_conventions:
            continue

        unquoted = strip_inline_backticks(raw_line)
        for m in re.finditer(r"\[DRAFT\s*(?:[—\-:]\s*([^\]]+))?\]", unquoted):
            tags["draft"].append((idx, m.group(0)))
        for m in re.finditer(r"\[ACCEPTED-AS-DRAFT\][^\n]*", unquoted):
            tags["accepted_draft"].append((idx, m.group(0).strip()))
        for m in re.finditer(r"\[BLOCKED[^\]]*\]", unquoted):
            tags["blocked"].append((idx, m.group(0)))
        for m in re.finditer(r"\[ORPHAN-CAPABILITY[^\]]*\]", unquoted):
            tags["orphan"].append((idx, m.group(0)))
        for m in re.finditer(r"\[CUSTOM\s*:[^\]]+\]", unquoted):
            tags["custom"].append((idx, m.group(0)))
    return tags


def load_optional_ledger(ledger_arg: Optional[str]) -> Optional[Dict[str, Any]]:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "") or os.getcwd()).resolve()
    if ledger_arg:
        p = Path(ledger_arg)
        target = p if p.is_absolute() else (root / p).resolve()
        if target.is_file():
            return json.loads(target.read_text(encoding="utf-8"))
        return None
    pointer = root / ".fds-state" / "active.json"
    if pointer.is_file():
        try:
            meta = json.loads(pointer.read_text(encoding="utf-8"))
            lp = Path(meta.get("ledger_path", ""))
            if lp.is_file():
                return json.loads(lp.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def audit_surface_inventory(sections_by_key: Dict[str, Dict[str, Any]], rel: str) -> Tuple[Set[str], Dict[str, Set[str]], Set[str], List[str]]:
    """Returns (defined_surfaces, obj_to_ops, listable_objs, issues)."""
    issues: List[str] = []
    defined_surfs: Set[str] = set()
    obj_to_ops: Dict[str, Set[str]] = {}
    listable_objs: Set[str] = set()

    sec = sections_by_key.get("surface-inventory")
    if not sec:
        issues.append(f"{rel}: Missing mandatory Section 8 'Surface Inventory' (§9.4).")
        return defined_surfs, obj_to_ops, listable_objs, issues

    tables = parse_markdown_tables(sec["lines"], sec["start_line"])
    if not tables:
        issues.append(f"{rel}:{sec['start_line']}: Section 8 'Surface Inventory' has no markdown checklist table (§9.4).")
        return defined_surfs, obj_to_ops, listable_objs, issues

    tbl = tables[0]
    hdr_low = [h.lower() for h in tbl["headers"]]
    if len(hdr_low) < 7 or "anchor" not in " ".join(hdr_low) or "phase" not in " ".join(hdr_low):
        issues.append(
            f"{rel}:{tbl['header_line']}: Surface Inventory header must follow 7-column contract "
            "'# | Surface | Anchor | Permitted Roles | Target Object / Relationship | CRUD / Associate | Phase' (§9.4)."
        )

    for row in tbl["rows"]:
        cells = row["cells"]
        if len(cells) < 7:
            issues.append(f"{rel}:{row['line']}: Surface Inventory row has fewer than 7 columns.")
            continue
        surf_anchors = [m.group(0) for m in SEMANTIC_ANCHOR_RE.finditer(cells[2]) if m.group(0).startswith("#surf-")]
        if not surf_anchors:
            issues.append(f"{rel}:{row['line']}: Surface Inventory Anchor column must define a '#surf-*' anchor.")
        for sa in surf_anchors:
            if sa in defined_surfs:
                issues.append(f"{rel}:{row['line']}: Duplicate surface anchor '{sa}' in Surface Inventory.")
            defined_surfs.add(sa)

        ops_low = cells[5].lower()
        target_objs = [m.group(0) for m in SEMANTIC_ANCHOR_RE.finditer(cells[4]) if m.group(0).startswith("#obj-")]
        for ob in target_objs:
            bucket = obj_to_ops.setdefault(ob, set())
            if "create" in ops_low:
                bucket.add("create")
            if "read" in ops_low or "list" in ops_low or "view" in ops_low or "search" in ops_low:
                bucket.add("read")
            if "list" in ops_low or "search" in ops_low or "inverse" in ops_low:
                listable_objs.add(ob)
            if "update" in ops_low or "edit" in ops_low or "transition" in ops_low:
                bucket.add("update")
            if "delete" in ops_low or "remove" in ops_low or "archive" in ops_low:
                bucket.add("delete")
            if "associate" in ops_low:
                bucket.add("associate")

    return defined_surfs, obj_to_ops, listable_objs, issues


def audit_objects(
    sections_by_key: Dict[str, Dict[str, Any]],
    listable_objs: Set[str],
    require_full_6cat: bool,
    rel: str,
) -> Tuple[Set[str], List[str]]:
    issues: List[str] = []
    defined_objs: Set[str] = set()
    sec = sections_by_key.get("core-objects")
    if not sec:
        issues.append(f"{rel}: Missing mandatory Section 5 'Core Objects' (§6.1).")
        return defined_objs, issues

    obj_blocks = split_h3_blocks(sec["lines"], sec["start_line"])
    if not obj_blocks:
        issues.append(f"{rel}:{sec['start_line']}: Section 5 'Core Objects' defines zero '### ... {{#obj-*}}' objects.")
        return defined_objs, issues

    for blk in obj_blocks:
        anc = blk["anchor"]
        if not anc or not anc.startswith("#obj-"):
            issues.append(
                f"{rel}:{blk['start_line']}: Core Object heading '{blk['heading']}' must carry a semantic '{{#obj-*}}' anchor (D10, D14)."
            )
            continue
        defined_objs.add(anc)
        body = "\n".join(blk["lines"])
        body_low = body.lower()
        tables = parse_markdown_tables(blk["lines"], blk["start_line"])

        # D3: 6-column Attributes table
        attr_tbl = None
        for t in tables:
            h_join = " | ".join(c.lower() for c in t["headers"])
            if "attribute" in h_join and "validation" in h_join and "error" in h_join:
                attr_tbl = t
                break
        if attr_tbl is None:
            issues.append(
                f"{rel}:{blk['start_line']}: Object '{anc}' is missing the 6-column D3 Attributes table "
                "('Attribute | Type | Phase | Constraints | Validation Rule | Error Message')."
            )
        else:
            if len(attr_tbl["headers"]) < 6:
                issues.append(f"{rel}:{attr_tbl['header_line']}: Object '{anc}' Attributes table must have all 6 D3 columns.")
            if not attr_tbl["rows"]:
                issues.append(f"{rel}:{attr_tbl['header_line']}: Object '{anc}' Attributes table has 0 attribute rows.")
            for r in attr_tbl["rows"]:
                if len(r["cells"]) < 6:
                    issues.append(f"{rel}:{r['line']}: Attribute row in '{anc}' has fewer than 6 cells (D3).")
                    continue
                for col_idx, cell in enumerate(r["cells"][:6]):
                    if not cell or cell in {"-", "TBD", "TODO", "N/A"}:
                        col_name = attr_tbl["headers"][col_idx]
                        issues.append(
                            f"{rel}:{r['line']}: Attribute '{r['cells'][0]}' in '{anc}' has blank/placeholder '{col_name}' (P6, D3)."
                        )
                err_msg = r["cells"][5].strip("\"'` ").lower()
                if err_msg in {"invalid input", "invalid value", "validation error", "error", "bad request"}:
                    issues.append(
                        f"{rel}:{r['line']}: Attribute '{r['cells'][0]}' in '{anc}' uses generic error message '{r['cells'][5]}'; "
                        "provide exact actionable user-facing copy (D3)."
                    )

        # D4: Lifecycle & State Machine
        is_stateless = bool(re.search(r"stateless|none\s*[—\-:]\s*stateless", body_low))
        if not is_stateless:
            if "valid states" not in body_low and "state" not in body_low:
                issues.append(
                    f"{rel}:{blk['start_line']}: Object '{anc}' must either declare 'Stateless' or define a D4 State Machine."
                )
            else:
                has_trans_tbl = any(
                    "from" in " ".join(h.lower() for h in t["headers"]) and "trigger" in " ".join(h.lower() for h in t["headers"])
                    for t in tables
                )
                if not has_trans_tbl:
                    issues.append(f"{rel}:{blk['start_line']}: Stateful object '{anc}' is missing a Transition table (From | To | Trigger | Guard) (D4).")
                has_forbid_tbl = any(
                    "attempted from" in " ".join(h.lower() for h in t["headers"])
                    for t in tables
                )
                if "forbidden transition" not in body_low and not has_forbid_tbl:
                    issues.append(f"{rel}:{blk['start_line']}: Stateful object '{anc}' is missing explicit Forbidden Transitions + rationale (D4).")

        # Relationships subsection
        if "#### relationships" not in body_low:
            issues.append(f"{rel}:{blk['start_line']}: Object '{anc}' is missing '#### Relationships' subsection (write 'None' explicitly if none, §6.1).")

        # Edge & Failure modes (6 categories + R8)
        if "edge" not in body_low and "failure" not in body_low:
            issues.append(f"{rel}:{blk['start_line']}: Object '{anc}' is missing 'Edge & Failure Modes' subsection (§6.6).")
        elif require_full_6cat:
            for kw, label in (
                ("boundary", "1. Boundary"),
                ("invalid", "2. Invalid Input"),
                ("adversarial", "3. Adversarial Input"),
                ("race", "4. Race / Concurrency"),
                ("dependency", "5. Dependency Failure"),
                ("r8", "6. Auth-Change Propagation (R8)"),
            ):
                if kw == "r8":
                    if "r8" not in body_low and "auth-change" not in body_low and "authorization change" not in body_low and "role" not in body_low:
                        issues.append(f"{rel}:{blk['start_line']}: Object '{anc}' Edge/Failure sweep is missing category '{label}' (§6.6).")
                elif kw == "race":
                    if "race" not in body_low and "concurren" not in body_low:
                        issues.append(f"{rel}:{blk['start_line']}: Object '{anc}' Edge/Failure sweep is missing category '{label}' (§6.6).")
                elif kw not in body_low:
                    issues.append(f"{rel}:{blk['start_line']}: Object '{anc}' Edge/Failure sweep is missing category '{label}' (§6.6).")

        # D20: Empty states (4 mandatory variants when listable or subsection present without 'Not applicable')
        empty_not_applicable = bool(re.search(r"empty states[\s\S]{0,160}not applicable", body_low))
        if (anc in listable_objs or "loaded-zero" in body_low) and not empty_not_applicable:
            for variant in ("loaded-zero", "zero-permission", "zero-day-zero", "loading-error"):
                if variant not in body_low:
                    issues.append(
                        f"{rel}:{blk['start_line']}: Listable object '{anc}' is missing empty-state variant '{variant}' (D20)."
                    )

    return defined_objs, issues


def audit_relationships_r1_r3(
    sections_by_key: Dict[str, Dict[str, Any]],
    defined_objs: Set[str],
    defined_surfs: Set[str],
    strict_r1_r3: bool,
    rel: str,
) -> List[str]:
    issues: List[str] = []
    sec = sections_by_key.get("relationship-map")
    if not sec:
        issues.append(f"{rel}: Missing mandatory Section 6 'Central Relationship Map' (D5, §6.3).")
        return issues

    sec_text = "\n".join(sec["lines"])
    if re.search(r"\bno relationships\b|\bnone\b", sec_text, flags=re.I) and "|" not in sec_text:
        return issues

    tables = parse_markdown_tables(sec["lines"], sec["start_line"])
    if not tables:
        issues.append(f"{rel}:{sec['start_line']}: Section 6 'Central Relationship Map' must include the 7-column D5 table.")
        return issues

    tbl = tables[0]
    if len(tbl["headers"]) < 7:
        issues.append(
            f"{rel}:{tbl['header_line']}: Central Relationship Map must have 7 columns: "
            "'Object A | Cardinality | Object B | Relationship Name | Constraints | Data-Carrying? | Surface Coverage' (§6.3)."
        )
        return issues

    for row in tbl["rows"]:
        cells = row["cells"]
        if len(cells) < 7:
            issues.append(f"{rel}:{row['line']}: Relationship row has fewer than 7 cells.")
            continue
        card = cells[1].upper()
        rel_name = cells[3]
        constraints = cells[4]
        data_carrying = cells[5].lower()
        surf_cov = cells[6]

        is_junction = ("N:M" in card or "M:N" in card or "*:*" in card or data_carrying.startswith("yes"))
        if is_junction:
            j_objs = [m.group(0) for m in SEMANTIC_ANCHOR_RE.finditer(rel_name + " " + cells[0] + " " + cells[2]) if m.group(0).startswith("#obj-")]
            promoted = [m.group(0) for m in SEMANTIC_ANCHOR_RE.finditer(rel_name) if m.group(0).startswith("#obj-")]
            if not promoted:
                issues.append(
                    f"{rel}:{row['line']}: R1 violation — relationship '{rel_name}' is N:M or Data-Carrying ('{cells[5]}') "
                    "and must be promoted to a first-class '#obj-*' in Relationship Name (§4.2, D18)."
                )
            elif strict_r1_r3 and promoted[0] not in defined_objs:
                issues.append(
                    f"{rel}:{row['line']}: R1 violation — promoted junction object '{promoted[0]}' is not defined in Section 5 Core Objects."
                )
            cov_low = surf_cov.lower()
            for req_op in ("create", "list", "remove", "inverse"):
                if req_op not in cov_low:
                    issues.append(
                        f"{rel}:{row['line']}: R1 violation — junction '{rel_name}' Surface Coverage is missing '{req_op}' "
                        "(specify '#surf-*' or '[CUSTOM: ... because ...]', D18)."
                    )

        if strict_r1_r3:
            c_low = constraints.lower()
            if not any(tok in c_low for tok in ("on_delete", "cascade", "restrict", "set_null", "set null", "soft_archive", "soft-delete", "immutable")):
                issues.append(
                    f"{rel}:{row['line']}: R3 violation — relationship '{rel_name}' Constraints must declare deletion/referential integrity "
                    "(CASCADE, RESTRICT, SET_NULL, SOFT_ARCHIVE, or immutable)."
                )
            for s_anc in SEMANTIC_ANCHOR_RE.findall(surf_cov):
                if s_anc.startswith("#surf-") and s_anc not in defined_surfs:
                    issues.append(
                        f"{rel}:{row['line']}: Relationship '{rel_name}' references surface '{s_anc}' missing from Section 8 Surface Inventory."
                    )

    return issues


def audit_features_and_flows(
    sections_by_key: Dict[str, Dict[str, Any]],
    defined_surfs: Set[str],
    strict_r2: bool,
    rel: str,
) -> List[str]:
    issues: List[str] = []
    feat_sec = sections_by_key.get("features")
    if not feat_sec:
        issues.append(f"{rel}: Missing mandatory Section 9 'Features' (§9.1).")
    else:
        feat_blocks = split_h3_blocks(feat_sec["lines"], feat_sec["start_line"])
        if not feat_blocks:
            issues.append(f"{rel}:{feat_sec['start_line']}: Section 9 'Features' defines zero '### ... {{#feat-*}}' features.")
        for fb in feat_blocks:
            anc = fb["anchor"]
            if not anc or not anc.startswith("#feat-"):
                issues.append(f"{rel}:{fb['start_line']}: Feature heading '{fb['heading']}' must carry a '{{#feat-*}}' anchor (D10).")
                continue
            fbody = "\n".join(fb["lines"])
            fbody_low = fbody.lower()

            # P5: single phase tag per feature
            pm = re.search(r"-\s*\*\*Phase:\*\*\s*([^\n]+)", fbody)
            if not pm:
                issues.append(f"{rel}:{fb['start_line']}: Feature '{anc}' is missing '- **Phase:** <Phase>' tag (D6, P5).")
            else:
                pval = re.sub(r"\*\(.*\)\*", "", pm.group(1)).strip()
                if len(re.findall(r"\bphase\s*\d+\b", pval, flags=re.I)) > 1:
                    issues.append(f"{rel}:{fb['start_line']}: Feature '{anc}' lists multiple phases ('{pval}'), violating P5 (one phase per feature).")

            # BDD Given / When / Then
            if not ("given" in fbody_low and "when" in fbody_low and "then" in fbody_low):
                issues.append(f"{rel}:{fb['start_line']}: Feature '{anc}' is missing BDD Given/When/Then acceptance criteria (§5.8).")

            # R2 Authorization Derivation Chain
            is_public = bool(re.search(r"public\s+anonymous|unauthenticated\s+public|zero-auth", fbody_low))
            if strict_r2 and not is_public:
                if "if-and-only-if" not in fbody_low and not re.search(r"\biff\b", fbody_low):
                    issues.append(
                        f"{rel}:{fb['start_line']}: R2 violation — role-gated feature '{anc}' is missing an 'IF-AND-ONLY-IF' "
                        "Authorization Derivation Trace (D19, §4.3)."
                    )
                else:
                    # Verify any #surf-* referenced in auth trace exists
                    for s_anc in SEMANTIC_ANCHOR_RE.findall(fbody):
                        if s_anc.startswith("#surf-") and defined_surfs and s_anc not in defined_surfs:
                            issues.append(
                                f"{rel}:{fb['start_line']}: Feature '{anc}' references surface '{s_anc}' missing from Section 8 Surface Inventory."
                            )

    flow_sec = sections_by_key.get("user-flows")
    if not flow_sec:
        issues.append(f"{rel}: Missing mandatory Section 10 'User Flows' (§9.2).")
    else:
        flow_blocks = split_h3_blocks(flow_sec["lines"], flow_sec["start_line"])
        if not flow_blocks:
            issues.append(f"{rel}:{flow_sec['start_line']}: Section 10 'User Flows' defines zero '### ... {{#flow-*}}' flows.")
        for flw in flow_blocks:
            anc = flw["anchor"]
            if not anc or not anc.startswith("#flow-"):
                issues.append(f"{rel}:{flw['start_line']}: User Flow heading '{flw['heading']}' must carry a '{{#flow-*}}' anchor (D10).")
                continue
            flw_low = "\n".join(flw["lines"]).lower()
            if "happy path" not in flw_low:
                issues.append(f"{rel}:{flw['start_line']}: User Flow '{anc}' is missing 'Happy Path' steps (§5.7, §9.2).")
            if "postcondition" not in flw_low:
                issues.append(f"{rel}:{flw['start_line']}: User Flow '{anc}' is missing explicit 'Postconditions' (§5.7, §9.2).")

    return issues


def audit_bootstrap_and_parity(
    sections_by_key: Dict[str, Dict[str, Any]],
    defined_objs: Set[str],
    defined_surfs: Set[str],
    obj_to_ops: Dict[str, Set[str]],
    strict_parity: bool,
    rel: str,
) -> List[str]:
    issues: List[str] = []
    boot_sec = sections_by_key.get("day-zero-bootstrap")
    seeded_objs: Set[str] = set()

    if not boot_sec:
        issues.append(f"{rel}: Missing mandatory critical Section 11 'Day-Zero Bootstrap Sequence' (D21, R4).")
    else:
        tables = parse_markdown_tables(boot_sec["lines"], boot_sec["start_line"])
        if not tables or not tables[0]["rows"]:
            issues.append(f"{rel}:{boot_sec['start_line']}: Day-Zero Bootstrap must contain an ordered bootstrap sequence table (R4).")
        else:
            for row in tables[0]["rows"]:
                row_raw = " | ".join(row["cells"])
                if "[SEED]" in row_raw:
                    for ob in SEMANTIC_ANCHOR_RE.findall(row_raw):
                        if ob.startswith("#obj-"):
                            seeded_objs.add(ob)
                for sa in SEMANTIC_ANCHOR_RE.findall(row_raw):
                    if sa.startswith("#surf-") and defined_surfs and sa not in defined_surfs:
                        issues.append(
                            f"{rel}:{row['line']}: R4 Bootstrap step references missing surface '{sa}' not in Surface Inventory."
                        )

    if strict_parity:
        core_sec = sections_by_key.get("core-objects")
        core_text = "\n".join(core_sec["lines"]) if core_sec else ""
        for ob in sorted(defined_objs):
            ops = obj_to_ops.get(ob, set())
            has_custom_orphan = bool(re.search(rf"{re.escape(ob)}[\s\S]{{0,300}}\[CUSTOM\s*:", core_text))
            if "create" not in ops and ob not in seeded_objs and not has_custom_orphan:
                issues.append(
                    f"{rel}: R5 Parity gap — object '{ob}' has neither a 'Create' surface in Section 8 nor a '[SEED]' step in Section 11 ([ORPHAN-CAPABILITY])."
                )
            if "read" not in ops and not has_custom_orphan:
                issues.append(
                    f"{rel}: R5 Parity gap — object '{ob}' has no 'Read / List' surface in Section 8 ([ORPHAN-CAPABILITY])."
                )

    return issues


def audit_nfr(sections_by_key: Dict[str, Dict[str, Any]], strict_tables: bool, rel: str) -> List[str]:
    issues: List[str] = []
    sec = sections_by_key.get("nfr")
    if not sec:
        issues.append(f"{rel}: Missing mandatory Section 13 'Non-Functional Requirements' (§7).")
        return issues

    nfr_text = "\n".join(sec["lines"])
    nfr_low = nfr_text.lower()

    for fam, pat in (("Security", r"\bSEC-[1-7]\b"), ("Performance", r"\bPERF-[1-5]\b"), ("Audit/Logging", r"\bLOG-[1-5]\b")):
        if not re.search(pat, nfr_text) and f"{fam.lower()}" not in nfr_low:
            issues.append(f"{rel}:{sec['start_line']}: Mandatory NFR category '{fam}' ({pat}) is missing (§7.5).")
        elif strict_tables and not re.search(pat, nfr_text) and "[CUSTOM:" not in nfr_text:
            issues.append(f"{rel}:{sec['start_line']}: Mandatory NFR category '{fam}' must select a concrete tier ({pat}) or '[CUSTOM: ... because ...]' (§7.2).")

    # §7.3 Quantitative rule whenever SCALE-1..5 is selected
    if re.search(r"\bSCALE-[1-5]\b", nfr_text):
        for req_re, desc in (
            (r"\b(?:qps|tps|rps|req/s|requests/sec)\b", "QPS/TPS/RPS throughput target"),
            (r"\bburst\b|\d+x\b", "burst multiplier"),
            (r"\bconcurrent\b", "concurrent users target"),
            (r"\b(?:\d+\s*(?:month|months|m|year|years|y)|horizon)\b", "growth horizon"),
            (r"\b(?:ratio|factor|linear)\b", "scaling resource/cost ratio"),
        ):
            if not re.search(req_re, nfr_low):
                issues.append(f"{rel}:{sec['start_line']}: Active SCALE-* NFR is missing mandatory numeric '{desc}' (§7.3).")

    # §7.4 Conditional mandatory PII Inventory table when PRIV-2+
    if re.search(r"\bPRIV-[234]\b", nfr_text):
        if "pii inventory" not in nfr_low:
            issues.append(f"{rel}:{sec['start_line']}: PRIV-2+ is selected -> mandatory 'PII Inventory' table is missing (§7.4).")

    # §7.4 Conditional mandatory Observability Component table when OBS-2+
    if re.search(r"\bOBS-[234]\b", nfr_text):
        if "observability component" not in nfr_low and "component matrix" not in nfr_low:
            issues.append(
                f"{rel}:{sec['start_line']}: OBS-2+ is selected -> mandatory 'Observability Component' table is missing (§7.4)."
            )

    return issues


def audit_banned_fluff_and_placeholders(lines: List[str], check_placeholders: bool, rel: str) -> List[str]:
    issues: List[str] = []
    in_fence = False
    in_antipatterns = False
    in_conventions = False

    for idx, raw_line in enumerate(lines, 1):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if stripped.startswith("## ") or stripped.startswith("### "):
            low_h = stripped.lower()
            in_antipatterns = "anti-pattern" in low_h
            in_conventions = "tag & anchor conventions" in low_h or "document tag conventions" in low_h

        if in_fence or in_antipatterns or in_conventions:
            continue

        unquoted = strip_inline_backticks(raw_line)
        for pat, message in BANNED_FLUFF_PATTERNS:
            if re.search(pat, unquoted, flags=re.I):
                issues.append(f"{rel}:{idx}: {message}")

        # Open-ended 'etc.' inside table rows or BDD steps
        if (stripped.startswith("|") or re.match(r"^\s*[-*\d.]+\s*\**(?:Given|When|Then)\b", stripped)) and re.search(r"\betc\.", unquoted, flags=re.I):
            issues.append(f"{rel}:{idx}: Open-ended 'etc.' inside contract table or BDD step violates P1/P6; list closed values.")

        if check_placeholders:
            for pm in re.finditer(r"<[A-Za-z][^>\n]{1,60}>", unquoted):
                tok = pm.group(0)
                if not tok.lower().startswith(("<a ", "<br", "<sup", "<sub", "<http")):
                    issues.append(f"{rel}:{idx}: Unresolved template placeholder '{tok}' remains in finalized spec.")

    return issues


def run_cli_gate(spec_path: Path, phase: str, ledger_arg: Optional[str], as_json: bool) -> int:
    if not spec_path.is_file():
        sys.stderr.write(f"Error: Spec file not found: {spec_path}\n")
        return 1

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "") or os.getcwd()).resolve()
    try:
        rel = spec_path.resolve().relative_to(root).as_posix()
    except ValueError:
        rel = spec_path.as_posix()

    text = spec_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    h2_sections = split_h2_sections(lines)
    sections_by_key = {s["key"]: s for s in h2_sections if s["key"]}
    defined_anchors, referenced_anchors = extract_defined_and_referenced_anchors(lines, sections_by_key)
    tags = extract_active_tags(lines)
    ledger = load_optional_ledger(ledger_arg)

    if phase == "intake":
        objs = sorted(a for a in defined_anchors if a.startswith("#obj-"))
        feats = sorted(a for a in defined_anchors if a.startswith("#feat-"))
        surfs = sorted(a for a in defined_anchors if a.startswith("#surf-"))
        flows = sorted(a for a in defined_anchors if a.startswith("#flow-"))
        fast_issues = check_fast_invariants(lines, rel)
        payload = {
            "phase": "intake",
            "spec": rel,
            "sections_found": [s["heading"] for s in h2_sections],
            "counts": {
                "objects": len(objs),
                "surfaces": len(surfs),
                "features": len(feats),
                "flows": len(flows),
                "draft_tags": len(tags["draft"]),
                "blocked_tags": len(tags["blocked"]),
                "fast_invariant_issues": len(fast_issues),
            },
            "objects": objs,
            "surfaces": surfs,
            "features": feats,
            "issues": fast_issues,
        }
        if as_json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Intake Audit for {rel}:")
            print(
                f"  Objects: {len(objs)} | Surfaces: {len(surfs)} | Features: {len(feats)} "
                f"| Flows: {len(flows)} | [DRAFT] tags: {len(tags['draft'])} | [BLOCKED]: {len(tags['blocked'])}"
            )
            if fast_issues:
                print("  Immediate D1/D7/D15/D16 Issues:")
                for item in fast_issues:
                    print(f"    - {item}")
        return 1 if fast_issues else 0

    if phase == "deep-dive-plan":
        sec_cfg = (ledger or {}).get("sections", {})
        rankings = []
        for s in h2_sections:
            s_tags = extract_active_tags(s["lines"])
            d_cnt = len(s_tags["draft"])
            b_cnt = len(s_tags["blocked"])
            o_cnt = len(s_tags["orphan"])
            key = s["key"] or "other"
            cfg = sec_cfg.get(key, {})
            is_crit = bool(cfg.get("critical")) or key == "day-zero-bootstrap" or b_cnt > 0
            weight = 3 if is_crit else int(cfg.get("weight", 2))
            weakness = d_cnt * weight
            rankings.append(
                {
                    "section": s["heading"],
                    "key": key,
                    "critical": is_crit,
                    "weight": weight,
                    "draft_count": d_cnt,
                    "blocked_count": b_cnt,
                    "orphan_count": o_cnt,
                    "weakness_score": weakness,
                    "priority_key": (b_cnt > 0, is_crit, weakness, d_cnt),
                }
            )
        rankings.sort(key=lambda r: r["priority_key"], reverse=True)
        for r in rankings:
            r.pop("priority_key", None)

        if as_json:
            print(json.dumps({"spec": rel, "rankings": rankings}, indent=2))
        else:
            print(f"Phase 3 Weakness-Scored Deep-Dive Queue for {rel} (Weakness = DRAFT_count * weight):")
            for idx, r in enumerate(rankings, 1):
                crit_badge = " [CRITICAL]" if r["critical"] else ""
                blk_badge = f" [BLOCKED={r['blocked_count']}]" if r["blocked_count"] else ""
                print(
                    f"  {idx:2d}. {r['section']}{crit_badge}{blk_badge} -> "
                    f"Weakness={r['weakness_score']} (drafts={r['draft_count']} * weight={r['weight']})"
                )
        return 0

    if phase == "review":
        review_rows = []
        for s in h2_sections:
            s_drafts = []
            in_fence = False
            in_conv = False
            for off, ln in enumerate(s["lines"]):
                st = ln.strip()
                if st.startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                if st.startswith("## ") or st.startswith("### "):
                    in_conv = "tag & anchor conventions" in st.lower()
                if in_conv:
                    continue
                unq = strip_inline_backticks(ln)
                if re.search(r"\[DRAFT\b", unq):
                    s_drafts.append({"line": s["start_line"] + off, "text": st})
            review_rows.append(
                {
                    "section": s["heading"],
                    "draft_count": len(s_drafts),
                    "disposition": "all confirmed, moving on" if not s_drafts else f"{len(s_drafts)} residual [DRAFT] item(s)",
                    "drafts": s_drafts,
                }
            )
        if as_json:
            print(json.dumps({"spec": rel, "total_drafts": len(tags["draft"]), "sections": review_rows}, indent=2))
        else:
            print(f"Phase 4 Residual [DRAFT] Sweep for {rel} (Total remaining: {len(tags['draft'])}):")
            for r in review_rows:
                if r["draft_count"] == 0:
                    print(f"  - {r['section']}: all confirmed, moving on.")
                else:
                    print(f"  - {r['section']}: {r['draft_count']} residual [DRAFT] item(s):")
                    for d in r["drafts"]:
                        print(f"      L{d['line']}: {d['text']}")
        return 0

    # Gate phases: scaffold | r5-parity | finalize
    issues: List[str] = []
    issues.extend(check_fast_invariants(lines, rel))

    strict_deep_dive = phase in {"r5-parity", "finalize"}
    is_finalize = phase == "finalize"

    defined_surfs, obj_to_ops, listable_objs, surf_issues = audit_surface_inventory(sections_by_key, rel)
    issues.extend(surf_issues)

    defined_objs, obj_issues = audit_objects(sections_by_key, listable_objs, require_full_6cat=strict_deep_dive, rel=rel)
    issues.extend(obj_issues)

    issues.extend(audit_relationships_r1_r3(sections_by_key, defined_objs, defined_surfs, strict_r1_r3=strict_deep_dive, rel=rel))
    issues.extend(audit_features_and_flows(sections_by_key, defined_surfs, strict_r2=strict_deep_dive, rel=rel))
    issues.extend(audit_bootstrap_and_parity(sections_by_key, defined_objs, defined_surfs, obj_to_ops, strict_parity=strict_deep_dive, rel=rel))
    issues.extend(audit_nfr(sections_by_key, strict_tables=strict_deep_dive, rel=rel))
    issues.extend(audit_banned_fluff_and_placeholders(lines, check_placeholders=is_finalize, rel=rel))

    if strict_deep_dive:
        for ln_no, tok in tags["blocked"]:
            issues.append(f"{rel}:{ln_no}: Unresolved '{tok}' marker prohibited at {phase} gate (§4.3).")
        for ln_no, tok in tags["orphan"]:
            issues.append(f"{rel}:{ln_no}: Unresolved '{tok}' marker prohibited at {phase} exit gate (R5, §4.3).")

    if is_finalize:
        # 1. Zero unreviewed [DRAFT — ...] tags
        for ln_no, tok in tags["draft"]:
            issues.append(
                f"{rel}:{ln_no}: Unresolved '{tok}' remains at Finalize; confirm it or convert to "
                "'[ACCEPTED-AS-DRAFT] — Implementation may require clarification' (§4.4)."
            )

        # 2. Canonical 16-section order (§4.5)
        excluded_keys: Set[str] = set()
        if ledger:
            for k, v in ledger.get("sections", {}).items():
                if v.get("status") == "excluded":
                    excluded_keys.add(k)

        expected_keys = [k for k, _ in CANONICAL_H2_ORDER if k not in excluded_keys and k != "anti-patterns"]
        present_keys = [s["key"] for s in h2_sections if s["key"]]
        for ek in expected_keys:
            if ek not in present_keys:
                issues.append(f"{rel}: Missing required canonical section '{ek}' in finalized 16-section FDS (§4.5).")

        order_index = {k: i for i, (k, _) in enumerate(CANONICAL_H2_ORDER)}
        prev_idx = -1
        prev_name = ""
        for s in h2_sections:
            k = s["key"]
            if k in order_index:
                if order_index[k] < prev_idx:
                    issues.append(
                        f"{rel}:{s['start_line']}: Section '{s['heading']}' is out of canonical §4.5 order (appeared after '{prev_name}')."
                    )
                prev_idx = order_index[k]
                prev_name = s["heading"]

        # 3. Broken internal #anchors (§8.3)
        for ln_no, anc in referenced_anchors:
            if anc not in defined_anchors:
                issues.append(f"{rel}:{ln_no}: Broken internal anchor cross-reference '{anc}' (§8.3).")

        # 4. Metadata & Changelog checks (§8.5, §8.6)
        meta_sec = sections_by_key.get("metadata")
        if meta_sec:
            meta_txt = "\n".join(meta_sec["lines"]).lower()
            for mf in ("version", "date", "status", "meta prompt version"):
                if mf not in meta_txt:
                    issues.append(f"{rel}:{meta_sec['start_line']}: Metadata header missing required field '{mf}' (§8.5).")
        chg_sec = sections_by_key.get("changelog")
        if chg_sec and not re.search(r"\bDC-\d{3}\b", "\n".join(chg_sec["lines"])):
            issues.append(f"{rel}:{chg_sec['start_line']}: Section 15 Changelog must contain at least one 'DC-NNN' transaction entry (§8.6).")

    result = {
        "phase": phase,
        "spec": rel,
        "passed": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues,
        "summary": {
            "objects": len(defined_objs),
            "surfaces": len(defined_surfs),
            "open_drafts": len(tags["draft"]),
            "accepted_drafts": len(tags["accepted_draft"]),
            "blocked": len(tags["blocked"]),
            "orphans": len(tags["orphan"]),
        },
    }

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        status_word = "PASS" if result["passed"] else "FAIL"
        print(
            f"FDS Audit [{phase}] {status_word} for {rel} "
            f"(objects={len(defined_objs)}, surfaces={len(defined_surfs)}, drafts={len(tags['draft'])}, issues={len(issues)})"
        )
        for item in issues:
            print(f"  - {item}")

    return 0 if result["passed"] else 1


def run_post_tool_hook() -> int:
    raw_stdin = sys.stdin.read()
    if not raw_stdin.strip():
        return 0
    try:
        payload = json.loads(raw_stdin)
    except Exception:
        return 0

    ti = payload.get("tool_input") or {}
    raw_path = ti.get("file_path") or ti.get("path") or ""
    if not raw_path or not raw_path.endswith(".md"):
        return 0

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "") or os.getcwd()).resolve()
    target = Path(raw_path)
    if not target.is_absolute():
        target = (root / target).resolve()
    if not target.is_file():
        return 0

    try:
        rel = target.relative_to(root).as_posix()
    except ValueError:
        rel = target.as_posix()

    # Never trigger FDS document checks on skill docs/templates/guides themselves
    fname = Path(rel).name
    if (
        "/.claude/skills/" in ("/" + rel)
        or fname in {"FDS_BUILDER.md", "FINDINGS.md", "README.md", "TEMP-PLANNING.md", "CLAUDE.md", "AGENTS.md"}
        or fname.startswith("GREENFIELD")
    ):
        return 0

    text = target.read_text(encoding="utf-8", errors="ignore")
    head = "\n".join(text.splitlines()[:40])
    is_fds = bool(
        re.search(r"(?i)(^|/|[-_])fds([-_.]|\.md$)|(^|/)docs/spec\.md$", rel)
        or "Functional Design Specification" in head
        or "Meta Prompt Version" in head
    )
    if not is_fds:
        return 0

    issues = check_fast_invariants(text.splitlines(), rel)
    if issues:
        msg = "FDS Builder PostToolUse invariant check blocked edit:\n" + "\n".join("- " + x for x in issues[:8])
        print(json.dumps({"decision": "block", "reason": msg}))
    return 0


def main() -> None:
    if len(sys.argv) == 1:
        sys.exit(run_post_tool_hook())

    parser = argparse.ArgumentParser(description="Deterministic FDS static auditor for /fds-builder")
    parser.add_argument("spec", help="Path to FDS markdown file")
    parser.add_argument(
        "--phase",
        choices=["intake", "scaffold", "deep-dive-plan", "r5-parity", "review", "finalize"],
        default="finalize",
        help="Audit gate to execute",
    )
    parser.add_argument("--ledger", help="Optional path to fds-state JSON ledger")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    args = parser.parse_args()
    sys.exit(run_cli_gate(Path(args.spec), args.phase, args.ledger, args.json))


if __name__ == "__main__":
    main()
