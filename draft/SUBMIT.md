# IETF Submission Guide — draft-aevum-agentcard-00

The Internet Draft is complete (20 pages, xml2rfc 3.33.0 validated).
One-time account creation required, then ~5 minutes to submit.

---

## Step 1 — Create IETF Datatracker Account (one time)

1. Go to: https://datatracker.ietf.org/accounts/create/
2. Use a real email address (noreply emails are rejected)
3. Verify the email
4. Save your credentials

---

## Step 2 — Submit via Web Form

1. Go to: https://datatracker.ietf.org/submit/
2. Click **"Upload your Internet-Draft"**
3. Upload: `draft/draft-aevum-agentcard-00.xml`
4. The system auto-fills title, authors, abstract from the XML
5. Click **"Submit"**
6. A confirmation email is sent to the author address in the XML

---

## Step 3 — Submit via API (alternative, if account exists)

```bash
curl -X POST "https://datatracker.ietf.org/api/submission/" \
  -F "xml=@draft/draft-aevum-agentcard-00.xml;type=application/xml" \
  -F "user=YOUR_DATATRACKER_EMAIL@example.com"
```

On success, returns:
```json
{
  "id": "<submission_id>",
  "status": "validating",
  "url": "https://datatracker.ietf.org/submit/<submission_id>/"
}
```

---

## Step 4 — After Submission

Within ~1 hour:
- Draft appears at: https://datatracker.ietf.org/doc/draft-aevum-agentcard/
- Plain-text copy: https://www.ietf.org/archive/id/draft-aevum-agentcard-00.txt
- IETF sends confirmation to author email

**Recommended next steps:**
- Post to `dispatch@ietf.org` mailing list announcing the draft
- Post to `wimse@ietf.org` (WIMSE WG — Workload Identity in Multi-System Environments)
  as AgentCard complements WIMSE identity work
- Post to `oauth@ietf.org` if requesting review there

---

## Draft artifacts in this repo

| File | Description |
|------|-------------|
| `draft/draft-aevum-agentcard-00.xml` | RFC XML v3 source (submit this) |
| `draft/draft-aevum-agentcard-00.txt` | Plain text (20 pages, xml2rfc rendered) |
| `draft/draft-aevum-agentcard-00.html` | HTML rendering |

---

## Key metadata

| Field | Value |
|-------|-------|
| Draft name | `draft-aevum-agentcard-00` |
| Category | Informational |
| Submission type | Individual |
| Expires | 25 October 2026 |
| IANA requests | `application/agentcard+json` media type, `agentcard` well-known URI |
| Related WGs | wimse, oauth, dispatch |
