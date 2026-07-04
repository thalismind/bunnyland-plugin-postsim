from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_postsim import (
    CourierComponent,
    LetterComponent,
    MailboxComponent,
    MailInTransitComponent,
    ParcelComponent,
    PostWorldgenHook,
    install_postsim,
    postsim_fragments,
)
from bunnyland_postsim.plugin import PLUGIN_ID


def test_plugin_loads_with_module_qualified_id():
    plugins = load_modules(["bunnyland_postsim"])
    assert [p.id for p in plugins] == [PLUGIN_ID]


def test_plugin_declares_its_contributions():
    plugin = load_modules(["bunnyland_postsim"])[0]
    for component in (
        LetterComponent,
        ParcelComponent,
        MailInTransitComponent,
        MailboxComponent,
        CourierComponent,
    ):
        assert component in plugin.ecs.components
    assert PostWorldgenHook in plugin.content.worldgen_hooks
    assert postsim_fragments in plugin.content.prompt_fragments


def test_plugin_version():
    plugin = load_modules(["bunnyland_postsim"])[0]
    assert plugin.version == "0.1.0"


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(load_modules(["bunnyland_postsim"]), actor)
    assert applied[0].id == PLUGIN_ID
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {"write-letter", "send-parcel", "check-mail"} <= command_types


def test_plugin_installs_courier_consequence():
    plugin = load_modules(["bunnyland_postsim"])[0]
    assert install_postsim in plugin.runtime.service_factories
