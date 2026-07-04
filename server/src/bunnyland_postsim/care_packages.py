"""Care packages: the warm-fuzzy effect a gift parcel has when it is delivered.

A parcel flagged ``care_package`` does more than arrive: delivering it lifts the recipient's
mood and warms the social bond in *both* directions between sender and recipient. This module
owns that effect so the courier consequence can simply call
:func:`apply_care_package_delivery` when it drops a care package at its destination.

The affect bump is a small, clamped rise in ``valence`` (the pleasant/unpleasant mood axis);
the bond warms via the shared :func:`bunnyland.mechanics.social.adjust_bond` so a care package
reads exactly like a kind gesture between two characters.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import AffectComponent
from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.mechanics.social import adjust_bond
from relics import World

#: How much a delivered care package lifts the recipient's valence, clamped to the axis range.
CARE_PACKAGE_VALENCE = 0.2
#: Ceiling for the affect valence axis (mirrors the wider affect model's [-1, 1] convention).
_VALENCE_CEILING = 1.0
#: How the sender <-> recipient social bond warms on delivery (applied both directions).
CARE_PACKAGE_BOND = {"affinity": 0.12, "trust": 0.05}


def raise_affect(world: World, character_id, amount: float = CARE_PACKAGE_VALENCE) -> bool:
    """Lift ``character_id``'s mood valence by ``amount`` (clamped). Returns whether it applied."""
    parsed = parse_entity_id(str(character_id))
    if parsed is None or not world.has_entity(parsed):
        return False
    character = world.get_entity(parsed)
    if not character.has_component(AffectComponent):
        return False
    affect = character.get_component(AffectComponent)
    new_valence = min(_VALENCE_CEILING, affect.current.valence + amount)
    if new_valence == affect.current.valence:
        return False
    replace_component(
        character,
        replace(affect, current=replace(affect.current, valence=new_valence)),
    )
    return True


def warm_bond(world: World, sender_id: str, recipient_id: str) -> bool:
    """Warm the sender <-> recipient bond both ways. Returns whether both endpoints existed."""
    sender = parse_entity_id(sender_id)
    recipient = parse_entity_id(recipient_id)
    if sender is None or recipient is None or sender == recipient:
        return False
    if not world.has_entity(sender) or not world.has_entity(recipient):
        return False
    adjust_bond(world, sender, recipient, CARE_PACKAGE_BOND)
    adjust_bond(world, recipient, sender, CARE_PACKAGE_BOND)
    return True


def apply_care_package_delivery(world: World, sender_id: str, recipient_id: str) -> None:
    """Apply the full care-package delivery effect: recipient affect + a two-way bond warmth."""
    raise_affect(world, recipient_id)
    warm_bond(world, sender_id, recipient_id)


__all__ = [
    "CARE_PACKAGE_BOND",
    "CARE_PACKAGE_VALENCE",
    "apply_care_package_delivery",
    "raise_affect",
    "warm_bond",
]
