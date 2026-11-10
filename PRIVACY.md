# Privacy Policy

_Last updated: 10 November 2026_

Mercadona Dashboard ("the app") is an open-source, self-hosted application that tracks
supermarket spending from digital receipts. This policy explains how it handles data
when it accesses a Gmail account.

## Who runs the app

The app is not a hosted service. Each user runs their own copy on their own computer
(via Docker). The authors of this repository do not operate any server and never
receive, see or store any user data.

## Google user data accessed

The app requests a single OAuth scope:

| Scope | Purpose |
|---|---|
| `https://www.googleapis.com/auth/gmail.readonly` | Find emails that contain receipt PDFs and download those attachments. |

The app **cannot** send, delete, move or modify emails, and it does not access any other
Google service.

## How the data is used

- Only emails matching a configurable search filter (by default, emails with a PDF
  attachment from Mercadona's digital receipt sender) are read.
- From each matching email the app stores: message ID, received date, sender, subject
  and the PDF attachment.
- The PDF is parsed to extract the purchase data (store, date, products, prices, totals).
  Card digits and payment authorisation codes printed on the receipt are not stored.
- The data is used exclusively to show spending statistics and price history to the
  person running the app.

## Storage and sharing

- All data (database, PDFs and the OAuth token) is stored **locally** on the machine
  running the app.
- No data is sent to the app authors or to any third party, and no data is used for
  advertising or sold.
- The only external services the app talks to are Google's Gmail API (to read receipts)
  and Mercadona's public online-shop API (to look up product information; no personal
  data is sent).

## Compliance with Google API Services User Data Policy

The app's use and transfer of information received from Google APIs adheres to the
[Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy),
including the Limited Use requirements.

## Retention and deletion

Data stays on the user's machine until the user deletes it. To revoke access and remove
the data:

1. Revoke the app at <https://myaccount.google.com/permissions>.
2. Delete `secrets/token.json`.
3. Remove the local database and media volumes (`docker compose down -v`).

## Contact

Questions about this policy can be raised as an issue at
<https://github.com/B0rjitaaa/mercadona-dashboard/issues>.
