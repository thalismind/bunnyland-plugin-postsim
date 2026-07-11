"""Declarative world-generation plans for settlement postal infrastructure."""

from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainerComponent,
    ContainmentMode,
    Contains,
    GenerationChild,
    GenerationDelta,
    GenerationRequest,
    IdentityComponent,
)

from .components import CourierComponent, MailboxComponent
from .gazette_components import BulletinBoardComponent, GazetteComponent, NewsdeskComponent

SETTLEMENT_TERMS = (
    "town",
    "village",
    "city",
    "hamlet",
    "settlement",
    "outpost",
    "post",
    "hub",
    "market",
    "square",
    "camp",
    "inn",
    "tavern",
    "waystation",
    "station",
    "harbor",
    "harbour",
    "port",
    "plaza",
)


def _is_settlement(request: GenerationRequest) -> bool:
    text = " ".join((request.source_key, request.description, *request.tags)).casefold()
    return request.entity_kind == "room" and any(term in text for term in SETTLEMENT_TERMS)


def _child(
    request: GenerationRequest,
    key: str,
    kind: str,
    components: tuple,
    *,
    singleton_key: str | None = None,
) -> GenerationChild:
    return GenerationChild(
        request=GenerationRequest(
            entity_kind=kind,
            description=key.replace("-", " "),
            source_seed=request.source_seed,
            source_key=f"{request.source_key}:{key}",
            tags=("postsim",),
        ),
        parent_edge=Contains(mode=ContainmentMode.ROOM_CONTENT),
        components=components,
        singleton_key=singleton_key,
    )


class PostGenerationEnricher:
    capabilities: tuple[str, ...] = ()

    def enrich(self, request: GenerationRequest) -> GenerationDelta:
        if not _is_settlement(request):
            return GenerationDelta()
        return GenerationDelta(
            children=(
                _child(
                    request,
                    "mailbox",
                    "mailbox",
                    (
                        IdentityComponent(name="mailbox", kind="mailbox", tags=("postsim",)),
                        ContainerComponent(),
                        MailboxComponent(),
                    ),
                ),
                _child(
                    request,
                    "bulletin-board",
                    "bulletin-board",
                    (
                        IdentityComponent(
                            name="bulletin board",
                            kind="bulletin-board",
                            tags=("postsim",),
                        ),
                        ContainerComponent(),
                        BulletinBoardComponent(),
                    ),
                ),
                _child(
                    request,
                    "courier",
                    "character",
                    (
                        IdentityComponent(name="courier", kind="character", tags=("postsim",)),
                        CharacterComponent(),
                        CourierComponent(),
                    ),
                    singleton_key="bunnyland.postsim.courier",
                ),
                _child(
                    request,
                    "gossip-sheet",
                    "gazette",
                    (
                        IdentityComponent(name="gossip sheet", kind="gazette", tags=("postsim",)),
                        GazetteComponent(name="gossip sheet"),
                        NewsdeskComponent(),
                    ),
                    singleton_key="bunnyland.postsim.gazette",
                ),
            )
        )


__all__ = ["PostGenerationEnricher", "SETTLEMENT_TERMS"]
