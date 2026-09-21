# systemd deployment

A small, hardened, **periodic batch job**. The simulation has no daemon mode:
a run reads parameters, computes to the end of its horizon, writes a report and
exits. Scheduling it is therefore a `timer` plus a `oneshot` service, not a
long-running unit with a restart policy.

Scope note: this path runs `cs-sim` on a single host and writes Markdown reports
into a state directory. It does not serve HTTP, does not talk to hardware, and
does not send anything anywhere. The API service is a separate concern and is
not installed by these units.

## What it does

| Unit | Role |
| --- | --- |
| `conscious-subconscious.service` | `Type=oneshot`. Runs the `week-long` scenario with `--report`, then a one-factor sensitivity ranking. Both are written to `out/` under the state directory. |
| `conscious-subconscious.timer` | Daily at 03:30 local time, `Persistent=true`, up to 10 minutes of jitter. |

Reports are timestamped by the systemd instance specifier (`%i`), so successive
days produce separate files that can be diffed. Because runs are deterministic,
a diff that is not empty means the code or the parameters changed — which is
precisely the signal worth having.

## Install

```bash
# 1. Service account. No login shell, no home directory contents.
sudo useradd --system \
  --home /var/lib/conscious-subconscious \
  --shell /usr/sbin/nologin \
  conscious-subconscious

# 2. Install the package into a dedicated virtualenv.
sudo python3 -m venv /opt/conscious-subconscious/venv
sudo /opt/conscious-subconscious/venv/bin/python -m pip install \
  /path/to/conscious-subconscious

# 3. Install the units.
sudo install -m 0644 conscious-subconscious.service /etc/systemd/system/
sudo install -m 0644 conscious-subconscious.timer   /etc/systemd/system/
sudo systemctl daemon-reload

# 4. Verify before enabling.
sudo systemctl start conscious-subconscious.service
systemctl status conscious-subconscious.service
sudo journalctl -u conscious-subconscious.service -n 50 --no-pager

# 5. Enable the schedule.
sudo systemctl enable --now conscious-subconscious.timer
systemctl list-timers conscious-subconscious.timer
```

### Paths you must change

- `Environment=CS_VENV=/opt/conscious-subconscious/venv` — point this at wherever
  the package was installed. The `Makefile`'s default `.venv` is a checkout-local
  convenience and is not a suitable deployment location.
- `ExecStart` / `ExecStartPost` — the scenario (`week-long`) and the output paths
  are conventions, not requirements. Any `cs-sim` subcommand works.
- `User=` / `Group=` — if you do not create the `conscious-subconscious` account,
  name an existing unprivileged account instead.

### Hardening already applied in the unit

`ProtectSystem=strict` with a single `ReadWritePaths` entry, `ProtectHome`,
`PrivateTmp`, `PrivateDevices`, `NoNewPrivileges`, an empty
`CapabilityBoundingSet`, `RestrictAddressFamilies=AF_UNIX`, a
`SystemCallFilter` allow-list and `MemoryDenyWriteExecute`. There is no network
address family available, so the job cannot exfiltrate a report even if it wanted
to. If a future version needs to read from a hardware adapter over a serial line
or a BLE socket, that is a deliberate change to this unit's threat model and must
be reviewed, not quietly patched in.

### Output

Reports land in `/var/lib/conscious-subconscious/out/`. The state directory is
created by systemd with mode 0750 and owned by the service account. Nothing in
that directory is uploaded, synced or backed up by this project.

## What has NOT been verified

Stated plainly, because the alternative is a README that implies more testing
than happened:

- **These units have not been executed on a real system by the project.** They are
  written against the documented `cs-sim` interface (`run --scenario ... --report
  --out ...`, `sensitivity --out ...`), which has been exercised locally, but the
  unit files themselves have not been booted and the hardening directives have not
  been confirmed with `systemd-analyze security`.
- **`systemd-analyze security` has not been run** on this unit. Expect a
  non-trivial exposure score anyway; the directives above are a reasonable set,
  not a maximised one.
- **No distribution matrix has been tested.** `SystemCallFilter=@system-service`
  and `StateDirectory=` require systemd 235 or newer; `ProtectProc=invisible`
  and `RestrictSUIDSGID` require newer builds still. On an older systemd, remove
  the unsupported directives rather than deleting the whole hardening block.
- **No SELinux or AppArmor policy is shipped.** `ProtectSystem` and friends are
  not a substitute for a MAC policy.
- **No log rotation, retention or alerting is configured.** `journald` defaults
  apply, and a failed run is visible only to someone who looks.
- **`ExecStartPost` runs only if `ExecStart` succeeds**, so a sensitivity ranking
  is skipped whenever the main run fails. That is intentional, but it means a
  silently absent ranking file is a signal, not a gap.

Nothing here is a medical device, and none of it produces clinical information.
See `DISCLAIMER.md` in the repository root.
