# Listing API — Integration Manual

Create and manage your Livuma listings programmatically — with the same validation, content moderation, image and video pipeline as the website.

## New in October 2026 — video tours

Listings can now carry a **video tour**, shown on the listing page below the description. Nothing changes for existing integrations — it is optional and purely additive:

- New endpoints under `/api/v1/listings/{id}/videos` — see **5b**.
- `GET` and `PUT /api/v1/listings/{id}` responses gain a `videos` array (empty when the listing has none).
- New error codes: `VIDEO_LIMIT_REACHED`, `VIDEO_FILE_TOO_LARGE`, `VIDEO_TYPE_NOT_ALLOWED`, `VIDEO_NOT_FOUND`, `VIDEOS_DISABLED` — see **7**.

---

## Changed in August 2026 — action needed

Indonesia's updated tourism-accommodation rules (KBLI 2025 + the Ministry of Tourism's OTA verification program) added new required fields:

- **Monthly rentals** now require `"residentialLeaseConfirmed": true` — your declaration that the property is let as a residential lease (the tenant lives there as their residence; it is not operated as tourist accommodation). Without it, creates and updates of monthly listings return `400` with code `residential_lease_confirmation_required`.
- **Short-term (daily) rentals** accept an optional `nkuNumber` (NKU — Nomor Kegiatan Usaha: the per-activity number in your NIB attachment in OSS, not the NIB itself) alongside the required NIB + KBLI. It is not required yet; once it is, the error code is `nku_required`.
- `kbliCodes` must be accommodation (division 55) codes — see the field reference for the accepted list. Real-estate codes such as 68111 are rejected (`kbli_not_accepted`).
- `npwpdNumber` was **removed**. If you still send it, it is ignored.

For most integrations the fix is one line: add `"residentialLeaseConfirmed": true` to your monthly-listing payloads.

---

## 1. Get access

