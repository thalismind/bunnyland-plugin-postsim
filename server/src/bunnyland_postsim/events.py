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


__all__ = [
    "LetterWrittenEvent",
    "MailCheckedEvent",
    "MailDeliveredEvent",
    "MailPostedEvent",
    "MailReturnedEvent",
]
