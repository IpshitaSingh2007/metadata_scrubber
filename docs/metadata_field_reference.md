# metadata field reference 

This document lists the EXIF/image metadata tags the srubber checks for, what each one reveals, its privacy risk level, and the message shown to the user
 
## location 

| Tag | What it reveals | Severity | Risk message|
|---|---|---|---|
| GPSLatitude/GPSLongitude | Exact location, accurate to ~10m. Shown as single finding| High| "This reveals your exact location"|
| GPSAltitude | Elevation at the time of capture | Low| "Reveals the elevation"|
| GPSTimeStamp | UTC time at the GPS fix was recorded | Low| "Reveals the exact time your location was recorded"|

## Timestamp

| Tag | What it reveals | Severity | Risk message|
|---|---|---|---|
| DateTimeOriginal | Exact date and time the photo was taken | Medium | "Reveals the exact time the photo was taken"
| DateTimeDigitized | When the file was saved/digitized, can differ from capture time| Low | "Reveals when this file was digitized." |

## Device 

| Tag | What it reveals | Severity | Risk message|
|---|---|---|---|
| Make | Camera/Phone manufacturer | Medium | "Reveals the device brand used to take this photo"|
| Model | Exact device model| Medium | "Reveals the exact device model used."|
| LensModel | Specific lens used | Low | "Reveals technical camera/lens details." |
| SerialNumber | Camera's unique serial number, when present | High | "Reveals the camera's unique serial number"|

## Identity 

| Tag | What it reveals | Severity | Risk message|
|---|---|---|---|
| Artist | Free-text field that can contain a name | High | "This file may directly contain a name." |
| Copyright | Free-text field, same risk as Artist | High | "This file may contain identifying text." |
| Embedded thumbnail | A preview image generated from the original photo — can still show content that was later cropped or edited out of the visible image | Medium | "The hidden preview image inside this file may show content you thought you removed." |

## Technical 

| Tag | What it reveals | Severity | Risk message|
|---|---|---|---|
| Software | Editing software and version used | Low | "Reveals what software was used to edit this file." |
| PNG tEXt / iTXt chunks | Free-text metadata, sometimes comments or usernames | Medium | "Contains free-text data that may include personal notes or usernames." |

## Implementation 

- Tags marked High are always flagged 'sensitive: True' regardless of value. 
- GPSLatitude and GPSLongitude are combined into one finding, not shown separately. 
- The embedded thumbnail check needs to compare thumbnail image data against the main image, not just read a tag
- If a tag is absent from a file omit it from the output rather than including it with a null value