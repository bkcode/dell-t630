# Penpot supervision failure-evidence candidate

2026-11-11, Asia/Shanghai. **Offline candidate artifact; server deployment is tracked separately by the parent.** This now
combines bounded failure evidence with the fixed DNS init-reaper deployment
policy. Parent-observed DNS zombies identify the compose `init: true` change;
this candidate alone does not change compose or make the old DNS process reap.
Base is the exact VM250 public supervisor capture with SHA256
`fdd384bf5470890eb1802cc2eacb49bcc0c0d96013cfe57b257c5021af3b0448`.
It preserves the actual `192.168.19.50` identity and reads Git HEAD from the
existing deployment lock. It does not touch Penpot Git, images, credentials,
design data, fill UI, health status predicates, thresholds, PID limits, timings,
or restart policy. Only `penpot-dns` now requires the lock policy
`require_init: true` and actual `HostConfig.Init` exactly true. Missing, false,
null and truthy non-booleans fail with `DNS-init-reaper-required`; no other
service gains a new init requirement.

The normal Docker frame gains only `failing_streak` and `init`. Init uses the
optional-key-safe Go template `{{json (index .HostConfig "Init")}}`: Docker can
omit that key on existing containers, in which case the scan must receive JSON
null instead of failing before compose can recreate DNS. The first dot-lookup
candidate failed this native prestart scan; parent restored the original source
and service before a separately checked second attempt. The offline regression
now fixes the safe template and covers missing, null and true inputs; native Go
rendering and eleven-container scans are proven by the parent's separate checks.
Before `stop_group`, a
failure records the last frame already collected for validation, its UTC capture
time, exception class, fixed failure reason code and a strictly filtered set of
known-service status fields. No extra Docker calls are made while recording.
If a scan itself failed, this can be an older frame; `frame_available` and
`frame_observed_at_utc` keep that limitation explicit. The listed unhealthy,
stopped or DNS-init-policy violating services are observed symptoms, not a claim
about a new root cause.

The persistent sink is `/var/lib/dell-penpot-supervision`, root-owned `0700`.
Only `failures.jsonl`, `.1`, and `.2` are managed, root-owned `0600`, at most
64 KiB each (192 KiB total data); a single record is capped to 8 KiB. Symlinks,
hard links, wrong ownership/modes and oversized existing files are rejected,
not repaired or truncated. The oldest own archive is removed only during
bounded rotation; unrelated files and journals remain untouched. A partial
append attempts to restore the prior length before emitting a fixed warning.

Journal output is limited to UTC time, exception class, sanitized fixed reason
and known failed-service names. Non-Failure text is always `details-suppressed`;
unrecognized Failure arguments are not persisted. Logging errors emit a fixed
warning and do not replace the original failure or bypass its stop path. File
I/O is synchronous; the candidate bounds data, not arbitrary filesystem stalls.

Tests use temporary user-owned directories by patching only the diagnostic owner
constant; production defaults remain UID0. All original fourteen assertion
methods run unchanged against the candidate; only their shared DNS fixture adds
init true and the policy marker. The current 38 tests include metadata redaction,
malicious exception strings, secure filesystem rejection, rotation, partial
writes, record-before-stop, clean SIGTERM and DNS true/missing/false/null cases.
The two new DNS guard if-statements are matched exactly and removed only for AST
comparison against baseline; every remaining load/validation statement is
unchanged. Other guard/monitor/remediation functions match baseline AST directly.
The scan AST differs only in its two permitted format fields.

```sh
python3 -m unittest discover -s completion/20261111-penpot-hourly/tests -v
```

Adoption remains a parent/root decision after actual offender evidence exists.
Do not upload this file over a running hash-locked supervisor: any approved
installation must use the existing controlled maintenance procedure and update
only the corresponding public SHA lock entries, the DNS `require_init` policy
and matching compose DNS `init: true`. No installation or Git command is
included in this candidate.
