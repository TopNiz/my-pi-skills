#!/usr/bin/env python3
"""Inspect and index a Rocket.Chat OpenAPI spec (live /api/docs/json)."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")


def load_spec(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def resolve(spec: dict, schema):
    """Resolve local $ref chains."""
    seen = 0
    while isinstance(schema, dict) and "$ref" in schema and seen < 25:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            return schema
        node = spec
        for part in ref[2:].split("/"):
            key = part.replace("~1", "/").replace("~0", "~")
            node = node.get(key, {}) if isinstance(node, dict) else {}
        schema = node
        seen += 1
    return schema


def schema_type(spec: dict, schema) -> str:
    schema = resolve(spec, schema)
    if not isinstance(schema, dict):
        return "any"
    if "type" in schema:
        kind = schema["type"]
        if kind == "array":
            return "array<%s>" % schema_type(spec, schema.get("items", {}))
        return kind
    for key in ("anyOf", "oneOf", "allOf"):
        if key in schema:
            parts = [schema_type(spec, sub) for sub in schema[key]]
            unique = list(dict.fromkeys(parts))
            if len(unique) == 1:
                return unique[0]
            return "%s(%s)" % (key, " | ".join(unique))
    if "enum" in schema:
        return "enum"
    return "object"


def object_props(spec: dict, schema) -> dict:
    """Merge top-level properties with any anyOf/oneOf/allOf branches."""
    schema = resolve(spec, schema)
    if not isinstance(schema, dict):
        return {}
    props: dict = dict(schema.get("properties") or {})
    for key in ("anyOf", "oneOf", "allOf"):
        for sub in schema.get(key, []):
            props.update(object_props(spec, sub))
    return props


def required_set(spec: dict, schema) -> set:
    """Fields required in every valid payload (top-level and allOf only)."""
    schema = resolve(spec, schema)
    if not isinstance(schema, dict):
        return set()
    required = set(schema.get("required") or [])
    for sub in schema.get("allOf", []):
        required |= required_set(spec, sub)
    return required


def required_alternatives(spec: dict, schema) -> list[frozenset]:
    """Alternative required-field sets from anyOf/oneOf."""
    schema = resolve(spec, schema)
    if not isinstance(schema, dict):
        return []
    alternatives: list[frozenset] = []
    for key in ("anyOf", "oneOf"):
        for sub in schema.get(key, []):
            sub = resolve(spec, sub)
            fields = set((sub.get("required") if isinstance(sub, dict) else None) or [])
            if fields:
                alternatives.append(frozenset(fields))
    return list(dict.fromkeys(alternatives))


def normalize_target(target: str) -> str:
    target = target.strip()
    if target.startswith("/"):
        return target
    return "/api/v1/" + target


def derive(path: str) -> tuple[str, str]:
    """Return (family, action) from a path."""
    match = re.match(r"^/api/v1/(.*)$", path)
    if match:
        rest = match.group(1)
        first = rest.split("/", 1)[0]
        if "." in first:
            family, action = first.split(".", 1)
            return family, action
        if "/" in rest:
            family, action = rest.split("/", 1)
            return family, action
        return (rest or "(root)"), "(root)"
    match = re.match(r"^/api/(.*)$", path)
    if match:
        rest = match.group(1)
        if "/" in rest:
            family, action = rest.split("/", 1)
            return family, action
        return (rest or "(root)"), "(root)"
    return "(root)", path


def all_operations(spec: dict):
    for path, ops in spec.get("paths", {}).items():
        for method in HTTP_METHODS:
            if method in ops:
                yield method, path, ops[method]


def find_path(spec: dict, target: str):
    """Resolve a target to (status, path), where status is ok/ambiguous/missing."""
    paths = spec.get("paths", {})
    if target in paths:
        return "ok", target
    normalized = normalize_target(target)
    if normalized in paths:
        return "ok", normalized
    needle = target.lower()
    matches = [p for p in paths if needle in p.lower()]
    if len(matches) == 1:
        return "ok", matches[0]
    if matches:
        print("Multiple paths match %r:" % target, file=sys.stderr)
        for path in sorted(matches)[:30]:
            print("  " + path, file=sys.stderr)
        return "ambiguous", None
    return "missing", None


def print_operation(spec: dict, path: str, method: str | None, as_json: bool, documented: bool):
    ops = spec["paths"][path]
    if as_json:
        if method:
            print(json.dumps(ops[method], indent=2))
        else:
            print(json.dumps(ops, indent=2))
        return 0

    if method is None:
        methods = [m for m in HTTP_METHODS if m in ops]
        if len(methods) > 1:
            print("%s has multiple methods: %s" % (path, ", ".join(m.upper() for m in methods)))
            print("Pick one, for example: rc-doc.sh %s %s" % (methods[0].upper(), path))
            return 0
        if not methods:
            print("No HTTP methods found for %s" % path)
            return 1
        method = methods[0]

    op = ops[method]
    print("%s %s" % (method.upper(), path))
    if not documented:
        print("note: undocumented route; only present with withUndocumented=true")
    print()

    print("Parameters")
    printed = 0
    alt_schemas: list[dict] = []
    for param in op.get("parameters") or []:
        name = param.get("name", "?")
        location = param.get("in", "?")
        schema = param.get("schema", {})
        if name == "query":
            alt_schemas.append(schema)
            props = object_props(spec, schema)
            req = required_set(spec, schema)
            for prop_name, prop_schema in props.items():
                mark = " (required)" if prop_name in req else ""
                desc = (prop_schema.get("description") or "").strip()
                line = "  %s [query]%s: %s" % (prop_name, mark, schema_type(spec, prop_schema))
                if desc:
                    line += "  " + desc
                print(line)
                printed += 1
            continue
        mark = " (required)" if param.get("required") else ""
        desc = (param.get("description") or "").strip()
        line = "  %s [%s]%s: %s" % (name, location, mark, schema_type(spec, schema))
        if desc:
            line += "  " + desc
        print(line)
        printed += 1
    if not printed:
        print("  (none)")

    print()
    print("Request body")
    request_body = op.get("requestBody")
    if request_body:
        content = request_body.get("content") or {}
        media = content.get("application/json") or (next(iter(content.values()), {}) if content else {})
        schema = media.get("schema", {}) if isinstance(media, dict) else {}
        alt_schemas.append(schema)
        props = object_props(spec, schema)
        req = required_set(spec, schema)
        if not props:
            print("  %s" % schema_type(spec, schema))
        else:
            for prop_name, prop_schema in props.items():
                mark = " (required)" if prop_name in req else ""
                desc = (prop_schema.get("description") or "").strip()
                line = "  %s%s: %s" % (prop_name, mark, schema_type(spec, prop_schema))
                if desc:
                    line += "  " + desc
                print(line)
    else:
        print("  (none)")

    alternatives: list[frozenset] = []
    for alt_schema in alt_schemas:
        alternatives.extend(required_alternatives(spec, alt_schema))
    alternatives = list(dict.fromkeys(alternatives))
    if alternatives:
        print()
        rendered = ["one of: " + ", ".join(sorted(fields)) for fields in alternatives]
        print("Required alternatives: " + " | ".join(rendered))

    print()
    print("Responses")
    responses = op.get("responses") or {}
    for status in sorted(responses, key=lambda s: (not str(s).startswith("2"), str(s))):
        response = responses[status]
        desc = (response.get("description") or "").strip()
        content = response.get("content") or {}
        media = content.get("application/json") if isinstance(content, dict) else None
        if not media:
            print("  %s: %s" % (status, desc or "no body"))
            continue
        schema = media.get("schema", {})
        props = object_props(spec, schema)
        req = required_set(spec, schema)
        keys = []
        for prop_name, prop_schema in props.items():
            mark = "*" if prop_name in req else ""
            keys.append("%s%s:%s" % (prop_name, mark, schema_type(spec, prop_schema)))
        line = "  %s: %s" % (status, ", ".join(keys) if keys else schema_type(spec, schema))
        if desc:
            line += "  (%s)" % desc
        print(line)

    print()
    print("Legend: * = required. Types are simplified; use --json for the raw operation.")
    return 0


def print_families(spec: dict, doc_paths: set[str] | None):
    families: dict[str, list] = {}
    for method, path, _ in all_operations(spec):
        family, action = derive(path)
        families.setdefault(family, []).append((method, path, action))
    print("Families in this spec (%d operations):" % sum(len(v) for v in families.values()))
    for family in sorted(families, key=lambda f: (-len(families[f]), f.lower())):
        print("  %-28s %d" % (family, len(families[family])))
    return 0


def print_family(spec: dict, family: str, doc_paths: set[str] | None):
    rows = []
    for method, path, _ in all_operations(spec):
        fam, action = derive(path)
        if fam == family:
            documented = (doc_paths is None) or (path in doc_paths)
            rows.append((method, path, action, documented))
    if not rows:
        print("No endpoints found for family: %s" % family, file=sys.stderr)
        return 1
    for method, path, action, documented in sorted(rows, key=lambda r: (r[1], r[0])):
        mark = "" if documented else "  (undocumented)"
        print("%-6s %s%s" % (method.upper(), path, mark))
    return 0


def build_index(spec_full: dict, spec_doc: dict | None, out_path: str, url: str):
    doc_paths = set(spec_doc.get("paths", {})) if spec_doc else set()
    families: dict[str, list] = {}
    for method, path, _ in all_operations(spec_full):
        family, action = derive(path)
        families.setdefault(family, []).append((method, path, action, path in doc_paths))

    total = sum(len(v) for v in families.values())
    info = spec_full.get("info", {})
    lines = [
        "# Rocket.Chat REST API Index",
        "",
        "- **Live source**: `%s`" % url,
        "- **Server version**: %s" % info.get("version", "?"),
        "- **OpenAPI**: %s" % spec_full.get("openapi", "?"),
        "- **Operations**: %d across %d paths" % (total, len(spec_full.get("paths", {}))),
        "- **Generated**: %s" % _dt.date.today().isoformat(),
        "",
        "Undocumented routes are marked with a dagger (†). They only appear when the spec is fetched with `?withUndocumented=true`.",
        "",
        "For full parameter, request-body, and response detail:",
        "",
        "```bash",
        "bash scripts/rc-doc.sh <family>.<action>",
        "```",
        "",
        "## Families",
        "",
        "| Family | Operations |",
        "|---|---:|",
    ]
    for family in sorted(families, key=lambda f: (-len(families[f]), f.lower())):
        lines.append("| `%s` | %d |" % (family, len(families[family])))
    lines.append("")

    for family in sorted(families, key=lambda f: (-len(families[f]), f.lower())):
        lines.append("## %s" % family)
        lines.append("")
        lines.append("| Method | Endpoint | Action |")
        lines.append("|---|---|---|")
        for method, path, action, documented in sorted(families[family], key=lambda r: (r[1], r[0])):
            mark = "" if documented else " †"
            lines.append("| %s | `%s`%s | %s |" % (method.upper(), path, mark, action))
        lines.append("")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return total, len(families)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a Rocket.Chat OpenAPI spec.")
    sub = parser.add_subparsers(dest="command", required=True)

    doc = sub.add_parser("doc", help="Describe one endpoint or list a family.")
    doc.add_argument("--spec", required=True, help="Spec file to inspect.")
    doc.add_argument("--doc-spec", help="Documented-only spec, used to flag undocumented routes.")
    doc.add_argument("--path", help="Exact path, for example /api/v1/users.create.")
    doc.add_argument("--target", help="Shorthand, for example users.create.")
    doc.add_argument("--method", help="HTTP method when a path has several.")
    doc.add_argument("--family", help="List every endpoint in this family.")
    doc.add_argument("--list", action="store_true", help="List families.")
    doc.add_argument("--json", action="store_true", help="Print the raw operation JSON.")
    doc.add_argument("positional", nargs="*", help="Target and optional method.")

    index = sub.add_parser("index", help="Generate the markdown API index.")
    index.add_argument("--spec", required=True, help="Full spec (withUndocumented).")
    index.add_argument("--doc-spec", help="Documented-only spec.")
    index.add_argument("--out", required=True, help="Output markdown path.")
    index.add_argument("--url", required=True, help="Live spec URL for the header.")

    args = parser.parse_args()

    if args.command == "index":
        spec_full = load_spec(args.spec)
        spec_doc = load_spec(args.doc_spec) if args.doc_spec else None
        total, families = build_index(spec_full, spec_doc, args.out, args.url)
        print("Indexed %d operations across %d families -> %s" % (total, families, args.out))
        return 0

    spec = load_spec(args.spec)
    doc_paths = set(load_spec(args.doc_spec).get("paths", {})) if args.doc_spec else None

    if args.list:
        return print_families(spec, doc_paths)

    if args.family:
        return print_family(spec, args.family, doc_paths)

    method = args.method
    target = args.path or args.target

    if not target and args.positional:
        first = args.positional[0]
        if first.upper() in {m.upper() for m in HTTP_METHODS} and len(args.positional) > 1:
            method = first
            target = args.positional[1]
        else:
            target = first
            if len(args.positional) > 1:
                method = args.positional[1]

    if not target:
        parser.error("doc requires a target, for example: users.create or /api/v1/users.create")

    status, path = find_path(spec, target)
    if status != "ok":
        if status == "missing":
            print("No path matched: %s" % target, file=sys.stderr)
            print("Try: rc-doc.sh --list", file=sys.stderr)
            if doc_paths is not None:
                print("If it is undocumented, drop --documented-only.", file=sys.stderr)
        return 1

    documented = (doc_paths is None) or (path in doc_paths)
    if method:
        method = method.lower()
        if method not in {m for m in HTTP_METHODS if m in spec["paths"][path]}:
            print("%s is not a method for %s" % (method.upper(), path), file=sys.stderr)
            return 1
    return print_operation(spec, path, method, args.json, documented)


if __name__ == "__main__":
    raise SystemExit(main())
