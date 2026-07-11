from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins

from bunnyland_postsim import (
    BulletinBoardComponent,
    BulletinNoticeComponent,
    CourierComponent,
    GazetteComponent,
    GossipSheetComponent,
    LetterComponent,
    MailboxComponent,
    MailInTransitComponent,
    NewsdeskComponent,
    ParcelComponent,
    PostedBy,
    PostGenerationEnricher,
    Reports,
    bulletin_fragments,
    install_gazette,
    install_postsim,
    postsim_fragments,
)
from bunnyland_postsim.plugin import PLUGIN_ID
from bunnyland_postsim.plugin import bunnyland_plugins as _plugins


def test_plugin_loads_with_module_qualified_id():
    plugins = _plugins()
    assert [p.id for p in plugins] == [PLUGIN_ID]


def test_plugin_declares_its_contributions():
    plugin = _plugins()[0]
    for component in (
        LetterComponent,
        ParcelComponent,
        MailInTransitComponent,
        MailboxComponent,
        CourierComponent,
        GazetteComponent,
        NewsdeskComponent,
        GossipSheetComponent,
        BulletinBoardComponent,
        BulletinNoticeComponent,
    ):
        assert component in plugin.ecs.components
    assert Reports in plugin.ecs.edges
    assert PostedBy in plugin.ecs.edges
    assert PostGenerationEnricher in [type(item) for item in plugin.content.generation_enrichers]
    assert postsim_fragments in plugin.content.prompt_fragments
    assert bulletin_fragments in plugin.content.prompt_fragments


def test_plugin_version():
    plugin = _plugins()[0]
    assert plugin.version == "0.2.0"


def test_plugin_recommends_wildsim_synergy():
    plugin = _plugins()[0]
    assert "bunnyland.wildsim" in plugin.dependencies.recommends


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(_plugins(), actor)
    assert applied[0].id == PLUGIN_ID
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {
        "write-letter",
        "send-parcel",
        "check-mail",
        "post-notice",
        "read-board",
    } <= command_types


def test_plugin_installs_both_service_factories():
    plugin = _plugins()[0]
    assert install_postsim in plugin.runtime.service_factories
    assert install_gazette in plugin.runtime.service_factories


def test_plugin_typed_events_registered():
    plugin = _plugins()[0]
    names = {event.__name__ for event in plugin.commands.typed_events}
    assert {"GazettePublishedEvent", "NoticePostedEvent", "BoardReadEvent"} <= names


def test_apply_installs_gazette_press():
    actor = WorldActor()
    apply_plugins(_plugins(), actor)
    presses = list(actor.world.query().with_all([GazetteComponent]).execute_entities())
    assert len(presses) == 1
