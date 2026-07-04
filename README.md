# Bunnyland Postsim

Out-of-tree [Bunnyland](https://github.com/thalismind/bunnyland-server) plugin that adds
**letters, parcels, and couriers** — asynchronous messaging that travels the world graph over
time instead of teleporting. The cozy connective tissue between characters who are never in the
same room at the same time.

> Write. Send. Wait for the reply.

## Mechanics

- **Letters & parcels** — `write-letter` produces a `LetterComponent` mail item addressed to
  another character; `send-parcel` posts a held letter into a mailbox and can wrap a held gift
  to send along.
- **Mailboxes** — a `MailboxComponent` container per room: mail is dropped in to be sent, and
  delivered mail waits in the addressee's mailbox until they `check-mail`.
- **Couriers** — a `CourierComponent` NPC carries posted mail **across rooms over ticks** via
  the `PostConsequence`, walking a deterministic BFS over `ExitTo` and delivering to the
  addressee's mailbox on arrival.
- **Care packages** — flag a parcel a care package and its delivery raises the recipient's
  affect and warms the sender <-> recipient `SocialBond` both ways.
- **Return to sender** — mail that times out (`ttl_ticks`) or whose destination is unreachable
  bounces back to its sender and is re-addressed so they can collect it.

This repo intentionally keeps all postal work outside the main `bunnyland-server` repo.

## Layout

- `server/` - Python Bunnyland plugin package with the postal components, the courier
  consequence, prompt fragments, a worldgen enrichment hook, the player/AI verbs, spawn
  factories, and tests.

## Server Plugin

The plugin exposes `bunnyland_postsim.bunnyland_plugins()` and contributes:

- `LetterComponent`, `ParcelComponent`, `MailInTransitComponent`, `MailboxComponent`,
  `CourierComponent`.
- `PostConsequence` - advances each in-transit item one room-hop toward its destination every
  tick and delivers on arrival, emitting `MailDeliveredEvent`/`MailReturnedEvent` plus a
  `ControllerOutboxMessageComponent` delivery notice.
- `postsim_fragments` - renders "there is mail in the mailbox" / "a letter for you has arrived"
  into human and AI prompts.
- `PostWorldgenHook` - drops a mailbox into generated settlements and stations a courier.
- `write-letter`, `send-parcel`, and `check-mail` - verbs for characters (human or AI).
- `spawn_mailbox`, `spawn_courier`, `spawn_letter`, `spawn_parcel` - spawn factories.

## Running

This package builds no containers. It is loaded into the stock server via `--module`:

```bash
bunnyland serve --module bunnyland_postsim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported. The
`bunnyland_postsim` package must be importable by the server (installed into the server's
environment, or on `PYTHONPATH`).

## Development

Run server tests against a sibling `bunnyland-server` checkout (no install required —
`server/tests/conftest.py` puts both packages on `sys.path`). From `server/`:

```bash
uv run --project ../../bunnyland-server -m pytest
uv run --project ../../bunnyland-server ruff check src tests
```

See [`server/README.md`](server/README.md) for more detail.

## Contributing & Conduct

This plugin follows the Bunnyland project's
[contribution guidelines](CONTRIBUTING.md) and [code of conduct](CODE_OF_CONDUCT.md),
which point back to the `bunnyland-server` repository.

## License

Licensed under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
