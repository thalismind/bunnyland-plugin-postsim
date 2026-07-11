"""Behaviour tests for the v2 world gossip sheet: history-driven press, newsdesk, storyteller."""

from __future__ import annotations

import sys
import types

from bunnyland.core import (
    IdentityComponent,
    RoomComponent,
    WorldActor,
    container_of,
    spawn_entity,
)
from bunnyland.foundation.history.mechanics import record_world_history
from bunnyland.foundation.storyteller.mechanics import IncidentComponent

from bunnyland_postsim.gazette import (
    GAZETTE_INCIDENT_KIND,
    MAX_NEWSDESK_HEADLINES,
    PARTNER_HEADLINES,
    GazetteConsequence,
    NewsdeskReactor,
    append_breaking,
    ensure_gazette,
    gazette_presses,
    install_gazette,
)
from bunnyland_postsim.gazette_components import (
    MAX_EDITION_HEADLINES,
    GazetteComponent,
    GossipSheetComponent,
    NewsdeskComponent,
    Reports,
)
from bunnyland_postsim.prefabs import spawn_gazette

# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------


def _room(world, title="Town Square"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _seed_history(world, summary, *, event_id, epoch=0, tags=(), event_type="TestEvent"):
    return record_world_history(
        world,
        summary=summary,
        source_event_id=event_id,
        event_type=event_type,
        created_at_epoch=epoch,
        tags=tuple(tags),
    )


def _editions(world):
    return list(world.query().with_all([GossipSheetComponent]).execute_entities())


def _incidents(world, kind):
    return [
        entity
        for entity in world.query().with_all([IncidentComponent]).execute_entities()
        if entity.get_component(IncidentComponent).kind == kind
    ]


# --------------------------------------------------------------------------------------
# ensure / presses
# --------------------------------------------------------------------------------------


def test_ensure_gazette_is_idempotent():
    world = WorldActor().world
    first = ensure_gazette(world)
    second = ensure_gazette(world)
    assert first.id == second.id
    assert len(gazette_presses(world)) == 1


# --------------------------------------------------------------------------------------
# the history-driven path: quiet day vs. with world events
# --------------------------------------------------------------------------------------


def test_quiet_day_publishes_nothing():
    world = WorldActor().world
    _room(world)
    ensure_gazette(world)
    events = GazetteConsequence().process(world, 1)
    assert events == []
    assert _editions(world) == []


def test_world_events_compose_an_edition():
    world = WorldActor().world
    room = _room(world)
    press = ensure_gazette(world)
    _seed_history(world, "A hunter landed a record stag.", event_id="e1", epoch=0)
    _seed_history(world, "The harvest festival opened at dawn.", event_id="e2", epoch=0)

    events = GazetteConsequence().process(world, 0)

    assert len(events) == 1
    published = events[0]
    assert published.edition == 1
    assert published.headline_count == 2
    assert published.scandal is False

    editions = _editions(world)
    assert len(editions) == 1
    sheet = editions[0].get_component(GossipSheetComponent)
    assert "A hunter landed a record stag." in sheet.headlines
    assert "The harvest festival opened at dawn." in sheet.headlines
    assert set(sheet.claim_ids) == {"e1", "e2"}
    # The edition is dropped in a room where any board can read it.
    assert container_of(editions[0]) == room.id
    # Provenance edges link the edition back to the history records it reported.
    reported = list(editions[0].get_relationships(Reports))
    assert len(reported) == 2
    # The press advanced its bookkeeping.
    refreshed = press.get_component(GazetteComponent)
    assert refreshed.edition_seq == 1
    assert refreshed.last_published_epoch == 0


def test_press_does_not_republish_stale_news():
    world = WorldActor().world
    _room(world)
    ensure_gazette(world)
    _seed_history(world, "A quiet bit of news.", event_id="e1", epoch=0)
    consequence = GazetteConsequence()

    assert len(consequence.process(world, 0)) == 1
    # Same epoch again: still within the interval, nothing new.
    assert consequence.process(world, 0) == []
    # Later tick, but no records newer than the last edition.
    assert consequence.process(world, 5) == []
    assert len(_editions(world)) == 1


def test_press_respects_publish_interval():
    world = WorldActor().world
    _room(world)
    spawn_entity(
        world,
        [
            IdentityComponent(name="gossip sheet", kind="gazette"),
            GazetteComponent(interval_ticks=5, last_published_epoch=10),
            NewsdeskComponent(),
        ],
    )
    _seed_history(world, "Breaking mid-interval.", event_id="e1", epoch=11)
    consequence = GazetteConsequence()

    assert consequence.process(world, 12) == []  # 12 < 10 + 5
    assert len(consequence.process(world, 15)) == 1  # interval elapsed


def test_edition_caps_headlines_and_folds_breaking_first():
    world = WorldActor().world
    _room(world)
    press = ensure_gazette(world)
    # Three breaking headlines on the newsdesk...
    for index in range(3):
        append_breaking(world, f"Breaking {index}!", f"b{index}")
    # ...and five history records; the edition is capped at MAX_EDITION_HEADLINES.
    for index in range(5):
        _seed_history(world, f"History item {index}.", event_id=f"h{index}", epoch=index)

    events = GazetteConsequence().process(world, 10)
    assert len(events) == 1
    sheet = _editions(world)[0].get_component(GossipSheetComponent)
    assert len(sheet.headlines) == MAX_EDITION_HEADLINES
    # Breaking headlines lead the edition.
    assert sheet.headlines[:3] == ("Breaking 0!", "Breaking 1!", "Breaking 2!")
    # The newsdesk buffer is cleared once folded into an edition.
    assert press.get_component(NewsdeskComponent).headlines == ()


def test_breaking_only_edition_without_history():
    world = WorldActor().world
    _room(world)
    ensure_gazette(world)
    append_breaking(world, "Extra! Extra!", "b1")
    events = GazetteConsequence().process(world, 3)
    assert len(events) == 1
    sheet = _editions(world)[0].get_component(GossipSheetComponent)
    assert sheet.headlines == ("Extra! Extra!",)
    assert sheet.claim_ids == ()


# --------------------------------------------------------------------------------------
# publish room resolution
# --------------------------------------------------------------------------------------


def test_edition_lands_in_press_home_room_when_set():
    world = WorldActor().world
    other = _room(world, "Alley")
    home = _room(world, "Newsroom")
    spawn_gazette(world, home_room_id=str(home.id))
    _seed_history(world, "Home-room news.", event_id="e1", epoch=0)
    GazetteConsequence().process(world, 0)
    edition = _editions(world)[0]
    assert container_of(edition) == home.id
    assert container_of(edition) != other.id


def test_invalid_home_room_falls_back_to_first_room():
    world = WorldActor().world
    room = _room(world, "Square")
    # home points at a non-room entity -> falls back to the lowest-id room.
    stray = spawn_entity(world, [IdentityComponent(name="cart", kind="item")])
    spawn_gazette(world, home_room_id=str(stray.id))
    _seed_history(world, "Fallback news.", event_id="e1", epoch=0)
    GazetteConsequence().process(world, 0)
    assert container_of(_editions(world)[0]) == room.id


def test_edition_publishes_even_with_no_rooms():
    world = WorldActor().world
    ensure_gazette(world)
    _seed_history(world, "News in the void.", event_id="e1", epoch=0)
    events = GazetteConsequence().process(world, 0)
    assert len(events) == 1
    assert events[0].room_id == ""
    assert container_of(_editions(world)[0]) is None


# --------------------------------------------------------------------------------------
# scandal -> storyteller incident
# --------------------------------------------------------------------------------------


def test_scandal_edition_registers_one_open_incident():
    world = WorldActor().world
    room = _room(world)
    ensure_gazette(world)
    _seed_history(
        world, "A beloved elder passed away.", event_id="e1", epoch=0, tags=("death", "loss")
    )
    events = GazetteConsequence().process(world, 0)
    assert events[0].scandal is True
    incidents = _incidents(world, GAZETTE_INCIDENT_KIND)
    assert len(incidents) == 1
    assert incidents[0].get_component(IncidentComponent).room_id == str(room.id)

    # A second scandal while the first is unresolved must not pile up another incident.
    _seed_history(world, "A scandal at the fair!", event_id="e2", epoch=1, tags=("scandal",))
    GazetteConsequence().process(world, 1)
    assert len(_incidents(world, GAZETTE_INCIDENT_KIND)) == 1


def test_scandal_incident_without_room():
    world = WorldActor().world
    ensure_gazette(world)
    _seed_history(world, "Distant tragedy.", event_id="e1", epoch=0, tags=("loss",))
    GazetteConsequence().process(world, 0)
    incidents = _incidents(world, GAZETTE_INCIDENT_KIND)
    assert len(incidents) == 1
    assert incidents[0].get_component(IncidentComponent).room_id is None


# --------------------------------------------------------------------------------------
# newsdesk buffer
# --------------------------------------------------------------------------------------


def test_append_breaking_dedupes_and_caps():
    world = WorldActor().world
    press = ensure_gazette(world)
    assert append_breaking(world, "First!", "s1") is True
    # Same source id is ignored.
    assert append_breaking(world, "First again!", "s1") is False
    # Blank headline is ignored.
    assert append_breaking(world, "   ", "s2") is False
    # Overflow the buffer; it stays capped and keeps the newest.
    for index in range(MAX_NEWSDESK_HEADLINES + 3):
        append_breaking(world, f"News {index}", f"n{index}")
    desk = press.get_component(NewsdeskComponent)
    assert len(desk.headlines) == MAX_NEWSDESK_HEADLINES
    assert desk.headlines[-1] == f"News {MAX_NEWSDESK_HEADLINES + 2}"


def test_append_breaking_without_press_is_noop():
    world = WorldActor().world
    assert append_breaking(world, "Nobody home.", "s1") is False


# --------------------------------------------------------------------------------------
# optional wildsim synergy (connector)
# --------------------------------------------------------------------------------------


def test_wild_news_events_absent_logs_warning(caplog):
    from bunnyland_postsim.gazette import _wild_news_events

    with caplog.at_level("WARNING"):
        assert _wild_news_events() == ()
    assert any("wildsim" in record.message for record in caplog.records)


def test_wild_news_events_present_when_partner_loaded(monkeypatch):
    fake = types.ModuleType("bunnyland_wildsim")
    events = types.ModuleType("bunnyland_wildsim.events")

    class GameBaggedEvent:
        pass

    class GameTrappedEvent:
        pass

    class PredatorIncursionEvent:
        pass

    events.GameBaggedEvent = GameBaggedEvent
    events.GameTrappedEvent = GameTrappedEvent
    events.PredatorIncursionEvent = PredatorIncursionEvent
    fake.events = events
    monkeypatch.setitem(sys.modules, "bunnyland_wildsim", fake)
    monkeypatch.setitem(sys.modules, "bunnyland_wildsim.events", events)

    from bunnyland_postsim.gazette import _wild_news_events

    assert _wild_news_events() == (GameBaggedEvent, GameTrappedEvent, PredatorIncursionEvent)


def test_newsdesk_reactor_buffers_partner_headline():
    world = WorldActor().world
    press = ensure_gazette(world)
    reactor = NewsdeskReactor(world)

    class GameBaggedEvent:
        event_id = "wild-1"

    reactor._on_partner_event(GameBaggedEvent())
    assert PARTNER_HEADLINES["GameBaggedEvent"] in press.get_component(NewsdeskComponent).headlines


def test_newsdesk_reactor_uses_fallback_headline_for_unknown_event():
    world = WorldActor().world
    press = ensure_gazette(world)
    reactor = NewsdeskReactor(world)

    class MysteryEvent:
        event_id = "x-1"

    reactor._on_partner_event(MysteryEvent())
    headlines = press.get_component(NewsdeskComponent).headlines
    assert any("beyond the walls" in line for line in headlines)


def test_newsdesk_reactor_subscribe_no_partner_is_noop():
    world = WorldActor().world
    subscribed = []

    class FakeBus:
        def subscribe(self, event_type, handler):
            subscribed.append(event_type)

    NewsdeskReactor(world).subscribe(FakeBus())
    assert subscribed == []


def test_newsdesk_reactor_subscribe_with_partner(monkeypatch):
    fake = types.ModuleType("bunnyland_wildsim")
    events = types.ModuleType("bunnyland_wildsim.events")

    class GameBaggedEvent:
        pass

    class GameTrappedEvent:
        pass

    class PredatorIncursionEvent:
        pass

    for cls in (GameBaggedEvent, GameTrappedEvent, PredatorIncursionEvent):
        setattr(events, cls.__name__, cls)
    fake.events = events
    monkeypatch.setitem(sys.modules, "bunnyland_wildsim", fake)
    monkeypatch.setitem(sys.modules, "bunnyland_wildsim.events", events)

    subscribed = []

    class FakeBus:
        def subscribe(self, event_type, handler):
            subscribed.append(event_type)

    world = WorldActor().world
    NewsdeskReactor(world).subscribe(FakeBus())
    assert len(subscribed) == 3


# --------------------------------------------------------------------------------------
# install wiring
# --------------------------------------------------------------------------------------


def test_install_gazette_wires_press_and_consequence():
    actor = WorldActor()
    _room(actor.world)
    install_gazette(actor)
    assert len(gazette_presses(actor.world)) == 1
    _seed_history(actor.world, "Installed news.", event_id="e1", epoch=0)
    # The registered consequence runs on the next tick and publishes.
    events = []
    for consequence in actor._consequences:  # noqa: SLF001 - inspect registered consequences
        events.extend(consequence.process(actor.world, 0))
    assert any(getattr(event, "edition", None) == 1 for event in events)
