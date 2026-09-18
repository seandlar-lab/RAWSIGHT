from __future__ import annotations

import ctypes
import os
import platform
from pathlib import Path


def _safe_fraction(
    numerator: int | None,
    denominator: int | None,
) -> float | None:
    if (
        numerator is None
        or denominator is None
        or denominator <= 0
    ):
        return None

    return numerator / denominator


def _inspect_windows_memory() -> dict:
    """
    Read physical-memory information from Windows.

    GlobalMemoryStatusEx reports the memory state at the time of
    inspection. No judgment about whether an analysis should run is
    made here.
    """

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)

    success = ctypes.windll.kernel32.GlobalMemoryStatusEx(
        ctypes.byref(status)
    )

    if not success:
        raise OSError(
            "GlobalMemoryStatusEx failed"
        )

    total = int(status.ullTotalPhys)
    available = int(status.ullAvailPhys)

    return {
        "status": "measured",
        "source": "windows_GlobalMemoryStatusEx",
        "total_memory_bytes": total,
        "available_memory_bytes": available,
        "used_memory_bytes": total - available,
        "available_fraction": _safe_fraction(
            available,
            total,
        ),
        "reported_memory_load_percent": int(
            status.dwMemoryLoad
        ),
    }


def _inspect_linux_memory() -> dict:
    """
    Read physical-memory information from /proc/meminfo.

    MemAvailable is preferred because it estimates how much memory
    can be allocated without swapping.
    """

    meminfo_path = Path("/proc/meminfo")

    if not meminfo_path.exists():
        raise OSError(
            "/proc/meminfo is not available"
        )

    values: dict[str, int] = {}

    for line in meminfo_path.read_text(
        encoding="utf-8"
    ).splitlines():
        if ":" not in line:
            continue

        key, raw_value = line.split(
            ":",
            1,
        )

        parts = raw_value.strip().split()

        if not parts:
            continue

        try:
            value = int(parts[0])
        except ValueError:
            continue

        values[key] = value * 1024

    total = values.get("MemTotal")
    available = values.get(
        "MemAvailable"
    )

    if total is None:
        raise OSError(
            "MemTotal is missing from /proc/meminfo"
        )

    used = (
        total - available
        if available is not None
        else None
    )

    return {
        "status": (
            "measured"
            if available is not None
            else "partial"
        ),
        "source": "linux_proc_meminfo",
        "total_memory_bytes": total,
        "available_memory_bytes": available,
        "used_memory_bytes": used,
        "available_fraction": _safe_fraction(
            available,
            total,
        ),
        "reported_memory_load_percent": (
            (
                round(
                    (used / total) * 100,
                    2,
                )
                if used is not None
                and total > 0
                else None
            )
        ),
    }


def _inspect_posix_total_memory() -> dict:
    """
    Portable fallback for POSIX-like systems.

    This fallback can usually determine installed physical memory but
    not the currently available memory. That limitation is explicit in
    the returned status.
    """

    page_size_names = (
        "SC_PAGE_SIZE",
        "SC_PAGESIZE",
    )

    page_size = None

    for name in page_size_names:
        try:
            page_size = os.sysconf(name)
            break
        except (
            AttributeError,
            OSError,
            ValueError,
        ):
            continue

    try:
        physical_pages = os.sysconf(
            "SC_PHYS_PAGES"
        )
    except (
        AttributeError,
        OSError,
        ValueError,
    ):
        physical_pages = None

    if (
        page_size is None
        or physical_pages is None
    ):
        raise OSError(
            "Physical memory could not be determined"
        )

    total = int(
        page_size * physical_pages
    )

    return {
        "status": "partial",
        "source": "posix_sysconf",
        "total_memory_bytes": total,
        "available_memory_bytes": None,
        "used_memory_bytes": None,
        "available_fraction": None,
        "reported_memory_load_percent": None,
    }


def inspect_memory_resources() -> dict:
    """
    Inspect the current machine's physical-memory resources.

    The function reports observed resource state only. It does not set
    dataset-size limits, batch sizes, or decide whether an analysis
    should run.
    """

    system = platform.system().lower()

    try:
        if system == "windows":
            memory = _inspect_windows_memory()

        elif system == "linux":
            memory = _inspect_linux_memory()

        elif os.name == "posix":
            memory = _inspect_posix_total_memory()

        else:
            raise OSError(
                "No memory provider is available "
                f"for platform: {system}"
            )

    except Exception as error:
        memory = {
            "status": "unavailable",
            "source": None,
            "total_memory_bytes": None,
            "available_memory_bytes": None,
            "used_memory_bytes": None,
            "available_fraction": None,
            "reported_memory_load_percent": None,
            "error": str(error),
        }

    return {
        "platform": system,
        "memory": memory,
    }


def compare_working_set_to_available_memory(
    estimated_peak_bytes: int,
    resource_snapshot: dict | None = None,
) -> dict:
    """
    Compare an externally estimated peak working set with currently
    available physical memory.

    This comparison is factual rather than policy-based. It does not
    introduce arbitrary warning thresholds. A later execution-policy
    layer can decide how much headroom it requires and whether user
    confirmation is appropriate.
    """

    if estimated_peak_bytes < 0:
        raise ValueError(
            "estimated_peak_bytes must not be negative"
        )

    snapshot = (
        resource_snapshot
        if resource_snapshot is not None
        else inspect_memory_resources()
    )

    memory = snapshot.get(
        "memory",
        {},
    )

    available = memory.get(
        "available_memory_bytes"
    )

    if not isinstance(available, int):
        return {
            "status": "not_comparable",
            "estimated_peak_bytes": (
                estimated_peak_bytes
            ),
            "available_memory_bytes": (
                available
            ),
            "fits_currently_available_memory": None,
            "headroom_bytes": None,
            "estimated_fraction_of_available": None,
            "basis": (
                "available_memory_not_measured"
            ),
        }

    headroom = (
        available - estimated_peak_bytes
    )

    return {
        "status": "compared",
        "estimated_peak_bytes": (
            estimated_peak_bytes
        ),
        "available_memory_bytes": available,
        "fits_currently_available_memory": (
            estimated_peak_bytes
            <= available
        ),
        "headroom_bytes": headroom,
        "estimated_fraction_of_available": (
            _safe_fraction(
                estimated_peak_bytes,
                available,
            )
        ),
        "basis": (
            "estimated_peak_vs_current_available_memory"
        ),
    }
