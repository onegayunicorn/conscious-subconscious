# Incident response

Written for a project this size: one maintainer, no on-call rotation, no legal
department and no dedicated security contact. A plan that assumes a team is a plan
that does not get followed, so this one assumes there is one person and that they
may be asleep.

The two incidents most likely to actually happen here are **a leaked credential**
and **a leaked sensor recording**. Both get concrete procedures below.

> **Boundary.** An incident involving this project does not create any clinical
> obligation, because the project has no clinical function. But the reverse is not
> true: if real health data is involved, the operator may have legal obligations
> regardless of what this project does or does not claim. See
> [DISCLAIMER.md](https://github.com/onegayunicorn/conscious-subconscious/blob/main/DISCLAIMER.md).

## 1. Roles

| Role | Who | Responsibility |
| --- | --- | --- |
| **Incident lead** | The maintainer, or whoever is first | Owns the timeline, makes the calls, does not also try to debug |
| **Handler** | The incident lead, in practice, until help arrives | Investigates, contains, remediates |
| **Communicator** | The incident lead | Tells affected parties, files the disclosure, publishes the advisory |
| **Second opinion** | A trusted person outside the project | Reads the draft advisory for accuracy and tone |

Concentrating all four roles in one person is a weakness and it is the honest
starting point at this scale. If an incident exceeds one person, the first useful
action is to recruit the second opinion — someone who can read a security advisory
and tell you it is too vague or too alarming.

**Who to contact, and how:** private vulnerability reporting on the repository
(`https://github.com/onegayunicorn/conscious-subconscious/security/advisories/new`)
is the only configured channel. **No dedicated security email address exists for
this project**, and none is invented here. If you are deploying this software and
need to be reachable, publish your own contact route rather than relying on the
upstream project's.

## 2. Severity

Assigned by impact, not by type. When in doubt, start one level higher and come
down.

| Level | Definition | Response target | Examples |
| --- | --- | --- | --- |
| **S1 Critical** | A published artefact is compromised, or a credential that grants write access is public. | Act immediately, within hours. | Malicious release on PyPI; `CS_API_KEY` committed to a public repository; a pushed tag that was not authored by the maintainer; a compromised GitHub Action executing in this repository's context. |
| **S2 High** | Personal health-adjacent data is exposed, or the service is exploitable for cross-tenant access. | Same day. | A leaked sensor recording; a shared API key leaked and the service is reachable; session authorisation bypass; arbitrary code execution through a pipeline definition. |
| **S3 Moderate** | Availability or integrity is affected; no data exposed. | Within a few days. | Rate-limit bypass; unbounded session growth; a dependency advisory with a reachable path. |
| **S4 Low** | Hardening gap with no demonstrated impact. | Next maintenance window. | Missing `--unsafe`-safe YAML lint, an unpinned action tag, an informational scanner finding. |

The level determines cadence, not importance of fixing: an S4 still gets fixed.

## 3. The first hour

A fixed sequence, so it can be followed while tired.

1. **Stop the bleeding, not the bleeding edge.** Prefer the smallest action that
   stops the harm: revoke the credential, unpublish the artefact, disable the
   workflow, scale the deployment to zero. Do not start by diagnosing.
2. **Write down the time and what you did.** A plain text file, appended to as you
   go. Every later step depends on this and memory is unreliable under stress.
   ```bash
   mkdir -p /tmp/incident-$(date +%Y%m%d) && cd /tmp/incident-$(date +%Y%m%d)
   printf '%s\t%s\n' "$(date -Is)" "noticed: <what you saw>" >> timeline.txt
   ```
3. **Work in a preserved copy.** Do not edit the evidence in place. Copy logs and
   artefacts out before changing anything, and record the digests.
4. **Determine the blast radius with three questions.** What did the attacker get?
   What would they need to *use* it, and what do you still hold that they do not?
   Who else is affected — is this your own deployment, a fork, or every user?
5. **Decide whether to disclose now or in an hour.** The rule: if a credential is
   live and public, rotate **first**, disclose second. If a fix is needed before
   disclosure helps anyone, fix first and disclose when the fix ships.
6. **Tell someone.** For S1, the second opinion. For anything involving real health
   data, whoever owns that data — that is not your call to make alone.

## 4. Credential leak (`CS_API_KEY` or equivalent)

The specific, uncomfortable details matter more than the general advice.

```bash
# 1. Contain. Rotate. The old value is dead from this moment.
openssl rand -hex 32                    # new value into your secret manager
kubectl -n conscious-subconscious create secret generic \
  conscious-subconscious-secrets \
  --from-literal=CS_API_KEY="<new value>" --dry-run=client -o yaml \
  | kubectl apply -f -
kubectl -n conscious-subconscious rollout restart deploy/conscious-subconscious-api

# 2. Invalidate the old value wherever else it exists.
#    - .env on any workstation (replace, do not just delete)
#    - CI secrets on every fork
#    - docker-compose overrides, shell history, notes apps, tickets
```

Then:

- **Confirm the new value actually took effect.** A rotation that silently did not
  apply is worse than none: you believe you are safe and are not.
- **Assume the old value was used.** Review access logs for the window from the
  first possible exposure to the rotation, looking for unfamiliar source addresses,
  commands on sessions you did not create, and session ids you do not recognise.
- **Do not rely on deleting the commit.** Git history is public and mirrors exist.
  Rotation is the fix.
- **If the key protected something real, treat the data behind it as exposed.**
  An unauthenticated party could read and drive sessions for as long as the key was
  live.
- **GitHub Actions secrets and Docker credentials** are separate credentials. A
  leaked `GITHUB_TOKEN` cannot be rotated by you; it expires, but any long-lived
  PAT that was exposed must be revoked explicitly and its usage audited.
- **PyPI:** this project publishes via OIDC Trusted Publishing, so there is no PyPI
  token to leak. If a release was published from a compromised workflow, delete the
  release, yank the version on PyPI (yank, do not delete — deletion breaks anyone
  pinned to it and hides the evidence), rotate the trusted-publisher configuration,
  and publish a security advisory.

Afterwards, add a `gitleaks` rule or a pre-commit exclusion only if it would have
caught this specific leak. A generic "be more careful" note is not a remediation.

## 5. Sensor recording or participant data leak

The most sensitive data this project can hold is a recording from a real person:
heart rate, EDA, skin temperature, or anything that makes an individual
identifiable. Treat every recording as personal data by default.

**Contain:**

1. Remove public access to the file or location — permissions first, deletion
   second. Deleting first destroys your ability to know what leaked.
2. Record the exact filename, size, format and content shape (which channels, what
   time span) **without copying the values into the incident record**.
3. If the data left the operator's systems (a bucket, a paste, a repository, a
   screenshot, a support ticket, an analytics provider), list every destination and
   take down each one. A recording uploaded to a chat tool is also in that tool's
   backups.
