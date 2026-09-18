from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path


_BENCH_PATH = Path(__file__).parents[1] / "scripts" / "bench.py"
_SPEC = importlib.util.spec_from_file_location("bench", _BENCH_PATH)
bench = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(bench)


def test_parallel_benchmark_is_faster_than_sequential_for_io_bound_work():
    sequential, parallel = asyncio.run(bench.benchmark(items_count=4, delay_seconds=0.02, concurrency=4))
    assert parallel < sequential * 0.7
