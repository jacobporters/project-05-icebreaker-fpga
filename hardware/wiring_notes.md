# Wiring Notes -- iCEBreaker FPGA V1.1a

## Board pinout used (iCEBreaker V1.1a, iCE40UP5K, SG48 package)

| Signal | FPGA pin | Notes |
|---|---|---|
| `clk` | 35 | Onboard 12MHz oscillator |
| `led1`-`led5` | 26, 27, 25, 23, 21 | Breakaway tab, no soldering required |
| `btn1`-`btn3` | 20, 19, 18 | Breakaway tab, active-high |
| `led_red_n`/`led_grn_n`/`led_blu_n` | 39, 40, 41 | Onboard RGB LED, active-low |
| `tx` | 9 | Routed to onboard FTDI FT2232H channel B -- enumerates as its own `/dev/cu.usbserial-*` device, separate from the programming channel. No external USB-serial adapter needed. |

PMOD1A/PMOD1B (2x6, 2.54mm pitch, positions 1-4/7-10 per side) were soldered but ultimately not used in the final design -- `tx` was moved to the board's built-in UART pin (9) instead, once it was clear the FTDI chip already exposes a second, independent serial channel with no extra hardware required.

## iCEBreaker <-> ESP32 (Project 3 datalogger) link

| iCEBreaker | ESP32 | Notes |
|---|---|---|
| `tx` (pin 9, physically the onboard header pin routed to it) | GPIO16 | UART2 RX, remapped via `Serial2.begin(baud, SERIAL_8N1, 16, -1)` |
| GND | GND | Shared ground -- required for UART reference |

Both boards run 3.3V logic -- no level shifting needed for this link.

GPIO16 was chosen over the other free ESP32 pins available (GPIO2, GPIO5) because both of those are boot-time strapping pins; wiring an external signal to them risks interfering with the ESP32's boot sequence.

## UART protocol (message override)

Custom framing over the 9600-baud link, byte values chosen arbitrarily:

| Byte | Meaning |
|---|---|
| `0x01` | Start override -- ESP32 begins buffering incoming bytes as message text, OLED measurement rows hidden |
| (ASCII bytes) | Message text, one byte per character |
| `0x00` | End of message text -- message is now complete and displayed |
| `0x02` | End override -- OLED reverts to normal sensor display |

## Debugging notes worth keeping

- **Probe attenuation mismatch**: a 10x/1x mismatch between the physical probe switch and the scope's channel setting produced a false ~330mV reading on what was actually a clean 3.3V logic line. Always confirm both sides agree.
- **Locating a physical pin without trusting voltage alone**: unused, floating iCE40 I/O pins commonly settle near 3.3V due to internal weak pull-ups -- meaning a steady 3.3V reading can't distinguish a real driven pin from a floating neighbor. Resolved by flashing a minimal design that drives the pin of interest to a clean 0V, then locating it on the physical header by elimination (`firmware/debug_pin_finder.v`).
- **Auto-measurement pulse-width readings can mislead**: the scope's automatic `Wid+` parameter read ~144µs against an expected ~104.2µs (9600 baud bit period) -- traced to the measurement aggregating across pulses of different widths (idle-high time vs. a single bit), not an actual timing bug. Manually reading a single isolated pulse against the grid divisions (~104µs) confirmed the design was correct.
