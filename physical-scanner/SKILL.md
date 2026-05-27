---
name: physical-scanner
description: Scan physical documents to PDF via AirPrint/eSCL network scanners using the direct eSCL HTTP protocol. No proprietary drivers needed. Supports flatbed and ADF (auto document feeder), single and duplex scanning.
---

# Physical Scanner — eSCL / AirScan

Scan documents directly from an AirPrint-compatible network scanner/printer using the **eSCL** (Email-capable Scanning Lite) protocol over HTTP. Works with any modern MFP that supports Apple AirScan / AirPrint scanning (Canon, HP, Brother, Epson, etc.).

**Compatibility**: Canon PIXMA G4010 series (tested), and any device supporting eSCL (list: <https://support.apple.com/en-us/HT201311>).

---

## Protocol Overview

eSCL is a vendor-neutral HTTP-based protocol for driverless scanning. It is also known as:

- **Apple AirScan / AirPrint scanning**
- **Mopria Scan**
- **eSCL** (official protocol name)

The backend implementation reference: <https://github.com/alexpevzner/sane-airscan>

SANE (Scanner Access Now Easy) integration: <https://wiki.archlinux.org/title/SANE> · <https://wiki.debian.org/SaneOverNetwork>

---

## Scanner Discovery

### 1. Find the scanner on the network (Bonjour/mDNS)

```bash
# Browse for eSCL scanners
dns-sd -B _uscan._tcp

# Browse for printers (some also support scanning)
dns-sd -B _ipp._tcp
dns-sd -B _ipps._tcp
```

Expected output:
```
Browsing for _uscan._tcp
  Add  Canon G4010 series  _uscan._tcp.  local.
```

### 2. Resolve scanner details (hostname, port, capabilities)

```bash
dns-sd -L "Canon G4010 series" _uscan._tcp local.
```

Output shows:
```
hostname:port  (e.g., 0924B3000000.local.:80)
rs=eSCL      → scanner supports eSCL
cs=color     → color modes: grayscale,color
is=platen,adf → scan sources: flatbed, ADF
duplex=F     → duplex not supported
```

### 3. Alternative discovery by OS

**macOS:**
```bash
system_profiler SPPrintersDataType | grep -A 20 "Scanning support: Yes"
```

If Bonjour browsing does not show the scanner, derive the printer hostname/URL from CUPS:

```bash
# List configured printers and their device URIs
lpstat -t

# Example output:
# device for Canon_G4010_series: dnssd://Canon%20G4010%20series._ipps._tcp.local./?uuid=...

# Get detailed printer info and PPD path
lpstat -l -p Canon_G4010_series

# Inspect the PPD for AirPrint URLs/hostnames
head -60 /private/etc/cups/ppd/Canon_G4010_series.ppd
```

Look for lines such as:

```text
*APSupplies: "http://0924B3000000.local./index.html?page=PAGE_INK"
```

This reveals the printer hostname (`0924B3000000.local.` in this example). Once reachable, use it for read-only eSCL checks:

```bash
curl -s http://0924B3000000.local./eSCL/ScannerStatus
curl -s http://0924B3000000.local./eSCL/ScannerCapabilities
```

Notes:
- The `dnssd://..._ipps._tcp.local` URI is the Bonjour service name for printing, not necessarily the direct HTTP hostname.
- The PPD `APSupplies` URL often contains the real device hostname.
- Do not create a scan job unless explicitly requested; `ScannerStatus` and `ScannerCapabilities` are read-only.

**Linux:**
```bash
# Using avahi (native mDNS)
avahi-browse -rt _uscan._tcp

# Using SANE
scanimage -L
```

---

## eSCL Protocol — Endpoints

All endpoints are HTTP GET/POST/DELETE on port **80** (or **443** for HTTPS) of the scanner.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/eSCL/ScannerStatus` | Get scanner status and job list |
| `GET` | `/eSCL/ScannerCapabilities` | Get detailed capabilities (resolutions, formats, sources) |
| `POST` | `/eSCL/ScanJobs` | Create a scan job |
| `GET` | `/eSCL/ScanJobs/{jobId}` | Get job status |
| `GET` | `/eSCL/ScanJobs/{jobId}/NextDocument` | Retrieve scanned image/PDF |
| `DELETE` | `/eSCL/ScanJobs/{jobId}` | Cancel a scan job |

---

## Scanning Workflow

### Step 1: Check scanner status

```bash
curl -s http://<scanner-ip>:80/eSCL/ScannerStatus
```

Key fields:
- `<pwg:State>` — `Idle`, `Processing`, `Down`
- `<scan:AdfState>` — `ScannerAdfLoaded` (paper in tray), `ScannerAdfEmpty`
- `<pwg:ImagesCompleted>` — number of images scanned so far

### Step 2: Check capabilities

```bash
curl -s http://<scanner-ip>:80/eSCL/ScannerCapabilities
```

Look for:
- `<scan:PlatenInputCaps>` — flatbed settings
- `<scan:AdfSimplexInputCaps>` — ADF simplex settings
- `<scan:AdfDuplexInputCaps>` — ADF duplex settings (if present)
- `<scan:DocumentFormatExt>` — `image/jpeg`, `application/pdf`
- `<scan:ColorModes>` — `Grayscale8`, `RGB24`
- `<scan:SupportedResolutions>` — available DPIs

### Step 3: Create a scan job

**Flatbed scan (single page, PDF, grayscale):**

```bash
SCAN_SETTINGS='<?xml version="1.0" encoding="UTF-8"?>
<scan:ScanSettings xmlns:scan="http://schemas.hp.com/imaging/escl/2011/05/03"
                   xmlns:pwg="http://www.pwg.org/schemas/2010/12/sm"
                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <pwg:Version>2.63</pwg:Version>
  <scan:Intent>TextAndGraphic</scan:Intent>
  <scan:DocumentFormatExt>application/pdf</scan:DocumentFormatExt>
  <scan:InputSource>Platen</scan:InputSource>
  <scan:ColorMode>Grayscale8</scan:ColorMode>
  <scan:XResolution>300</scan:XResolution>
  <scan:YResolution>300</scan:YResolution>
</scan:ScanSettings>'

curl -s -D - -X POST "http://<scanner-ip>:80/eSCL/ScanJobs" \
  -H "Content-Type: text/xml" \
  -d "$SCAN_SETTINGS"
```

Response includes `Location: http://.../eSCL/ScanJobs/{jobId}` — save this URI.

**ADF simplex scan** — same as above but with `<scan:InputSource>ADF</scan:InputSource>`.

**ADF duplex scan** — add `<scan:Duplex>true</scan:Duplex>`.

**JPEG output** — use `<scan:DocumentFormatExt>image/jpeg</scan:DocumentFormatExt>`.

### Step 4: Wait and retrieve

```bash
# Wait for scanning to complete (5-30 seconds depending on scanner)
sleep 10

# Download the scanned image/PDF
curl -s -o output.pdf \
  "http://<scanner-ip>:80/eSCL/ScanJobs/{jobId}/NextDocument"
```

### Step 5: Check for additional pages (ADF multi-page)

```bash
# Try to get next page — returns 404 if no more pages
curl -s -o output-2.pdf \
  "http://<scanner-ip>:80/eSCL/ScanJobs/{jobId}/NextDocument"
```

### Step 6: Cancel/close the job when done

```bash
curl -s -X DELETE "http://<scanner-ip>:80/eSCL/ScanJobs/{jobId}"
```

---

## Recommended Scan Settings for Documents (Invoices)

| Setting | Value | Reason |
|---|---|---|
| ColorMode | `Grayscale8` | B&W documents, smaller files |
| Resolution | `300` dpi | Good quality for text OCR |
| Format | `application/pdf` | Standard, compressible |
| Intent | `TextAndGraphic` | Optimized for documents |
| InputSource | `ADF` (multi-page) or `Platen` (single) | As needed |

---

---

## Post-Scan: Extract & Describe Scanned Documents

Once you've scanned a document, analyze it with the **[describe-image](../describe-image/SKILL.md)** skill using pi's vision models:

```bash
cd ~/.agents/skills/describe-image
./describe-image.sh scan-output.pdf
./describe-image.sh page1.pdf page2.pdf page3.png
./describe-image.sh --provider openai-codex --model gpt-5.4 invoice.pdf
```

See [describe-image](../describe-image/SKILL.md) for full details.

---

## macOS Integration

### Via SANE (sane-airscan backend)

The `sane-airscan` project (<https://github.com/alexpevzner/sane-airscan>) provides a SANE backend for eSCL scanners. On macOS:

1. Install `sane-backends` via Homebrew:
   ```bash
   brew install sane-backends
   ```

2. Build `sane-airscan` from source:
   ```bash
   git clone https://github.com/alexpevzner/sane-airscan.git
   cd sane-airscan
   make
   sudo make install
   ```

3. Test:
   ```bash
   scanimage -L
   ```

**Note**: On macOS, the native Bonjour/mDNS replaces Avahi (Linux). The build requires `gnutls`, `libjpeg`, `libpng`, `libtiff` and `avahi-devel` (install via Homebrew). The direct eSCL HTTP approach (above) is simpler and doesn't require building.

### Via native AirScanScanner.app (macOS)

macOS includes `/System/Library/Image Capture/Devices/AirScanScanner.app` but it runs as an XPC service and cannot be invoked directly from the command line. Use the eSCL HTTP approach instead.

---

## Troubleshooting

### Scanner not detected

```bash
# Check Bonjour/mDNS
dns-sd -B _uscan._tcp
dns-sd -B _scanner._tcp

# Check printer listing (macOS)
system_profiler SPPrintersDataType | grep -A 30 "Canon\|HP\|Brother\|Epson"
```

### Scanner stuck on "ScannerAdfLoaded"

1. Check for paper jams — open ADF cover, remove any stuck paper
2. Power-cycle the printer (off → 10s → on)
3. Cancel any stale jobs:
   ```bash
   curl -s -X DELETE "http://<scanner-ip>:80/eSCL/ScanJobs/{jobId}"
   ```

### Scan job not progressing

- Wait longer (some scanners are slow to warm up)
- Check status: `curl -s http://<scanner-ip>:80/eSCL/ScannerStatus`
- Cancel and retry with lower resolution (150 DPI)

### Scanner capabilities XML empty/malformed

Some printers require setting up AirPrint scanning on their web console:
- Canon: Home → Menu → Preferences → Network → TCP/IP Settings → Network Link Scan Settings → **On**
- Brother: Home → Menu → Preferences → Network → TCP/IP Settings → WSD Settings → Use WSD Scanning → **ON**
- HP: Settings → Security → Administrator Settings → Enable Scan from a Computer → **Apply**

---

## References

| Resource | URL |
|---|---|
| eSCL protocol spec (HP namespace) | <http://schemas.hp.com/imaging/escl/2011/05/03> |
| sane-airscan project | <https://github.com/alexpevzner/sane-airscan> |
| Apple AirPrint compatible devices | <https://support.apple.com/en-us/HT201311> |
| SANE project | <http://www.sane-project.org/> |
| Arch Linux SANE wiki | <https://wiki.archlinux.org/title/SANE> |
| Debian SANE over network | <https://wiki.debian.org/SaneOverNetwork> |
| eSCL protocol description | <https://github.com/markosjal/AirScan-eSCL.txt> |
| python-scan-eSCL (Python client) | <https://github.com/kno10/python-scan-eSCL> |
