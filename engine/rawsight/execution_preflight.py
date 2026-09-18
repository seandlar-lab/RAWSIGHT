from __future__ import annotations

import ctypes
import os
import platform
from pathlib import Path
from typing import Any, Callable, TypeVar


T = TypeVar("T")


def _inspect_windows_process_memory() -> dict[str, Any]:
    """
    Read memory counters for the current Windows process.

    Uses explicit Windows API signatures so HANDLE values and structure
    pointers are passed correctly on both 32-bit and 64-bit Windows.
    """

    from ctypes import wintypes

    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL(
        "kernel32",
        use_last_error=True,
    )
    psapi = ctypes.WinDLL(
        "psapi",
        use_last_error=True,
    )

    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE

    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
        wintypes.DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(
        PROCESS_MEMORY_COUNTERS_EX
    )

    process = kernel32.GetCurrentProcess()

    success = psapi.GetProcessMemoryInfo(
        process,
        ctypes.byref(counters),
        counters.cb,
    )

    if not success:
        error_code = ctypes.get_last_error()

        if error_code:
            raise ctypes.WinError(
                error_code
            )

        raise OSError(
            "GetProcessMemoryInfo failed "
            "without a Windows error code"
        )

    return {
        "status": "measured",
        "source": "windows_GetProcessMemoryInfo",
        "working_set_bytes": int(
            counters.WorkingSetSize
        ),
        "peak_working_set_bytes": int(
            counters.PeakWorkingSetSize
        ),
        "private_usage_bytes": int(
            counters.PrivateUsage
        ),
        "pagefile_usage_bytes": int(
            counters.PagefileUsage
        ),
        "peak_pagefile_usage_bytes": int(
            counters.PeakPagefileUsage
        ),
    }


def _read_linux_status_bytes(
    key: str,
) -> int | None:
    status_path = Path(
        "/proc/self/status"
    )

    if not status_path.exists():
        return None

    prefix = f"{key}:"

    for line in status_path.read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.startswith(prefix):
            continue

        parts = line[len(prefix):].strip().split()

        if not parts:
            return None

        try:
            value = int(parts[0])
        except ValueError:
            return None

        return value * 1024

    return None


def _inspect_linux_process_memory() -> dict[str, Any]:
    """
    Read current and peak resident memory from /proc/self/status.
    """

    working_set = _read_linux_status_bytes(
        "VmRSS"
    )
    peak_working_set = _read_linux_status_bytes(
        "VmHWM"
    )
    virtual_size = _read_linux_status_bytes(
        "VmSize"
    )

    if (
        working_set is None
        and peak_working_set is None
    ):
        raise OSError(
            "Process memory is unavailable "
            "from /proc/self/status"
        )

    return {
        "status": "measured",
        "source": "linux_proc_self_status",
        "working_set_bytes": working_set,
        "peak_working_set_bytes": (
            peak_working_set
        ),
        "private_usage_bytes": None,
        "virtual_size_bytes": virtual_size,
    }


def _inspect_posix_process_memory() -> dict[str, Any]:
    """
    Fallback for POSIX-like systems.

    ru_maxrss is a lifetime peak rather than a current working set.
    The returned status is therefore explicitly partial.
    """

    import resource

    usage = resource.getrusage(
        resource.RUSAGE_SELF
    )

    max_rss = usage.ru_maxrss

    if platform.system().lower() == "darwin":
        peak_bytes = int(max_rss)
    else:
        peak_bytes = int(max_rss * 1024)

    return {
        "status": "partial",
        "source": "posix_getrusage",
        "working_set_bytes": None,
        "peak_working_set_bytes": peak_bytes,
        "private_usage_bytes": None,
    }


def inspect_process_memory() -> dict[str, Any]:
    """
    Inspect memory used by the current RAWSIGHT engine process.

    This function observes process memory only. It does not decide
    whether an analysis should run.
    """

    system = platform.system().lower()

    try:
        if system == "windows":
            memory = (
                _inspect_windows_process_memory()
            )

        elif system == "linux":
            memory = (
                _inspect_linux_process_memory()
            )

        elif os.name == "posix":
            memory = (
                _inspect_posix_process_memory()
            )

        else:
            raise OSError(
                "No process-memory provider is "
                f"available for platform: {system}"
            )

    except Exception as error:
        memory = {
            "status": "unavailable",
            "source": None,
            "working_set_bytes": None,
            "peak_working_set_bytes": None,
            "private_usage_bytes": None,
            "error": str(error),
        }

    return {
        "platform": system,
        "process_memory": memory,
    }


def run_execution_probe(
    probe: Callable[[], T],
) -> tuple[T, dict[str, Any]]:
    """
    Run one caller-supplied probe and record process memory around it.

    The caller decides what constitutes a representative probe.
    This module intentionally does not choose a row count, byte count,
    sample percentage, batch size, or dataset-size threshold.

    The measured peak is the operating system's process-lifetime peak.
    When the probe establishes a new peak, the increase is observable
    exactly. When the process already had a higher peak, no false
    probe-specific peak is inferred.
    """

    before = inspect_process_memory()

    result = probe()

    after = inspect_process_memory()

    before_memory = before.get(
        "process_memory",
        {},
    )
    after_memory = after.get(
        "process_memory",
        {},
    )

    before_working_set = before_memory.get(
        "working_set_bytes"
    )
    after_working_set = after_memory.get(
        "working_set_bytes"
    )

    before_peak = before_memory.get(
        "peak_working_set_bytes"
    )
    after_peak = after_memory.get(
        "peak_working_set_bytes"
    )

    working_set_delta = None

    if (
        isinstance(before_working_set, int)
        and isinstance(after_working_set, int)
    ):
        working_set_delta = (
            after_working_set
            - before_working_set
        )

    new_peak_bytes = None

    if (
        isinstance(before_peak, int)
        and isinstance(after_peak, int)
    ):
        new_peak_bytes = max(
            0,
            after_peak - before_peak,
        )

    measurement = {
        "status": "measured",
        "measurement_basis": "runtime_probe",
        "before": before,
        "after": after,
        "observed_working_set_delta_bytes": (
            working_set_delta
        ),
        "observed_new_process_peak_bytes": (
            new_peak_bytes
        ),
        "limitations": {
            "process_peak_is_lifetime_peak": True,
            "probe_specific_peak_known_only_if_new_peak": True,
        },
    }

    return result, measurement


def build_preflight_report(
    *,
    execution_mode: str,
    streaming_capable: bool | None,
    materialization_required: bool | None,
    probe_measurement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a neutral preflight report.

    This report contains observed execution characteristics and,
    optionally, a runtime-probe measurement. It does not apply warning
    thresholds or decide whether user confirmation is required.
    """

    if not execution_mode:
        raise ValueError(
            "execution_mode must not be empty"
        )

    if (
        streaming_capable is not None
        and not isinstance(
            streaming_capable,
            bool,
        )
    ):
        raise TypeError(
            "streaming_capable must be bool or None"
        )

    if (
        materialization_required is not None
        and not isinstance(
            materialization_required,
            bool,
        )
    ):
        raise TypeError(
            "materialization_required must be "
            "bool or None"
        )

    return {
        "execution_mode": execution_mode,
        "streaming_capable": streaming_capable,
        "materialization_required": (
            materialization_required
        ),
        "probe_measurement": probe_measurement,
    }
