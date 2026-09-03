# Booking API — Integration Manual

See and answer the booking requests on your listings programmatically: the same approve, decline,
cancel and chat actions as your Livuma dashboard, driven by the same booking engine.

Base URL for all endpoints: `https://livuma.com`

---

## Read this first — the 24-hour clock

A guest's booking request **expires if you do not answer within 24 hours**. Preventing that is the
whole reason to integrate, so build the polling loop (step 3) before anything else.

Every request carries a server-computed `respondBy` and `secondsRemaining`. Never derive the
deadline yourself from `createdAt`.

## 1. Get access

Exactly the same key as the [Listing API](listing-api.md). One key covers both.

1. Livuma support enables **API access** for your account. Contact us on
   [WhatsApp](https://wa.me/6281775235276).
2. Log in at livuma.com and open **Profile → Security → API Access**.
3. Click **Generate API key**. The key looks like `livuma_sk_…` and is shown **only once**. Store it
   in a secrets manager, never in source code.

## 2. Authentication

Send your key on every request:

```http
Authorization: Bearer livuma_sk_your_key_here
```

`X-Api-Key: livuma_sk_…` also works. The API only ever shows bookings on **your own** listings.
Someone else's booking id returns `404`, never `403`.

**Rate limit: 120 requests / minute**, shared with the Listing API. Above that you receive `429`
with a `Retry-After` header.

## 3. Poll for new requests

| Method | Endpoint | Notes |
|---|---|---|
| `GET` | `/api/v1/bookings/summary` | one cheap call: counts per bucket plus the next deadline. Poll this every minute. |

```json
{
  "requested": 2,
  "active": 7,
  "past": 34,
  "total": 43,
  "byStatus": { "requested": 2, "ready": 5, "checkedIn": 2, "cancelled": 30, "completed": 4 },
  "nextResponseDeadline": "2026-08-22T04:12:00Z",
  "nextResponseDeadlineSeconds": 48213
}
```

`nextResponseDeadline` is the earliest **still-live** deadline, or `null` when nothing is waiting on
you. A request whose window has already lapsed still counts in `requested` for a few minutes until
our sweep expires it; it just no longer supplies a deadline.

One call per minute sits comfortably inside the rate limit.

## 4. List bookings

| Method | Endpoint | Notes |
|---|---|---|
| `GET` | `/api/v1/bookings` | your bookings, newest first, paged, summary shape |

| Query | Meaning |
|---|---|
| `bucket` | `requests` (awaiting your answer) · `active` (approved through checked-in) · `past` (finished, cancelled, declined, expired) |
| `status` | Repeatable, exact statuses: `requested`, `approved`, `ready`, `checkedin`, `completed`, `pendingcancellation`, `cancelled`, `expired`, `declined`. Mutually exclusive with `bucket`. |
| `listingId` | Restrict to one of your listings. |
| `page` / `pageSize` | 1-based · 1–100, default 25. |

Use `GET /api/v1/bookings/{id}` for the money breakdown, payments and available actions. The list
is a compact summary.

## 5. Read a request — everything you need to decide

| Method | Endpoint | Notes |
|---|---|---|
| `GET` | `/api/v1/bookings/{id}` | the full picture, matching what your dashboard shows you |

| Question | Fields |
|---|---|
| Which property, where | `listingTitle`, `listingLocation`, `listingImageUrl` (absolute), `listingUrl` (site-relative, e.g. `/s/1019/villa-name`; prefix with `https://livuma.com`) |
| Who is asking | `guest.displayName`, `guest.isVerified`, `guest.memberSinceYear`, `guestNotes` |
| What they want | `checkInDate`, `checkOutDate`, `isOpenEnded`, `nights`, `rateType`, `numberOfGuests`, `viewingRequested` |
| Is their money committed | `reservationKind`, `estimatedFirstPayment` |
| How long to answer | `respondBy`, `secondsRemaining`, `responseWindowExpired` |
| What you earn — first period | `pricing.guestTotal`, `pricing.platformFeeAmount`, `pricing.platformFeeVatAmount`, `pricing.hostNetPayout`, `pricing.platformFeeRate` |
| What you earn — whole term | `pricing.schedule[]` plus `pricing.totalGuestPays` / `totalPlatformFee` / `totalHostPayout` |
| Open-ended rentals | `pricing.estimatedRecurringPayment`, `pricing.recurringHostNetPayout`, `pricing.minimumStayMonths` (monthly rentals only; `null` for daily and yearly) |
| Yearly rentals | `pricing.depositAmount`, `pricing.balanceDueAmount`, `pricing.balanceDueDate` |
| Is the money yours yet | `payments[].status` plus `payments[].isReservationPrepayment`, see the note below |
| Your exposure | `guestCancellationTerms`: the guest's free-cancel deadline, minimum stay and notice period |
| What you can do now | `actions[]` |

> **Decide on the whole term, not the first payment.** On a six-month tenancy `pricing.guestTotal`
> is only month one. `pricing.schedule[]` and the totals are the commitment you are accepting. For
> an *open-ended* rental the schedule is just the up-front minimum-stay deposit;
> `estimatedRecurringPayment` is what continues after it.

> **Absent beats wrong.** `pricing` is `null` if we could not compute the breakdown, and
> `pricing.platformFeeRate` is `null` if the fee configuration could not be resolved. Neither is
> ever zero-filled. A `0` commission would be a lie.

> **`"status": "Paid"` does not always mean the money is yours.** While a reservation is still only
> *secured* (a card hold, or a bank transfer sitting in escrow) the payment already reads `Paid` and
> counts towards `totalPaid`, because the guest really has parted with it.
> `payments[].isReservationPrepayment: true` is the flag that says it is **still fully refundable
> and not yet earned**. It flips to `false` at the moment of capture (your approval, or the guest's
> confirmation on a viewing booking). Read it before you treat a booking as money in the bank.

Guest **email and phone are never returned**, at any status. Talk to the guest through the booking
chat (step 8).

## 6. Approve or decline

| Method | Endpoint | Notes |
|---|---|---|
| `GET` | `/api/v1/bookings/{id}/actions` | what is legal right now, the authoritative answer |
| `POST` | `/api/v1/bookings/{id}/approve` | no body |
| `POST` | `/api/v1/bookings/{id}/decline` | `{ "reason": "..." }`, **required**, we pass it to the guest |

```http
POST /api/v1/bookings/1d825809-6811-4c42-af89-08deff3cf121/decline
Content-Type: application/json

{ "reason": "Those dates are no longer available" }
```

Every action returns the **fresh** booking and its new action list, so you never have to model our
booking engine yourself:

```json
{
  "action": "decline",
  "newStatus": "Declined",
  "booking": { "...": "full detail, including the updated actions[]" }
}
```

> **Offer what `actions[]` lists, don't guess.** Whether you may approve, decline or cancel depends
> on the booking's state and on your payout setup. Each action also carries a `label` and
> `requiresConfirmation` you can render directly. Entries marked `"supported": false` exist in your
> dashboard but have no API route yet.

> **`newStatus` is the stored status. Read it, don't infer it from the route.** Declining a
> *requested* booking gives `Declined`; declining one you had already *approved* is a
> self-cancellation and gives `Cancelled`.

Actions are **not** idempotent: approving twice returns `409`. To retry safely, re-read `/actions`
and act on what it says.

### What approving actually does to the money

Guests now secure a booking *before* you ever see it: their card is authorised, or their bank
transfer already received. So in the common case approving is not a request to pay, it **takes the
money that is already held**. Read `reservationKind` to know which case you are in:

| Booking | What approving does |
|---|---|
| `reservationKind` set, `viewingRequested: false` (the normal case) | Your approval **is** the commitment moment: the card hold is captured (or the transfer confirmed) immediately, and the booking moves to `ready` shortly after. Nothing further is asked of the guest, *unless it is a yearly rental*, see below. |
| `reservationKind` set, `viewingRequested: true` | The money stays **held, not taken**; the guest wants to view first. Approving starts their confirmation window (`confirmByUtc`); capture happens when they confirm, or automatically at that deadline. |
| `reservationKind: null` (older bookings) | No money is held. Approving invites the guest to pay, and the booking only becomes `ready` once they do. |

> **Yearly rentals are the exception: approving does not make them `ready`.** A yearly booking is
> paid in two parts: an advance deposit (secured up front, captured by your approval) and the
> balance, due before check-in (`pricing.balanceDueDate`). The booking stays `approved`, with
> `payments[1].status: "Pending"`, until that balance is paid; only then does it become `ready`.
> That is normal and needs nothing from you; we invoice the guest. Don't treat a long-lived
> `approved` yearly booking as stuck.

> **So declining is not free of consequence in the first two cases.** The guest's money is already
> committed. Declining releases the hold or refunds the transfer in full. That is also why a decline
> **requires a reason**: we pass it to a guest who has already paid.

If a capture fails (an expired or withdrawn card hold), the booking stays `approved` and the guest
is asked to secure it again in the app. You do not need to do anything, and there is no API call
for it.

## 7. Cancel an accepted booking

| Method | Endpoint | Notes |
|---|---|---|
| `GET` | `/api/v1/bookings/{id}/cancellation-preview` | free, read-only: what cancelling would cost |
| `POST` | `/api/v1/bookings/{id}/cancel` | `{ "reason": "..." }`, required |

**Cancel is not decline.** Decline ends a request, or an approved booking nobody has paid for, with
no penalty. Cancel runs the cancellation policy: notice periods, guest refunds, your compensation.
Always show the preview first:

```json
{
  "currentStatus": "Ready",
  "resultingStatus": "Cancelled",
  "cancellationInfo": {
    "canCancel": true,
    "reason": "Cancellation allowed — earliest termination Sep 20, 2026 (30-day notice)",
    "estimatedRefundAmount": 0,
    "isFreeCancellation": false,
    "noticeDays": 30
  }
}
```

`canCancel: false` is a normal answer, not an error. Some stays can only be ended by contacting
support. The `reason` explains why.

## 8. Chat with the guest

| Method | Endpoint | Notes |
|---|---|---|
| `GET` | `/api/v1/bookings/{id}/messages` | `?limit=100&before=…`, newest page first, oldest-first within the page |
| `POST` | `/api/v1/bookings/{id}/messages` | `{ "text": "..." }`, max 2000 characters |
| `POST` | `/api/v1/bookings/{id}/messages/read` | clears your unread badge, and the reminder emails that follow it |

| Field | Meaning |
|---|---|
| `sender` | `host` (you), `guest`, or `system` (Livuma). |
| `text` | Ready to display, in your account language. |
| `attachments[]` | Images, videos and files, **in message order**. |
| `hasMore` / `nextBefore` | Older messages exist. Pass `nextBefore` back as `before`. |

> **`nextBefore` is an opaque token.** Echo it back exactly; never build or parse one. A token that
> does not parse returns `400` rather than silently restarting from the newest page, which would
> loop your paging forever.

- Chat opens as soon as the guest has secured the booking with a card hold or bank transfer;
  older-style requests open it when you approve. Sending before that returns `409`.
- Finished bookings (cancelled, completed, expired, declined) are **read-only**. You can still fetch
  the transcript.
- One message per second. Faster returns `429`.
- Send plain text. Attachment markers inside `text` are rejected.

## 9. Error handling

Every failure is JSON and carries a stable `errorCode`. Branch on that, never on the English
`title`. Same contract as the Listing API, so one error handler covers both.

```json
{
  "title": "Booking is in Approved status, expected Requested",
  "status": 409,
  "errorCode": "INVALID_BOOKING_STATUS"
}
```

| Code | Meaning |
|---|---|
| `400` | Bad input: a missing decline/cancel reason, an unknown status or bucket, a malformed chat cursor. `VALIDATION_ERROR` · `BAD_REQUEST` |
| `401` | Missing / invalid / revoked key, or API access disabled. `UNAUTHORIZED` |
| `404` | No such booking, or not on one of your listings. `BOOKING_NOT_FOUND` |
| `409` | The booking moved on, or a policy said no. Re-read `/actions`. `ACTION_NOT_AVAILABLE` · `INVALID_BOOKING_STATUS` · `HOST_NOT_PAYOUT_READY` · `POLICY_DENIED` |
| `429` | Rate limit. Wait `Retry-After` seconds. `RATE_LIMITED` |
| `502` | Our payment provider failed, safe to retry later. `PROVIDER_ERROR` |
| `500` | Unexpected failure, always JSON. Quote the `traceId` to support. `INTERNAL_ERROR` |

> **`HOST_NOT_PAYOUT_READY`** means your payout setup, or that of the property's owner, is
> incomplete, so you cannot accept bookings yet. Finish it on livuma.com; the API cannot.

## 10. Dates, times and money

| Kind | Format |
|---|---|
| Moments in time | `createdAt`, `respondBy`, `cancelledAt`, `sentAt`, payment `dueDate` …: UTC with a trailing `Z`. Parse as UTC. |
| Calendar dates | `checkInDate`, `checkOutDate`, period boundaries, policy deadlines: plain `YYYY-MM-DD` in Bali time, no zone. There is no time to interpret. |
| Money | In the booking's `currency` (IDR in practice), unscaled: `1500000` means Rp 1,500,000. |

Platform fee and VAT are deducted from *your payout*, never added to the guest's total.
`hostNetPayout` is what reaches your bank.

## 11. Good to know

- Bookings a guest is still paying for are not visible here. They appear as `requested` the moment
  the guest secures them.
- The booking becomes `ready` on its own once **every payment due before check-in** has settled.
  There is never an API call for that step. For daily and monthly bookings that is the first
  payment; for yearly it is the deposit *and* the balance (see step 6).
- Everything this API does, your dashboard can do too, and both run the same booking engine. A
  booking answered in the app and one answered over the API behave identically.
- Keep the key server-side only. If it ever leaks, regenerate it immediately on
  **Profile → Security**.

---

Questions? We're happy to help: [WhatsApp support](https://wa.me/6281775235276) ·
[livuma.com](https://livuma.com) · hello@livuma.com
