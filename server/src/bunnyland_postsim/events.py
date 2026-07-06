"""Domain events emitted by the postal verbs and the courier consequence."""

from __future__ import annotations

from bunnyland.core.events import DomainEvent


class LetterWrittenEvent(DomainEvent):
    """A character wrote a letter (it now sits in their inventory)."""

    mail_id: str
    addressee_id: str


class MailPostedEvent(DomainEvent):
    """A character dropped mail into a mailbox, beginning its journey."""

    mail_id: str
    mailbox_id: str
    addressee_id: str
    is_parcel: bool = False
    is_care_package: bool = False


class MailDeliveredEvent(DomainEvent):
    """A courier delivered mail to its destination mailbox/room."""

    mail_id: str
    addressee_id: str
    room_id_delivered: str
    is_care_package: bool = False


class MailReturnedEvent(DomainEvent):
    """Undeliverable mail bounced back to its sender."""

    mail_id: str
    sender_id: str
    room_id_returned: str


class MailCheckedEvent(DomainEvent):
    """A character collected delivered mail addressed to them from a mailbox."""

    mailbox_id: str
    mail_ids: tuple[str, ...] = ()


class GazettePublishedEvent(DomainEvent):
    """The gossip-sheet press published a new edition from the world's news."""

    gazette_id: str
    edition: int
    headline_count: int
    scandal: bool = False


class NoticePostedEvent(DomainEvent):
    """A character pinned a notice to a bulletin board."""

    notice_id: str
    board_id: str
    author_id: str


class BoardReadEvent(DomainEvent):
    """A character read a bulletin board (latest gossip-sheet edition + local notices)."""

    board_id: str
    edition: int = 0
    notice_count: int = 0


__all__ = [
    "BoardReadEvent",
    "GazettePublishedEvent",
    "LetterWrittenEvent",
    "MailCheckedEvent",
    "MailDeliveredEvent",
    "MailPostedEvent",
    "MailReturnedEvent",
    "NoticePostedEvent",
]
