"""Runtime wiring: register the postal consequence on a world actor."""

from __future__ import annotations

from bunnyland.core.world_actor import WorldActor

from .couriers import PostConsequence


def install_postsim(actor: WorldActor) -> None:
    """Register the per-tick courier/delivery consequence (a ``service_factories`` entry)."""
    actor.register_consequence(PostConsequence())


__all__ = ["install_postsim"]