1. Livuma support enables **API access** for your account — contact us on [WhatsApp](https://wa.me/6281775235276).
2. Log in at livuma.com and open **Profile → Security → API Access**.
3. Click **Generate API key**. The key looks like `livuma_sk_…` and is shown **only once** — store it in a secrets manager, never in source code.
4. You can **Regenerate** (the old key stops working immediately) or **Revoke** the key there at any time.

---

## 2. Authentication

Send your key on every request:

```
Authorization: Bearer livuma_sk_your_key_here
```

(`X-Api-Key: livuma_sk_…` also works.) The API only ever shows and edits **your own** listings.

**Rate limit: 120 requests / minute** — above that you receive `429` with a `Retry-After` header.

---

## 3. First call — reference IDs

Write requests use IDs, not names. Fetch them once and cache them:

- **GET** `/api/v1/listings/reference-data` — offer types (rent/sale), property types, countries, currencies, availability & ownership types — each with `id` + `name`

Base URL for all endpoints: `https://livuma.com`

---

## 4. Create a listing

```
POST /api/v1/listings
Content-Type: application/json

{
  "title": "Modern 2BR Villa near Batu Bolong",
  "description": "Private pool, fast wifi, 5 min to the beach...",
  "offerTypeId":        "<rent id>",
  "objectTypeId":       "<Villa id>",
  "countryId":          "<Indonesia id>",
  "currencyId":         "<IDR id>",
  "availabilityTypeId": "<Immediately id>",
  "addressNo":   "Jl. Batu Bolong No. 88",
  "latitude":  -8.6478,
  "longitude": 115.1385,
  "isLongTermRental": true,
  "longTermMonthlyPrice": 28000000,
  "residentialLeaseConfirmed": true,
  "rooms": 2, "bathrooms": 2, "squareMeters": 120,
  "hasPool": true, "hasWiFi": true, "hasAC": true
}
```

The `201` response contains the listing `id`, its `publicId` and its public `url`. The listing starts in the hidden **"Notice"** state — upload your photos (step 5), then set it **online** (step 6) to publish. A listing needs at least one photo to go online.

> **Location is derived from your coordinates.** You do not send a city/zip field — Livuma reverse-geocodes `latitude`/`longitude` and stores the normalized location (e.g. "80361, Kuta Utara") so all listings display uniformly. Coordinates that don't resolve to Indonesia are rejected — double-check you haven't swapped lat/lng.

> **Monthly rentals** (a `longTermMonthlyPrice`) require `"residentialLeaseConfirmed": true` — your declaration that the property is let as a residential lease, not operated as tourist accommodation.

> **Short-term (daily) rentals** additionally require: `isShortTermRental: true`, `shortTermPrice`, your 13-digit `nibNumber`, `kbliCodes`, and both `shortTermRentalComplianceConfirmed` and `shortTermRentalComplianceResponsibilityAcknowledged` set to `true`.

---

## 5. Add photos

- **POST** `/api/v1/listings/{id}/images` — multipart/form-data, field name `files`

- jpg / jpeg / png / webp · max 20 MB per file · max 30 images per listing (checked before upload).
- Images are compressed server-side and pass automated content moderation — rejected images come back with a reason (`422` if all were rejected).
- The first image becomes the cover.

- **PUT** `/api/v1/listings/{id}/images/order` — `{ "imageIds": [...], "primaryImageId": "..." }` — must contain *every* image id of the listing exactly once, in the desired order
- **DELETE** `/api/v1/listings/{id}/images/{imageId}` — removes one image; the cover is re-assigned automatically

---

## Add a video tour (optional)

Upload the video **file** itself — links (YouTube, Vimeo …) are not accepted. The file goes straight to our video provider over the resumable [tus](https://tus.io) protocol, so large files survive dropped connections.

- 1 video per listing · up to 5 minutes · up to 4 GB · mp4 / mov / m4v / webm.
- Guests get the best quality their screen and connection can play (up to Full HD).
- Shown on the listing page below the description once it is processed and has passed content moderation (it must show the property).

- **POST** `/api/v1/listings/{id}/videos` — `{ "fileName": "tour.mp4", "sizeBytes": 734003200, "caption": "Villa tour" }` → `201` with an `upload` block

```
{
  "video":  { "id": "…", "status": "uploading", … },
  "upload": {
    "protocol": "tus",
    "endpoint": "https://video.bunnycdn.com/tusupload",
    "headers":  { "AuthorizationSignature": "…", "AuthorizationExpire": "1760999999",
                  "VideoId": "…", "LibraryId": "…" },
    "expiresAt": "2026-10-21T12:00:00Z"
  }
}
```

Upload the file to `upload.endpoint` with any tus 1.0 client, sending the four `upload.headers` exactly as received (they authorise this one upload for 24 hours). Example with the Python `tuspy` client:

```
from tusclient import client
c = client.TusClient(upload["endpoint"], headers=upload["headers"])
c.uploader("tour.mp4", chunk_size=32 * 1024 * 1024,
           metadata={"filetype": "video/mp4", "title": "tour.mp4"}).upload()
```

- **POST** `/api/v1/listings/{id}/videos/{videoId}/uploaded` — optional — tells us the upload finished, so processing starts at once
- **GET** `/api/v1/listings/{id}/videos/{videoId}` — poll until `status` is `ready` (then `posterUrl`, `embedUrl`, `playlistUrl` are set), `rejected` (see `rejectionReason`; `too_long` = over 5 minutes) or `failed` (re-export the file and try again)
- **PUT** `/api/v1/listings/{id}/videos/{videoId}` — `{ "caption": "…" }`
- **DELETE** `/api/v1/listings/{id}/videos/{videoId}` — removes the video — needed before uploading a replacement (`409 VIDEO_LIMIT_REACHED` otherwise)
- **GET** `/api/v1/listings/{id}/videos` — the listing's videos plus the current limits

---

## 6. Read, update, pause, delete

- **GET** `/api/v1/listings?page=1&pageSize=25` — your listings (summary shape)
- **GET** `/api/v1/listings/{id}` — full detail incl. all images and the `videos` array (same shape as in 5b)
- **PUT** `/api/v1/listings/{id}` — update — send *only* the fields you change; omitted or `null` fields keep their values. The response is the full detail, `videos` included
- **POST** `/api/v1/listings/{id}/status` — `{"status": "online" | "paused" | "removed"}`
- **DELETE** `/api/v1/listings/{id}` — same as status `removed`

- New listings start in the hidden **"Notice"** state; set them `online` once photos are uploaded.
- Pausing hides the listing; you can bring it back online anytime. Going **online** requires at least one photo and re-checks all listing rules.
- `"removed"` (alias `"deleted"`) is **permanent** — you cannot reactivate it yourself.

---

## Field reference — create / update body

All fields are optional in the JSON (updates change only what you send). “Required” means the listing must have it to be valid.

| Field | Type | Notes |
|---|---|---|
| `title` | string ≤50 | **Required.** Public URL slug derives from it. Moderated. |
| `description` | string ≤2000 | Moderated. |
| `offerTypeId` | guid | **Required.** Rent or sale (reference-data). |
| `objectTypeId` | guid | **Required.** Villa, Apartment, … |
| `countryId` | guid | **Required.** |
| `currencyId` | guid | **Required** for rentals and sales. |
| `availabilityTypeId` | guid | **Required.** Determines which dates you must send. |
| `ownershipTypeId` | guid | Required when the offer type demands it (e.g. sales). |
| `addressNo` | string ≤255 | **Required.** Street address. |
| `latitude`, `longitude` | decimal | **Required, non-zero.** Must resolve to Indonesia. City/zip display is derived from these. |
| `isShortTermRental`, `isLongTermRental` | bool | Rentals need at least one `true`. Default `false`. |
| `shortTermPrice` | decimal | Nightly rate — required > 0 when short-term is enabled. |
| `minimumStayDays` | int | Minimum nights (short-term). |
| `nibNumber` | string ≤20 | **Short-term:** required, exactly 13 digits (separators allowed). |
| `kbliCodes` | string ≤200 | **Short-term:** required, comma-separated. Accepted KBLI 2025 codes: `55203` Villa, `55201` Homestay, `55204` Hotel Apartment, `55106` Non-Star Hotel, `55202` Youth Hostel, `55300` Campground, `55209` Other Short-Term Accommodation, `55909` Other Accommodation (boarding house / kost, co-living) (legacy KBLI 2020 equivalents such as `55193`/`55130`/`55900` remain accepted while OSS records convert). Real-estate codes are rejected (`kbli_not_accepted`). |
| `nkuNumber` | string ≤30 | **Short-term:** optional (recommended) — NKU (Nomor Kegiatan Usaha), the per-activity number in your NIB attachment in OSS; not the same as the NIB. Part of the Ministry of Tourism's planned NIB + KBLI + NKU verification. |
| `shortTermRentalComplianceConfirmed`, `shortTermRentalComplianceResponsibilityAcknowledged` | bool | **Short-term:** both must be `true`. |
| `longTermMonthlyPrice`, `longTermYearlyPrice` | decimal | At least one > 0 when long-term is enabled. `0` means the rate is not offered: to remove a monthly or yearly rate on update, send `0` (`null` leaves it unchanged). To stop offering nightly stays, set `isShortTermRental` to `false`. |
| `residentialLeaseConfirmed` | bool | **Monthly rentals:** must be `true` — declares the property is let as a residential lease, not operated as tourist accommodation. Not needed for yearly-only listings. |
| `minimumStayMonths` | int | Minimum months (long-term). |
| `utilities` | decimal | Monthly utilities amount. |
| `salesPrice` | decimal | Required > 0 for sale offers. |
| `rooms`, `bathrooms` | int | Default 1. |
| `squareMeters` | decimal | Building size. |
| `yearBuilt`, `leaseholdYears` | int | Optional. |
| `availableFromDate`, `availableToDate` | datetime | Required depending on the availability type (from-date, or both). |
| `sizeInAre`, `zoning`, `accessRoadInfo` | — | Land details. |
| `electricityAvailable`, `waterAvailable`, `soilTestDone`, `waterTestDone`, `topographyTestDone` | bool | Land flags. |
| `hasPool`, `hasGarden`, `hasAC`, `isPetFriendly`, `hasParking`, `hasWiFi`, `hasSecurity`, `hasDedicatedWorkspace`, `hasEquippedKitchen` | bool | Amenities. |
| `cleaningIncluded`, `poolServiceIncluded`, `gardenerIncluded` | bool | Included services. |

---

## 7. Error handling

Every failure is `application/problem+json` and carries a stable `errorCode` — branch on that, never on the English `title`. Validation failures additionally list each field twice: `errors` (human messages) and `errorCodes` (per-field codes).

```
{
  "title": "Listing not found.",
  "status": 404,
  "errorCode": "LISTING_NOT_FOUND"
}
```

| Code | Meaning |
|---|---|
| `400` | Validation failed (`errorCode: VALIDATION_ERROR`). The body lists each field with a message, plus machine-readable codes in `errorCodes`: `[{ "field": "nib_number", "code": "nib_invalid" }, …]` — branch on the codes, not the text.  A malformed request (unknown status name, empty `imageIds`, coordinates outside Indonesia) uses `BAD_REQUEST`, `INVALID_STATUS`, `INVALID_IMAGE_ORDER` or `INVALID_COORDINATES`.  Video upload requests: `VIDEO_TYPE_NOT_ALLOWED` (not mp4/mov/m4v/webm) · `VIDEO_FILE_TOO_LARGE` (`sizeBytes` 0 or over 4 GB). |
| `401` | Missing / invalid / revoked key, or API access disabled. `UNAUTHORIZED` — this one is written by the auth layer, but carries `errorCode` like every other failure. |
| `403` | Not yours to modify. `UNAUTHORIZED`  Video tours are switched off on the platform right now. `VIDEOS_DISABLED` |
| `404` | Listing doesn't exist or isn't yours. `LISTING_NOT_FOUND` · `IMAGE_NOT_FOUND`  Video not found on that listing (or not yours). `VIDEO_NOT_FOUND`  An unmatched route is `NOT_FOUND`. |
| `405` / `415` | Wrong HTTP method for the route, or a body that isn't `application/json`. `METHOD_NOT_ALLOWED` · `UNSUPPORTED_MEDIA_TYPE` |
| `409` | The listing was removed (permanent) — it can no longer be modified. `LISTING_REMOVED`  The listing already has its video — delete it before uploading another. `VIDEO_LIMIT_REACHED` |
| `422` | Content moderation rejected your text or images. `MODERATION_REJECTED` · `IMAGE_MODERATION_REJECTED`  For image uploads the body keeps its normal shape — `accepted`, `rejected` (with a per-file reason) and `moderationMessage` — plus `errorCode`.  Videos are checked *after* the upload, so a refused video is not an error response: its `status` becomes `rejected` with a `rejectionReason`. |
| `429` | Rate limit — JSON body, wait `Retry-After` seconds. `RATE_LIMITED` |
| `500` / `503` | Server-side or storage failure — safe to retry. `INTERNAL_ERROR` · `SERVICE_UNAVAILABLE`  Always JSON, never an HTML error page, and the exception text is never returned — quote the `traceId` to support. |

**Already integrated?** Nothing was removed — `errors`, `errorCodes` and the HTTP statuses are unchanged. `errorCode` was added alongside them, so existing handlers keep working.

---

## 8. Dates & times

Two kinds of value, and only one carries a time zone:

| Field | Format |
|---|---|
| `creationDate` video `createdAt`, `readyAt`, upload `expiresAt` | **An instant.** UTC ISO-8601 with a trailing `Z` — `"2026-08-06T02:20:20.2027373Z"`. Parse as UTC. |
| `availableFromDate` `availableToDate` | **Calendar dates.** Sent with a trailing time component that carries no meaning and *no* zone marker — `"2026-08-06T10:19:43.4504547"`. Read the date part and ignore the rest. |

**Changed 2026-08-22:** `creationDate` previously came back without the `Z`, so a client had to guess the zone; the instant itself is unchanged and no field type changed — only the marker was added. The availability dates were deliberately left exactly as they were: marking them UTC would shift the date a day backwards for clients west of UTC.

---

## 9. Good to know

- Changing a title changes the listing's public URL (the slug is derived from the title).
- A video is optional and never required to go `online`. It appears on the listing page only once its `status` is `ready`; processing usually takes 1–3 minutes after the upload.
- Whether a listing is *bookable* also depends on your payout setup being complete — the API doesn't change that.
- Keep the key server-side only. If it ever leaks, regenerate it immediately on **Profile → Security**.
- The same key also drives the [Booking API](booking-api.md) — read and answer the booking requests on these listings (approve, decline, cancel, chat).

---

---

Questions? We're happy to help — [WhatsApp support](https://wa.me/6281775235276) · [livuma.com](https://livuma.com)
