# bunnyland-postsim (server plugin)

The out-of-tree Bunnyland plugin package `bunnyland_postsim`.

## Development

Tests run against a sibling `bunnyland-server` checkout without installing anything —
`tests/conftest.py` puts both this package's `src/` and `../bunnyland-server/src` on
`sys.path`. From this `server/` directory:

```bash
# uses the sibling bunnyland-server's virtualenv/deps
uv run --project ../../bunnyland-server -m pytest
# or, if bunnyland + relics are already importable:
python -m pytest
```

Lint:

```bash
uv run --project ../../bunnyland-server ruff check src tests
```

## Loading into the server

```bash
bunnyland serve --module bunnyland_postsim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported.

## What it contributes

- **Components** — `LetterComponent`, `ParcelComponent`, `MailInTransitComponent`,
  `MailboxComponent`, `CourierComponent`.
- **A courier consequence** (`PostConsequence`) that ages in-transit mail, walks couriers one
  room-hop per tick along a deterministic BFS over `ExitTo`, and delivers mail into the
  addressee's mailbox — emitting `MailDeliveredEvent`/`MailReturnedEvent` and a
  `ControllerOutboxMessageComponent` notice.
- **Prompt fragments** (`postsim_fragments`) reporting mail waiting in the room's mailbox.
- **A worldgen hook** (`PostWorldgenHook`) placing a mailbox in generated settlements and a
  courier in the first one.
- **Three verbs** — `write-letter`, `send-parcel`, `check-mail` — usable by any character.
- **Spawn factories** — `spawn_mailbox`, `spawn_courier`, `spawn_letter`, `spawn_parcel`.

### Mechanics detail

- **Letters & parcels** — `write-letter` spawns a `LetterComponent` item in your inventory;
  `send-parcel` attaches a `MailInTransitComponent` (routing + return-to-sender state), moves
  the letter into a mailbox, and optionally wraps a held gift item as a `ParcelComponent`.
- **Care packages** — delivering a `care_package` parcel raises the recipient's affect
  `valence` and warms the sender <-> recipient `SocialBond` both directions.
- **Return to sender** — `should_return` bounces mail that has outlived `ttl_ticks` or whose
  destination is unreachable; the courier carries it home and re-addresses it to the sender.
