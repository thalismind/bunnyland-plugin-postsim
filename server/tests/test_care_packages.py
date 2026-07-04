from __future__ import annotations

from bunnyland.core import (
    AffectComponent,
    AffectVector,
    CharacterComponent,
    ContainmentMode,
    Contains,
    ExitTo,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.mechanics.social import bond_between

from bunnyland_postsim import (
    PostConsequence,
    apply_care_package_delivery,
    raise_affect,
    spawn_courier,
    spawn_mailbox,
    spawn_parcel,
    warm_bond,
)
from bunnyland_postsim.components import MailInTransitComponent


def _character(world, name, *, affect=False):
    components = [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    if affect:
        components.append(AffectComponent())
    return spawn_entity(world, components)


def test_raise_affect_lifts_valence_for_a_character_with_affect():
    actor = WorldActor()
    recipient = _character(actor.world, "Kell", affect=True)

    assert raise_affect(actor.world, recipient.id) is True
    assert actor.world.get_entity(recipient.id).get_component(AffectComponent).current.valence > 0.0


def test_raise_affect_is_clamped_to_the_ceiling():
    actor = WorldActor()
    recipient = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="Kell", kind="character"),
            CharacterComponent(),
            AffectComponent(current=AffectVector(valence=0.95)),
        ],
    )
    raise_affect(actor.world, recipient.id, amount=0.2)
    valence = actor.world.get_entity(recipient.id).get_component(AffectComponent).current.valence
    assert valence == 1.0


def test_raise_affect_skips_characters_without_affect():
    actor = WorldActor()
    recipient = _character(actor.world, "Kell", affect=False)
    assert raise_affect(actor.world, recipient.id) is False


def test_warm_bond_creates_a_two_way_bond():
    actor = WorldActor()
    sender = _character(actor.world, "Vin")
    recipient = _character(actor.world, "Kell")

    assert warm_bond(actor.world, str(sender.id), str(recipient.id)) is True
    assert bond_between(actor.world, sender.id, recipient.id).affinity > 0.0
    assert bond_between(actor.world, recipient.id, sender.id).affinity > 0.0


def test_warm_bond_ignores_self_addressed_mail():
    actor = WorldActor()
    solo = _character(actor.world, "Vin")
    assert warm_bond(actor.world, str(solo.id), str(solo.id)) is False


def test_apply_care_package_delivery_does_both():
    actor = WorldActor()
    sender = _character(actor.world, "Vin")
    recipient = _character(actor.world, "Kell", affect=True)

    apply_care_package_delivery(actor.world, str(sender.id), str(recipient.id))

    assert actor.world.get_entity(recipient.id).get_component(AffectComponent).current.valence > 0.0
    assert bond_between(actor.world, sender.id, recipient.id).affinity > 0.0


def test_delivered_care_package_warms_recipient_through_the_consequence():
    actor = WorldActor()
    a = spawn_entity(actor.world, [RoomComponent(title="Post Office")])
    c = spawn_entity(actor.world, [RoomComponent(title="Cottage")])
    a.add_relationship(ExitTo(direction="out"), c.id)
    c.add_relationship(ExitTo(direction="back"), a.id)
    box_a = spawn_mailbox(actor.world, room_id=a.id)
    spawn_mailbox(actor.world, room_id=c.id)
    sender = _character(actor.world, "Vin")
    a.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), sender.id)
    recipient = _character(actor.world, "Kell", affect=True)
    c.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), recipient.id)
    spawn_courier(actor.world, room_id=a.id)

    parcel = spawn_parcel(
        actor.world,
        text="thinking of you",
        sender_id=str(sender.id),
        addressee_id=str(recipient.id),
        care_package=True,
    )
    box_a.add_relationship(Contains(mode=ContainmentMode.CONTAINER), parcel.id)
    parcel.add_component(
        MailInTransitComponent(
            sender_id=str(sender.id),
            addressee_id=str(recipient.id),
            origin_room_id=str(a.id),
            destination_room_id=str(c.id),
            current_room_id=str(a.id),
        )
    )

    consequence = PostConsequence()
    for epoch in range(1, 7):
        consequence.process(actor.world, epoch)

    assert not parcel.has_component(MailInTransitComponent)
    assert actor.world.get_entity(recipient.id).get_component(AffectComponent).current.valence > 0.0
    assert bond_between(actor.world, sender.id, recipient.id).affinity > 0.0
