"""Bunnyland plugin entrypoint for the out-of-tree postal extension."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    EcsContribution,
    Plugin,
    RuntimeContribution,
)

from .components import (
    CourierComponent,
    LetterComponent,
    MailboxComponent,
    MailInTransitComponent,
    ParcelComponent,
)
from .enrichment import PostWorldgenHook
from .events import (
    LetterWrittenEvent,
    MailCheckedEvent,
    MailDeliveredEvent,
    MailPostedEvent,
    MailReturnedEvent,
)
from .fragments import postsim_fragments
from .install import install_postsim
from .letters import LETTER_ACTION_DEFINITIONS, LETTER_ACTION_HANDLERS
from .mailboxes import MAILBOX_ACTION_DEFINITIONS, MAILBOX_ACTION_HANDLERS

PLUGIN_ID = "bunnyland.postsim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Postsim",
        version="0.1.0",
        default_enabled=True,
        ecs=EcsContribution(
            components=(
                LetterComponent,
                ParcelComponent,
                MailInTransitComponent,
                MailboxComponent,
                CourierComponent,
            ),
        ),
        commands=CommandContribution(
            action_handlers=LETTER_ACTION_HANDLERS + MAILBOX_ACTION_HANDLERS,
            action_definitions=LETTER_ACTION_DEFINITIONS + MAILBOX_ACTION_DEFINITIONS,
            typed_events=(
                LetterWrittenEvent,
                MailPostedEvent,
                MailDeliveredEvent,
                MailReturnedEvent,
                MailCheckedEvent,
            ),
        ),
        runtime=RuntimeContribution(
            service_factories=(install_postsim,),
        ),
        content=ContentContribution(
            prompt_fragments=(postsim_fragments,),
            worldgen_hooks=(PostWorldgenHook,),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
