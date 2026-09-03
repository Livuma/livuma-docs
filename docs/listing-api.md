# Listing API — Integration Manual

Create and manage your Livuma listings programmatically, with the same validation, content
moderation and image pipeline as the website.

Base URL for all endpoints: `https://livuma.com`

The same API key also drives the [Booking API](booking-api.md).

---

## Changed in August 2026 — action needed

Indonesia's updated tourism-accommodation rules (KBLI 2025 plus the Ministry of Tourism's OTA
verification program) added new required fields:

- **Monthly rentals** now require `"residentialLeaseConfirmed": true`, your declaration that the
  property is let as a residential lease (the tenant lives there as their residence; it is not
  operated as tourist accommodation). Without it, creates and updates of monthly listings return
  `400` with code `residential_lease_confirmation_required`.
- **Short-term (daily) rentals** now also require `nkuNumber` (NKU, Nomor Kegiatan Usaha from OSS,
  listed under your NIB), alongside the existing NIB + KBLI. Error code: `nku_required`.
- `kbliCodes` must be accommodation (division 55) codes, see the field reference for the accepted
  list. Real-estate codes such as 68111 are rejected (`kbli_not_accepted`).
- `npwpdNumber` was **removed**. If you still send it, it is ignored.

For most integrations the fix is one line: add `"residentialLeaseConfirmed": true` to your
monthly-listing payloads.

## 1. Get access

