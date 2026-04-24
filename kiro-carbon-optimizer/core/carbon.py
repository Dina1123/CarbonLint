"""Carbon estimator — profiles code execution and estimates energy/CO₂ emissions."""

from __future__ import annotations

from typing import Union

from core.models import Metrics, ErrorResponse
from core.profiler import profile_execution


def _estimate_with_codecarbon(execution_time_ms: float) -> tuple[float, float]:
    """Estimate energy_kwh and co2_grams from execution time using CodeCarbon or fallback."""
    try:
        from codecarbon import EmissionsTracker
        import tempfile
        import time as _time

        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = EmissionsTracker(
                output_dir=tmpdir,
                log_level="error",
                save_to_file=False,
                save_to_api=False,
            )
            tracker.start()
            # Simulate the execution duration (capped at 100ms to keep tests fast)
            _time.sleep(min(execution_time_ms / 1000.0, 0.1))
            emissions = tracker.stop()  # returns kg CO2

            if emissions is not None and emissions > 0:
                # Scale emissions to actual execution time
                scale_factor = execution_time_ms / min(execution_time_ms, 100.0)
                co2_grams = emissions * 1000 * scale_factor  # kg -> grams, scaled
                # Estimate energy: typical CPU uses ~15W, scale by actual time
                energy_kwh = (15 * (execution_time_ms / 1000.0)) / (3600 * 1000)
                return energy_kwh, co2_grams
    except Exception:
        pass

    # Fallback: estimate based on execution time
    # Assume average CPU power of 15W, carbon intensity of 475 gCO2/kWh (global average)
    execution_time_s = execution_time_ms / 1000.0
    energy_kwh = (15 * execution_time_s) / (3600 * 1000)  # 15W * time / (W*s per kWh)
    co2_grams = energy_kwh * 475  # gCO2/kWh global average
    return energy_kwh, co2_grams


def estimate_carbon(code: str, timeout_s: float = 5.0) -> Union[Metrics, ErrorResponse]:
    """Profile code execution and estimate carbon emissions."""
    profile = profile_execution(code, timeout_s=timeout_s)
    if isinstance(profile, ErrorResponse):
        return profile

    energy_kwh, co2_grams = _estimate_with_codecarbon(profile["execution_time_ms"])

    return Metrics(
        execution_time_ms=profile["execution_time_ms"],
        memory_used_bytes=profile["memory_used_bytes"],
        energy_kwh=energy_kwh,
        co2_grams=co2_grams,
    )
