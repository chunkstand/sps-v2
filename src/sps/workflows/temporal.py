"""Shared Temporal client helpers.

This module centralizes small pieces of Temporal client wiring so operator tooling
and tests behave consistently with the worker.

Constraints:
- Never log secrets (local dev uses none, but keep the pattern).
- Keep workflow contracts ergonomic: prefer Temporal's Pydantic data converter
  when available.
"""

from __future__ import annotations

from temporalio.client import Client

from sps.config import get_settings


def try_get_pydantic_data_converter():
    """Best-effort Pydantic support for Temporal payload conversion.

    The contrib module path has shifted across Temporal SDK versions. We treat
    this as optional to keep the code resilient.
    """

    try:
        from temporalio.contrib.pydantic import pydantic_data_converter  # type: ignore

        return pydantic_data_converter
    except Exception:
        return None


async def connect_client() -> Client:
    """Connect a Temporal client using Settings defaults."""

    settings = get_settings()
    return await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        data_converter=try_get_pydantic_data_converter(),
    )