4. Rotate anything that granted access to it.

**Assess:**

- Does the recording identify a person directly? `write_recording()` writes no
  participant identifier column and no metadata header, so identification usually
  comes from the **filename**, the surrounding directory, the session note or the
  person's own knowledge — not from the file's contents.
- How long was it exposed, and was it plausibly accessed? Access logs are the only
  evidence available.
- Are there physiological values in it that could be re-identified against another
  dataset? Heart rate over time is more identifying than it looks.

**Notify:** the affected person, plainly, in the first message — what data, when,
who could have seen it, what you have done, what they should consider doing. Do not
lead with what you were doing to protect them; lead with what happened. For
anything involving a study or a clinical context, the **operator's** ethics board or
legal obligation governs, and this project cannot advise on that.

**Then fix the mechanism:**

- Store recordings on encrypted media, with access limited to the service account.
- Set a retention period and actually delete on it. Nothing in this project deletes
  recordings for you.
- Remove names and dates from filenames. Keep a separate mapping, if you must keep
  one at all, in a different place with different access.
- Disable any telemetry or analytics that touches session content, before the next
  recording is made.

## 6. Compromised release or dependency

If a published artefact may be malicious (S1):

1. **Yank, do not delete.** On PyPI, yank the version so existing pins still
   resolve but new installs cannot pick it up. Delete the corresponding GitHub
   release and tag if the tag was not authored by the maintainer.
2. **Disable the publishing path** so nothing else ships while you investigate:
   disable the release workflow, and revoke the PyPI trusted-publisher
   configuration.
3. **Rotate every credential the workflow could reach**, including any secret in
   the repository, environment or organisation — assume they were read.
4. **Assume installs happened.** A backdoored wheel is installed silently; the
   remedy is an advisory telling anyone who installed that version to remove it and
   rotate anything the installed code could have read.
5. **Review the Actions used.** This repository pins actions to major tags rather
   than SHAs, which is the realistic path to a compromised workflow. Moving to SHA
   pins after an incident of this kind is a proportionate response; doing it before
   one is cheaper.
6. If the compromise came from a dependency, pin it above the affected range in
   `pyproject.toml`, note the reason in the commit, and consider whether the extra
   that pulled it in needs to exist at all. The core installs with no third-party
   dependencies, so most of the supply chain can be removed rather than patched.

## 7. A simulation result that turns out to be wrong

Not a security incident, but this project should treat it with similar
seriousness, because its entire value is that its numbers are honest.

If a bug, a changed default or an unreviewed golden-file regeneration means a
published result was wrong:

1. **Say so where the result was published**, with the same prominence as the
   original. A correction attached to the original is fine; a quiet edit is not.
2. **Identify the cause concretely** — which parameter, equation or step changed,
   and between which digests. The `run_digest` is the tool for this: a result whose
   digest no longer reproduces is a demonstrably stale result.
3. **Publish the corrected run** with its parameter provenance and the regeneration
   command, so a reader can check it.
4. **Do not describe it as a finding.** If a wrong result was ever described in
   terms that sounded like evidence about biology, the correction has to be
   explicit that no such evidence exists either before or after.

## 8. Timeline, postmortem and who reads it

- **Timeline:** written during the incident, not reconstructed afterwards. Rough is
  fine; absent is not.
- **Postmortem:** brief and blameless. What happened, what the impact was, what
  detected it (or what would have), what changed as a result. Include the things
  that went wrong in the response, including the maintainer's own mistakes — a
  postmortem that only lists what the attacker did is not useful.
- **Where it is published:** a GitHub Security Advisory for anything affecting users
  of the software, with a link from `CHANGELOG.md`. Anything with a fix gets a CVE
  requested through GitHub's advisory flow.
- **Who reads it:** the maintainer, the second opinion, and the affected parties.
  Publishing the postmortem publicly is usually correct here: this project has no
  attackers to learn from it that do not already know what they did.

## 9. What this document does not provide

- **No 24-hour response commitment.** A single maintainer cannot offer one, and
  pretending otherwise would be a worse failure than admitting it.
- **No guaranteed disclosure window.** Best effort only.
- **No security email address**, because none is configured. Do not use the
  repository's issues for a vulnerability; use private vulnerability reporting.
- **No legal or regulatory guidance.** If health data is involved, the operator's
  obligations are theirs to determine. Nothing here is legal advice.
- **No insurance, retainer or forensics provider.**