1. Livuma support enables **API access** for your account. Contact us on
   [WhatsApp](https://wa.me/6281775235276).
2. Log in at livuma.com and open **Profile → Security → API Access**.
3. Click **Generate API key**. The key looks like `livuma_sk_…` and is shown **only once**. Store it
   in a secrets manager, never in source code.
4. You can **Regenerate** (the old key stops working immediately) or **Revoke** the key there at any
   time.

## 2. Authentication

Send your key on every request:

```http
Authorization: Bearer livuma_sk_your_key_here
```

`X-Api-Key: livuma_sk_…` also works. The API only ever shows and edits **your own** listings.

**Rate limit: 120 requests / minute.** Above that you receive `429` with a `Retry-After` header.

## 3. First call — reference IDs

Write requests use IDs, not names. Fetch them once and cache them:

| Method | Endpoint | Returns |
|---|---|---|
| `GET` | `/api/v1/listings/reference-data` | offer types (rent/sale), property types, countries, currencies, availability and ownership types, each with `id` + `name` |

## 4. Create a listing

```http
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

The `201` response contains the listing `id`, its `publicId` and its public `url`. The listing
starts in the hidden **"Notice"** state: upload your photos (step 5), then set it **online**
(step 6) to publish. A listing needs at least one photo to go online.

> **Location is derived from your coordinates.** You do not send a city/zip field. Livuma
> reverse-geocodes `latitude`/`longitude` and stores the normalized location (e.g. "80361, Kuta
> Utara") so all listings display uniformly. Coordinates that don't resolve to Indonesia are
> rejected. Double-check you haven't swapped lat/lng.

> **Monthly rentals** (a `longTermMonthlyPrice`) require `"residentialLeaseConfirmed": true`, your
> declaration that the property is let as a residential lease, not operated as tourist
> accommodation.

> **Short-term (daily) rentals** additionally require: `isShortTermRental: true`, `shortTermPrice`,
> your 13-digit `nibNumber`, `kbliCodes`, your `nkuNumber` (NKU from OSS), and both
> `shortTermRentalComplianceConfirmed` and `shortTermRentalComplianceResponsibilityAcknowledged`
> set to `true`.

## 5. Add photos

| Method | Endpoint | Notes |
|---|---|---|
| `POST` | `/api/v1/listings/{id}/images` | `multipart/form-data`, field name `files` |
| `PUT` | `/api/v1/listings/{id}/images/order` | `{ "imageIds": [...], "primaryImageId": "..." }`, must contain *every* image id of the listing exactly once, in the desired order |
| `DELETE` | `/api/v1/listings/{id}/images/{imageId}` | removes one image; the cover is re-assigned automatically |

- jpg / jpeg / png / webp, max 20 MB per file, max 30 images per listing (checked before upload).
- Images are compressed server-side and pass automated content moderation. Rejected images come
  back with a reason (`422` if all were rejected).
- The first image becomes the cover.

## 6. Read, update, pause, delete

| Method | Endpoint | Notes |
|---|---|---|
| `GET` | `/api/v1/listings?page=1&pageSize=25` | your listings (summary shape) |
| `GET` | `/api/v1/listings/{id}` | full detail incl. all images |
| `PUT` | `/api/v1/listings/{id}` | update: send *only* the fields you change; omitted fields keep their values |
| `POST` | `/api/v1/listings/{id}/status` | `{"status": "online" \| "paused" \| "removed"}` |
| `DELETE` | `/api/v1/listings/{id}` | same as status `removed` |

- New listings start in the hidden **"Notice"** state; set them `online` once photos are uploaded.
- Pausing hides the listing; you can bring it back online anytime. Going **online** requires at
  least one photo and re-checks all listing rules.
- `"removed"` (alias `"deleted"`) is **permanent**. You cannot reactivate it yourself.

## 6b. Field reference — create / update body

All fields are optional in the JSON (updates change only what you send). "Required" means the
listing must have it to be valid.

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
| `shortTermPrice` | decimal | Nightly rate, required > 0 when short-term is enabled. |
| `minimumStayDays` | int | Minimum nights (short-term). |
| `nibNumber` | string ≤20 | **Short-term:** required, exactly 13 digits (separators allowed). |
| `kbliCodes` | string ≤200 | **Short-term:** required, comma-separated. Accepted KBLI 2025 codes: `55203` Villa, `55201` Homestay, `55204` Hotel Apartment, `55106` Non-Star Hotel, `55202` Youth Hostel, `55300` Campground, `55209` Other Short-Term Accommodation (legacy KBLI 2020 equivalents such as `55193`/`55130` remain accepted while OSS records convert). Real-estate codes are rejected (`kbli_not_accepted`). |
| `nkuNumber` | string ≤30 | **Short-term:** required. NKU (Nomor Kegiatan Usaha) from OSS, listed under your NIB. Part of the Ministry of Tourism's NIB + KBLI + NKU verification. |
| `shortTermRentalComplianceConfirmed`, `shortTermRentalComplianceResponsibilityAcknowledged` | bool | **Short-term:** both must be `true`. |
| `longTermMonthlyPrice`, `longTermYearlyPrice` | decimal | At least one > 0 when long-term is enabled. |
| `residentialLeaseConfirmed` | bool | **Monthly rentals:** must be `true`. Declares the property is let as a residential lease, not operated as tourist accommodation. Not needed for yearly-only listings. |
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

## 7. Error handling

Every failure is `application/problem+json` and carries a stable `errorCode`. Branch on that, never
on the English `title`. Validation failures additionally list each field twice: `errors` (human
messages) and `errorCodes` (per-field codes).

```json
{
  "title": "Listing not found.",
  "status": 404,
  "errorCode": "LISTING_NOT_FOUND"
}
```

| Code | Meaning |
|---|---|
| `400` | Validation failed (`errorCode: VALIDATION_ERROR`). The body lists each field with a message, plus machine-readable codes in `errorCodes`: `[{ "field": "nib_number", "code": "nib_invalid" }, …]`. Branch on the codes, not the text. A malformed request (unknown status name, empty `imageIds`, coordinates outside Indonesia) uses `BAD_REQUEST`, `INVALID_STATUS`, `INVALID_IMAGE_ORDER` or `INVALID_COORDINATES`. |
| `401` | Missing / invalid / revoked key, or API access disabled. `UNAUTHORIZED`. This one is written by the auth layer, but carries `errorCode` like every other failure. |
| `403` | Not yours to modify. `UNAUTHORIZED` |
| `404` | Listing doesn't exist or isn't yours. `LISTING_NOT_FOUND` · `IMAGE_NOT_FOUND`. An unmatched route is `NOT_FOUND`. |
| `405` / `415` | Wrong HTTP method for the route, or a body that isn't `application/json`. `METHOD_NOT_ALLOWED` · `UNSUPPORTED_MEDIA_TYPE` |
| `409` | The listing was removed (permanent) and can no longer be modified. `LISTING_REMOVED` |
| `422` | Content moderation rejected your text or images. `MODERATION_REJECTED` · `IMAGE_MODERATION_REJECTED`. For image uploads the body keeps its normal shape (`accepted`, `rejected` with a per-file reason, and `moderationMessage`) plus `errorCode`. |
| `429` | Rate limit. JSON body, wait `Retry-After` seconds. `RATE_LIMITED` |
| `500` / `503` | Server-side or storage failure, safe to retry. `INTERNAL_ERROR` · `SERVICE_UNAVAILABLE`. Always JSON, never an HTML error page, and the exception text is never returned. Quote the `traceId` to support. |

**Already integrated?** Nothing was removed. `errors`, `errorCodes` and the HTTP statuses are
unchanged. `errorCode` was added alongside them, so existing handlers keep working.

## 8. Dates and times

Two kinds of value, and only one carries a time zone:

| Field | Format |
|---|---|
| `creationDate` | **An instant.** UTC ISO-8601 with a trailing `Z`: `"2026-08-06T02:20:20.2027373Z"`. Parse as UTC. |
| `availableFromDate`, `availableToDate` | **Calendar dates.** Sent with a trailing time component that carries no meaning and *no* zone marker: `"2026-08-06T10:19:43.4504547"`. Read the date part and ignore the rest. |

**Changed 2026-08-22:** `creationDate` previously came back without the `Z`, so a client had to
guess the zone; the instant itself is unchanged and no field type changed, only the marker was
added. The availability dates were deliberately left exactly as they were: marking them UTC would
shift the date a day backwards for clients west of UTC.

## 9. Good to know

- Changing a title changes the listing's public URL (the slug is derived from the title).
- Whether a listing is *bookable* also depends on your payout setup being complete. The API doesn't
  change that.
- Keep the key server-side only. If it ever leaks, regenerate it immediately on
  **Profile → Security**.
- The same key also drives the [Booking API](booking-api.md): read and answer the booking requests
  on these listings (approve, decline, cancel, chat).

---

Questions? We're happy to help: [WhatsApp support](https://wa.me/6281775235276) ·
[livuma.com](https://livuma.com) · hello@livuma.com
