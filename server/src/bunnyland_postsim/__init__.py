"""Out-of-tree Bunnyland plugin: letters, parcels, mailboxes, and couriers.

Adds asynchronous messaging that travels the world graph over time. A character can
``write-letter`` and ``send-parcel`` (optionally wrapping a gift or care package) into a
mailbox; a :class:`CourierComponent` NPC carries it room-to-room over ticks and drops it in the
addressee's mailbox, where they ``check-mail`` to collect it. Undeliverable mail returns to its
sender, and a delivered care package warms the recipient's mood and the two-way social bond.
"""

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
    LetterWrittenEvent,
    MailCheckedEvent,
    MailDeliveredEvent,
    MailPostedEvent,
    MailReturnedEvent,
)
from .fragments import postsim_fragments
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
from .prefabs import spawn_courier, spawn_letter, spawn_mailbox, spawn_parcel
from .return_to_sender import begin_return, is_timed_out, is_unroutable, should_return
from .routing import next_hop, next_hop_to_any
from .spatial import holder_of, move_entity, room_of

__all__ = [
    "DEFAULT_TTL_TICKS",
    "LETTER_ACTION_DEFINITIONS",
    "LETTER_ACTION_HANDLERS",
    "MAILBOX_ACTION_DEFINITIONS",
    "MAILBOX_ACTION_HANDLERS",
    "PLUGIN_ID",
    "CheckMailHandler",
    "CourierComponent",
    "LetterComponent",
    "LetterWrittenEvent",
    "MailboxComponent",
    "MailCheckedEvent",
    "MailDeliveredEvent",
    "MailInTransitComponent",
    "MailPostedEvent",
    "MailReturnedEvent",
    "ParcelComponent",
    "PostConsequence",
    "PostWorldgenHook",
    "SendParcelHandler",
    "WriteLetterHandler",
    "apply_care_package_delivery",
    "begin_return",
    "bunnyland_plugins",
    "delivered_mail_for",
    "holder_of",
    "install_postsim",
    "is_timed_out",
    "is_unroutable",
    "mail_in_mailbox",
    "mailbox_in_room",
    "mailboxes_in_room",
    "move_entity",
    "next_hop",
    "next_hop_to_any",
    "plugin",
    "postsim_fragments",
    "raise_affect",
    "room_of",
    "should_return",
    "spawn_courier",
    "spawn_letter",
    "spawn_mailbox",
    "spawn_parcel",
    "warm_bond",
]
