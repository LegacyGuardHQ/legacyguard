import ast
import hashlib
import json
from pathlib import Path
import sys


COMPOUND_STATEMENT_FIELDS = {"body", "orelse", "finalbody", "handlers", "cases"}


def _statement_span(statement: ast.stmt, include_body: bool) -> tuple[int, int]:
    start_line = statement.lineno
    decorators = getattr(statement, "decorator_list", [])
    if decorators:
        start_line = min(start_line, *(decorator.lineno for decorator in decorators))
    end_line = statement.end_lineno or statement.lineno
    if not include_body:
        child_lines = []
        for field, value in ast.iter_fields(statement):
            if field not in COMPOUND_STATEMENT_FIELDS or not isinstance(value, list):
                continue
            for child in value:
                if isinstance(child, ast.stmt):
                    child_lines.append(child.lineno)
                else:
                    child_lines.extend(
                        nested.lineno
                        for nested in getattr(child, "body", [])
                        if isinstance(nested, ast.stmt)
                    )
        if child_lines:
            end_line = min(child_lines) - 1
    return start_line, end_line


def _source_for_statement(lines: list[str], statement: ast.stmt, include_body: bool = False) -> str:
    start_line, end_line = _statement_span(statement, include_body)

    return "\n".join(lines[start_line - 1 : end_line])


def get_fingerprint(path: Path, start_line: int, end_line: int) -> dict[str, object]:
    source = path.read_text(encoding="utf-8")
    lines = source.split("\n")
    tree = ast.parse(source, filename=str(path))
    candidates = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.stmt)
        and node.lineno <= start_line
        and (node.end_lineno or node.lineno) >= end_line
    ]
    if not candidates:
        raise ValueError("scanner range does not resolve to a Python statement")

    smallest_range = min((node.end_lineno or node.lineno) - node.lineno for node in candidates)
    targets = [
        node
        for node in candidates
        if (node.end_lineno or node.lineno) - node.lineno == smallest_range
    ]
    if len(targets) != 1:
        raise ValueError("scanner range resolves ambiguously to Python statements")
    target = targets[0]

    siblings = None
    target_index = -1
    for parent in ast.walk(tree):
        for _, value in ast.iter_fields(parent):
            if isinstance(value, list) and target in value:
                siblings = value
                target_index = value.index(target)
                break
        if siblings is not None:
            break
    if siblings is None:
        raise ValueError("reviewed Python statement has no enclosing statement block")

    previous = siblings[target_index - 1] if target_index > 0 else None
    following = siblings[target_index + 1] if target_index + 1 < len(siblings) else None
    if previous is not None and not isinstance(previous, ast.stmt):
        raise ValueError("preceding context is not a Python statement")
    if following is not None and not isinstance(following, ast.stmt):
        raise ValueError("following context is not a Python statement")

    target_source = _source_for_statement(lines, target, include_body=True)

    context_parts = [
        "legacyguard-reviewed-sast-source-v1",
        "previous statement",
        _source_for_statement(lines, previous) if previous is not None else "<block-start>",
        "reviewed statement",
        target_source,
        "following statement",
        _source_for_statement(lines, following) if following is not None else "<block-end>",
    ]
    canonical_source = "\n".join(context_parts) + "\n"
    fingerprint = hashlib.sha256(canonical_source.encode("utf-8")).hexdigest()

    def statement_range(statement: ast.stmt | None) -> list[int] | None:
        if statement is None:
            return None
        return list(_statement_span(statement, include_body=statement is target))

    return {
        "sha256": fingerprint,
        "previous": statement_range(previous),
        "reviewed": statement_range(target),
        "following": statement_range(following),
        "canonical_source": canonical_source,
    }


def main() -> int:
    try:
        result = get_fingerprint(Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
        print(json.dumps(result, ensure_ascii=True))
    except (IndexError, OSError, SyntaxError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())