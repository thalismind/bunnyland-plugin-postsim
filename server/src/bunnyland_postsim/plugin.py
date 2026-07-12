"""Bunnyland plugin entrypoint for the out-of-tree postal extension."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    DependencyContribution,
    EcsContribution,
    Plugin,
    RuntimeContribution,
)

from .bulletins import BULLETIN_ACTION_DEFINITIONS, BULLETIN_ACTION_HANDLERS
from .components import (
    CourierComponent,
    LetterComponent,
    MailboxComponent,
    MailInTransitComponent,
    ParcelComponent,
)
from .enrichment import PostGenerationEnricher
from .events import (
    BoardReadEvent,
    GazettePublishedEvent,
    LetterWrittenEvent,
    MailCheckedEvent,
    MailDeliveredEvent,
    MailPostedEvent,
    MailReturnedEvent,
    NoticePostedEvent,
)
from .fragments import bulletin_fragments, postsim_fragments
from .gazette import install_gazette
from .gazette_components import (
    BulletinBoardComponent,
    BulletinNoticeComponent,
    GazetteComponent,
    GossipSheetComponent,
    NewsdeskComponent,
    PostedBy,
    Reports,
)
from .install import install_postsim
from .integration_3d import install_postsim_3d
from .letters import LETTER_ACTION_DEFINITIONS, LETTER_ACTION_HANDLERS
from .mailboxes import MAILBOX_ACTION_DEFINITIONS, MAILBOX_ACTION_HANDLERS

PLUGIN_ID = "bunnyland.postsim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Postsim",
        version="0.2.0",
        default_enabled=True,
        # Optional synergy: wildsim's hunt/predator events flavour the gossip sheet when present.
        dependencies=DependencyContribution(
            recommends=("bunnyland.wildsim",), integrates_with=("bunnyland.3d",)
        ),
        ecs=EcsContribution(
            components=(
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
            ),
            edges=(Reports, PostedBy),
        ),
        commands=CommandContribution(
            action_handlers=(
                *LETTER_ACTION_HANDLERS,
                *MAILBOX_ACTION_HANDLERS,
                *BULLETIN_ACTION_HANDLERS,
            ),
            action_definitions=(
                *LETTER_ACTION_DEFINITIONS,
                *MAILBOX_ACTION_DEFINITIONS,
                *BULLETIN_ACTION_DEFINITIONS,
            ),
            typed_events=(
                LetterWrittenEvent,
                MailPostedEvent,
                MailDeliveredEvent,
                MailReturnedEvent,
                MailCheckedEvent,
                GazettePublishedEvent,
                NoticePostedEvent,
                BoardReadEvent,
            ),
        ),
        runtime=RuntimeContribution(
            service_factories=(install_postsim, install_gazette),
            integration_factories=(install_postsim_3d,),
        ),
        content=ContentContribution(
            prompt_fragments=(postsim_fragments, bulletin_fragments),
            generation_enrichers=(PostGenerationEnricher(),),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
