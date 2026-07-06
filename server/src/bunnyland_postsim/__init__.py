"""Out-of-tree Bunnyland plugin: letters, mailboxes, couriers, and a world gossip sheet.

The v1 layer adds asynchronous messaging that travels the world graph over time: a character can
``write-letter`` and ``send-parcel`` (optionally wrapping a gift or care package) into a
mailbox; a :class:`CourierComponent` NPC carries it room-to-room over ticks and drops it in the
addressee's mailbox, where they ``check-mail`` to collect it. Undeliverable mail returns to its
sender, and a delivered care package warms the recipient's mood and the two-way social bond.

The v2 layer turns the pack into a town-crier for the whole world: a :class:`GazetteComponent`
press reads the shared **world history** stream and publishes editions of a
:class:`GossipSheetComponent` gossip sheet, which characters read at :class:`BulletinBoardComponent`
boards (``read-board``) and add their own notices to (``post-notice``). A scandalous edition
registers a core storyteller incident, and optional wildsim events flavour the breaking news.
"""

from .bulletins import (
    BULLETIN_ACTION_DEFINITIONS,
    BULLETIN_ACTION_HANDLERS,
    PostNoticeHandler,
    ReadBoardHandler,
    board_in_room,
    boards_in_room,
    latest_edition,
    notices_on_board,
)
from .care_packages import apply_care_package_delivery, raise_affect, warm_bond
from .components import (
    DEFAULT_TTL_TICKS,
    CourierComponent,
    LetterComponent,
    MailboxComponent,
    MailInTransitComponent,
    ParcelComponent,
)
from .couriers import PostConsequence
from .enrichment import PostWorldgenHook
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
from .gazette import (
    GazetteConsequence,
    NewsdeskReactor,
    append_breaking,
    ensure_gazette,
    gazette_presses,
    install_gazette,
)
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
from .letters import (
    LETTER_ACTION_DEFINITIONS,
    LETTER_ACTION_HANDLERS,
    SendParcelHandler,
    WriteLetterHandler,
)
from .mailboxes import (
    MAILBOX_ACTION_DEFINITIONS,
    MAILBOX_ACTION_HANDLERS,
    CheckMailHandler,
    delivered_mail_for,
    mail_in_mailbox,
    mailbox_in_room,
    mailboxes_in_room,
)
from .plugin import PLUGIN_ID, bunnyland_plugins, plugin
from .prefabs import (
    spawn_bulletin_board,
    spawn_courier,
    spawn_gazette,
    spawn_letter,
    spawn_mailbox,
    spawn_parcel,
)
from .return_to_sender import begin_return, is_timed_out, is_unroutable, should_return
from .routing import next_hop, next_hop_to_any
from .spatial import holder_of, move_entity, room_of

__all__ = [
    "BULLETIN_ACTION_DEFINITIONS",
    "BULLETIN_ACTION_HANDLERS",
    "DEFAULT_TTL_TICKS",
    "LETTER_ACTION_DEFINITIONS",
    "LETTER_ACTION_HANDLERS",
    "MAILBOX_ACTION_DEFINITIONS",
    "MAILBOX_ACTION_HANDLERS",
    "PLUGIN_ID",
    "BoardReadEvent",
    "BulletinBoardComponent",
    "BulletinNoticeComponent",
    "CheckMailHandler",
    "CourierComponent",
    "GazetteComponent",
    "GazetteConsequence",
    "GazettePublishedEvent",
    "GossipSheetComponent",
    "LetterComponent",
    "LetterWrittenEvent",
    "MailboxComponent",
    "MailCheckedEvent",
    "MailDeliveredEvent",
    "MailInTransitComponent",
    "MailPostedEvent",
    "MailReturnedEvent",
    "NewsdeskComponent",
    "NewsdeskReactor",
    "NoticePostedEvent",
    "ParcelComponent",
    "PostConsequence",
    "PostNoticeHandler",
    "PostWorldgenHook",
    "PostedBy",
    "ReadBoardHandler",
    "Reports",
    "SendParcelHandler",
    "WriteLetterHandler",
    "append_breaking",
    "apply_care_package_delivery",
    "begin_return",
    "board_in_room",
    "boards_in_room",
    "bulletin_fragments",
    "bunnyland_plugins",
    "delivered_mail_for",
    "ensure_gazette",
    "gazette_presses",
    "holder_of",
    "install_gazette",
    "install_postsim",
    "is_timed_out",
    "is_unroutable",
    "latest_edition",
    "mail_in_mailbox",
    "mailbox_in_room",
    "mailboxes_in_room",
    "move_entity",
    "next_hop",
    "next_hop_to_any",
    "notices_on_board",
    "plugin",
    "postsim_fragments",
    "raise_affect",
    "room_of",
    "should_return",
    "spawn_bulletin_board",
    "spawn_courier",
    "spawn_gazette",
    "spawn_letter",
    "spawn_mailbox",
    "spawn_parcel",
    "warm_bond",
]
