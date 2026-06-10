"""Render a Behave JSON report as a GitHub Actions job summary (Markdown).

Usage: python behave_summary.py <behave-report.json>
Writes the Markdown summary to stdout; the workflow appends it to
$GITHUB_STEP_SUMMARY. Mirrors the frontend Vitest summary (features / scenarios /
steps, passed vs. total) and lists any failed scenarios.
"""

import collections
import json
import sys

_FAILED = {"failed", "error"}
_SKIPPED = {"skipped", "untested", "undefined"}


def _line(label: str, counts: collections.Counter) -> str:
    passed = counts.get("passed", 0)
    failed = sum(counts[s] for s in _FAILED if s in counts)
    skipped = sum(counts[s] for s in _SKIPPED if s in counts)
    total = passed + failed + skipped
    parts = [f"{'✅' if failed == 0 else '❌'} {passed} passed"]
    if failed:
        parts.append(f"❌ {failed} failed")
    if skipped:
        parts.append(f"⏭️ {skipped} skipped")
    parts.append(f"{total} total")
    return f"- **{label}:** " + " · ".join(parts)


def main() -> None:
    with open(sys.argv[1]) as fh:
        features = json.load(fh)

    feat = collections.Counter()
    scen = collections.Counter()
    step = collections.Counter()
    failed_scenarios: list[str] = []

    for feature in features:
        feat[feature.get("status", "untested")] += 1
        for element in feature.get("elements", []):
            for s in element.get("steps", []):
                status = s.get("result", {}).get("status")
                # Background placeholder steps carry no result — skip them.
                if status is not None:
                    step[status] += 1
            if element.get("type") != "scenario":
                continue
            status = element.get("status", "untested")
            scen[status] += 1
            if status in _FAILED:
                failed_scenarios.append(
                    f"{feature.get('name', '?')} › {element.get('name', '?')}"
                )

    out = [
        "## Backend Component Test Report",
        "",
        "### Summary",
        _line("Features", feat),
        _line("Scenarios", scen),
        _line("Steps", step),
    ]
    if failed_scenarios:
        out += ["", "### Failed scenarios"]
        out += [f"- ❌ {name}" for name in failed_scenarios]

    print("\n".join(out))


if __name__ == "__main__":
    main()
