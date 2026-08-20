"""voms.py — VOMS proxy token validation helpers."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class VomsProxyStatus:
    """Result of a VOMS proxy validity check."""

    valid: bool
    message: str


async def check_voms_proxy() -> VomsProxyStatus:
    """Check whether a valid VOMS proxy certificate exists.

    Runs ``voms-proxy-info --exists`` and interprets the exit code.
    Returns a :class:`VomsProxyStatus` with *valid=True* when a valid,
    unexpired proxy is found, and *valid=False* otherwise.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "voms-proxy-info", "--exists",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return VomsProxyStatus(valid=True, message="VOMS proxy is valid.")
        err_text = stderr.decode(errors="replace").strip()
        msg = err_text or "VOMS proxy is missing or has expired."
        return VomsProxyStatus(valid=False, message=msg)
    except FileNotFoundError:
        return VomsProxyStatus(
            valid=False,
            message=(
                "voms-proxy-info not found — cannot verify VOMS proxy. "
                "Please install voms-clients or initialise a proxy with voms-proxy-init."
            ),
        )
    except Exception as exc:
        return VomsProxyStatus(valid=False, message=f"VOMS proxy check failed: {exc}")
