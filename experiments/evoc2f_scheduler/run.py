"""EvoC2F effect-aware scheduling synthetic mechanism experiment.

No paper benchmark data or model calls are used. The experiment is intentionally small
and CPU-only; it demonstrates scheduling semantics, not paper-level performance.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parent
SEED = 20261008
REPEATS = 12


@dataclass(frozen=True)
class TaskSpec:
    name: str
    deps: tuple[str, ...]
    reads: frozenset[str]
    writes: frozenset[str]
    latency_s: float
    op_id: str | None
    action: str
    delta: int = 0
    fail_after_commit_once: bool = False
    max_retries: int = 2


@dataclass
class SharedStore:
    state: dict[str, int] = field(
        default_factory=lambda: {"account": 100, "inventory": 10, "report": 0, "summary": 0}
    )
    applied: dict[str, int] = field(default_factory=dict)
    failed_once: set[str] = field(default_factory=set)
    events: list[dict[str, object]] = field(default_factory=list)
    active: dict[str, tuple[frozenset[str], frozenset[str]]] = field(default_factory=dict)
    observed_conflicts: list[tuple[str, str, tuple[str, ...]]] = field(default_factory=list)
    event_lock: threading.Lock = field(default_factory=threading.Lock)

    def enter(self, task: TaskSpec) -> None:
        with self.event_lock:
            for other, (other_reads, other_writes) in self.active.items():
                resources = (task.writes & (other_reads | other_writes)) | (
                    task.reads & other_writes
                )
                if resources:
                    self.observed_conflicts.append((other, task.name, tuple(sorted(resources))))
            self.active[task.name] = (task.reads, task.writes)

    def leave(self, task: TaskSpec) -> None:
        with self.event_lock:
            self.active.pop(task.name, None)

    def log(self, **event: object) -> None:
        with self.event_lock:
            self.events.append({"time": time.perf_counter(), **event})


TASKS: dict[str, TaskSpec] = {
    "account_bonus": TaskSpec(
        "account_bonus", (), frozenset({"account"}), frozenset({"account"}), 0.040,
        "plan/account_bonus", "delta", 10,
    ),
    "account_credit": TaskSpec(
        "account_credit", (), frozenset({"account"}), frozenset({"account"}), 0.040,
        "plan/account_credit", "delta", 20,
    ),
    "inventory_restock": TaskSpec(
        "inventory_restock", (), frozenset({"inventory"}), frozenset({"inventory"}), 0.055,
        "plan/inventory_restock", "delta", 5,
    ),
    "account_report": TaskSpec(
        "account_report", ("account_bonus", "account_credit"), frozenset({"account"}),
        frozenset({"report"}), 0.025, None, "copy_account",
    ),
    "inventory_ship": TaskSpec(
        "inventory_ship", ("inventory_restock",), frozenset({"inventory"}),
        frozenset({"inventory"}), 0.030, "plan/inventory_ship", "delta", -2, True,
    ),
    "finalize": TaskSpec(
        "finalize", ("account_report", "inventory_ship"),
        frozenset({"report", "inventory"}), frozenset({"summary"}), 0.020,
        None, "summary",
    ),
}


def conflict(left: TaskSpec, right: TaskSpec) -> bool:
    return bool(
        (left.writes & (right.reads | right.writes))
        | (left.reads & right.writes)
    )


def transitive_reachable(deps: dict[str, set[str]], source: str, target: str) -> bool:
    """Return whether target already depends (directly or transitively) on source."""
    frontier = [target]
    seen: set[str] = set()
    while frontier:
        current = frontier.pop()
        if current == source:
            return True
        if current in seen:
            continue
        seen.add(current)
        frontier.extend(deps[current])
    return False


def compile_effect_edges(tasks: dict[str, TaskSpec]) -> tuple[dict[str, set[str]], list[tuple[str, str]]]:
    deps = {name: set(task.deps) for name, task in tasks.items()}
    added: list[tuple[str, str]] = []
    names = sorted(tasks)
    for index, left_name in enumerate(names):
        for right_name in names[index + 1 :]:
            left, right = tasks[left_name], tasks[right_name]
            if not conflict(left, right):
                continue
            if transitive_reachable(deps, left_name, right_name) or transitive_reachable(
                deps, right_name, left_name
            ):
                continue
            # Stable identifier order is the deterministic per-resource ordering.
            deps[right_name].add(left_name)
            added.append((left_name, right_name))
    return deps, added


def execute_task(store: SharedStore, task: TaskSpec, attempt: int) -> dict[str, object]:
    store.enter(task)
    store.log(event="start", task=task.name, attempt=attempt)
    try:
        if task.op_id is not None and task.op_id in store.applied:
            store.log(event="idempotent_replay", task=task.name, attempt=attempt)
            return {"replayed": True, "value": store.applied[task.op_id]}

        if task.action == "delta":
            resource = next(iter(task.writes))
            before = store.state[resource]
            # This intentionally models a non-atomic external read-modify-write.
            time.sleep(task.latency_s)
            after = before + task.delta
            store.state[resource] = after
            if task.op_id is not None:
                store.applied[task.op_id] = after
            store.log(
                event="commit", task=task.name, attempt=attempt,
                resource=resource, before=before, after=after,
            )
            if task.fail_after_commit_once and task.name not in store.failed_once:
                store.failed_once.add(task.name)
                store.log(event="transient_after_commit", task=task.name, attempt=attempt)
                raise RuntimeError("synthetic transient failure after commit")
            return {"replayed": False, "value": after}

        if task.action == "copy_account":
            time.sleep(task.latency_s)
            store.state["report"] = store.state["account"]
            return {"value": store.state["report"]}

        if task.action == "summary":
            time.sleep(task.latency_s)
            store.state["summary"] = store.state["report"] + store.state["inventory"]
            return {"value": store.state["summary"]}
        raise ValueError(f"unknown action: {task.action}")
    finally:
        store.log(event="end", task=task.name, attempt=attempt)
        store.leave(task)


def run_schedule(mode: str) -> dict[str, object]:
    if mode == "effect_aware":
        deps, effect_edges = compile_effect_edges(TASKS)
        workers = 4
    else:
        deps = {name: set(task.deps) for name, task in TASKS.items()}
        effect_edges = []
        workers = 1 if mode == "serial" else 4

    store = SharedStore()
    pending = set(TASKS)
    completed: set[str] = set()
    attempts = {name: 0 for name in TASKS}
    running: dict[Future[dict[str, object]], str] = {}
    started = time.perf_counter()

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix=mode) as pool:
        while pending or running:
            ready = sorted(name for name in pending if deps[name] <= completed)
            while ready and len(running) < workers:
                name = ready.pop(0)
                pending.remove(name)
                attempts[name] += 1
                future = pool.submit(execute_task, store, TASKS[name], attempts[name])
                running[future] = name

            if not running:
                raise RuntimeError(f"scheduler deadlock in {mode}: {sorted(pending)}")

            done, _ = wait(running, return_when=FIRST_COMPLETED)
            for future in done:
                name = running.pop(future)
                try:
                    future.result()
                except Exception as exc:
                    if attempts[name] <= TASKS[name].max_retries:
                        store.log(event="retry", task=name, attempt=attempts[name], error=str(exc))
                        pending.add(name)
                    else:
                        raise
                else:
                    completed.add(name)

    elapsed = time.perf_counter() - started
    return {
        "mode": mode,
        "elapsed_seconds": elapsed,
        "final_state": dict(store.state),
        "attempts": attempts,
        "idempotency_keys": sorted(store.applied),
        "observed_conflicts": [list(item) for item in store.observed_conflicts],
        "effect_edges": [list(edge) for edge in effect_edges],
        "events": store.events,
    }


def summarize(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "p95_nearest_rank": ordered[max(0, int(0.95 * len(ordered) + 0.999999) - 1)],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    all_runs: list[dict[str, object]] = []
    for repeat in range(REPEATS):
        for mode in ("serial", "dependency_only", "effect_aware"):
            result = run_schedule(mode)
            result["repeat"] = repeat
            all_runs.append(result)

    reference = next(run for run in all_runs if run["mode"] == "serial")["final_state"]
    by_mode: dict[str, dict[str, object]] = {}
    for mode in ("serial", "dependency_only", "effect_aware"):
        runs = [run for run in all_runs if run["mode"] == mode]
        states = [run["final_state"] for run in runs]
        by_mode[mode] = {
            "timing_seconds": summarize([float(run["elapsed_seconds"]) for run in runs]),
            "equivalent_runs": sum(state == reference for state in states),
            "total_runs": len(runs),
            "unique_final_states": [
                json.loads(value)
                for value in sorted({json.dumps(state, sort_keys=True) for state in states})
            ],
            "mean_observed_conflicts": statistics.fmean(
                len(run["observed_conflicts"]) for run in runs
            ),
            "retry_attempts": [run["attempts"]["inventory_ship"] for run in runs],
        }

    serial_mean = float(by_mode["serial"]["timing_seconds"]["mean"])
    effect_mean = float(by_mode["effect_aware"]["timing_seconds"]["mean"])
    dep_mean = float(by_mode["dependency_only"]["timing_seconds"]["mean"])
    summary = {
        "experiment": "EvoC2F dependency/effect-aware scheduling mechanism example",
        "reproduction_level": "机制示例（合成任务，不是论文基准复现）",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "repeats": REPEATS,
        "task_graph": {
            name: {
                "deps": list(task.deps),
                "reads": sorted(task.reads),
                "writes": sorted(task.writes),
                "latency_s": task.latency_s,
                "op_id": task.op_id,
                "fail_after_commit_once": task.fail_after_commit_once,
            }
            for name, task in TASKS.items()
        },
        "serial_reference_state": reference,
        "modes": by_mode,
        "effect_aware_speedup_vs_serial": serial_mean / effect_mean,
        "dependency_only_speedup_vs_serial": serial_mean / dep_mean,
        "checks": {
            "effect_aware_all_equivalent": by_mode["effect_aware"]["equivalent_runs"] == REPEATS,
            "dependency_only_exposes_non_equivalence": by_mode["dependency_only"]["equivalent_runs"] < REPEATS,
            "retry_was_exercised": all(
                attempt == 2 for attempt in by_mode["effect_aware"]["retry_attempts"]
            ),
            "idempotent_retry_preserved_inventory": all(
                state["inventory"] == 13
                for state in by_mode["effect_aware"]["unique_final_states"]
            ),
        },
    }

    assert all(summary["checks"].values()), summary["checks"]
    (output_dir / "results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (output_dir / "runs.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "repeat", "mode", "elapsed_seconds", "equivalent_to_serial",
                "observed_conflict_count", "inventory_ship_attempts", "final_state",
            ],
        )
        writer.writeheader()
        for run in all_runs:
            writer.writerow(
                {
                    "repeat": run["repeat"],
                    "mode": run["mode"],
                    "elapsed_seconds": f"{run['elapsed_seconds']:.9f}",
                    "equivalent_to_serial": run["final_state"] == reference,
                    "observed_conflict_count": len(run["observed_conflicts"]),
                    "inventory_ship_attempts": run["attempts"]["inventory_ship"],
                    "final_state": json.dumps(run["final_state"], sort_keys=True),
                }
            )

    first_runs = {mode: next(run for run in all_runs if run["mode"] == mode) for mode in by_mode}
    log_lines = [
        f"generated_at={summary['generated_at']}",
        f"seed={SEED}",
        f"repeats={REPEATS}",
        f"serial_reference={json.dumps(reference, sort_keys=True)}",
    ]
    for mode in ("serial", "dependency_only", "effect_aware"):
        log_lines.append(f"[{mode}] {json.dumps(by_mode[mode], ensure_ascii=False, sort_keys=True)}")
        log_lines.append(
            f"[{mode}:first_run_events] "
            + json.dumps(first_runs[mode]["events"], ensure_ascii=False, sort_keys=True)
        )
    log_lines.append("checks=" + json.dumps(summary["checks"], ensure_ascii=False, sort_keys=True))
    (output_dir / "run.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
