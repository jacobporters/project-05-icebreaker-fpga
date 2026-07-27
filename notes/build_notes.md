# Build Notes

## Sequence

1. Soldered PMOD1A/PMOD1B headers (2x6, 2.54mm) -- ultimately unused in the final design.
2. Installed the OSS CAD Suite (Yosys, nextpnr-ice40, icepack, iceprog) toolchain.
3. Blinky -- full synth -> place&route -> pack -> program flow, verified on the breakaway-tab LED.
4. Combinational button->LED, then a debounced version using a saturating counter (60,000-cycle window at 12MHz for a ~5ms bounce tolerance).
5. Binary counter and one-hot "walker" pattern across the 5 breakaway LEDs -- `case` statements, bit-slicing, concatenation.
6. Traffic light FSM -- first Moore machine (separate sequential state-transition block and combinational output block).
7. Standalone baud-rate clock divider (12MHz / 9600 = 1250 cycles/bit, verified exact since it divides evenly), confirmed by dividing further down to a visible ~1Hz LED toggle before trusting it inside a larger design.
8. Full UART transmitter (`uart_tx.v`) -- FSM + shift-out, parameterized bit timing so the same core module could run at real speed or 1 second/bit for eyeball verification.
9. Oscilloscope verification of the real-speed (9600 baud) frame on a FNIRSI 2C53T.
10. Routed `tx` to the iCEBreaker's built-in FTDI UART pin (pin 9) instead of a PMOD, since the onboard FT2232H already exposes a second, independent serial channel.
11. Wired iCEBreaker `tx` directly into ESP32 GPIO16 (Project 3's datalogger board), no level shifting needed (both 3.3V).
12. Designed a simple byte-level protocol (`0x01`/text/`0x00`/`0x02`) so button presses on the FPGA override the Project 3 OLED with a message, and drive a matching popup on the Flask dashboard via UDP.
13. `fpga_messenger.v` -- final button-driven sequencer: button 1 sends the start code, button 2 sends a fixed message + terminator, button 3 sends the revert code. Guards ensure one transmission in flight can't be interrupted by another button press mid-byte.

## Notable debugging

**Scope trigger wouldn't fire despite correct settings.** Spent significant time on this before isolating it as a probe-connection/measurement-interpretation issue rather than a design bug:
- Confirmed the FPGA was actually transmitting independent of the scope, by slowing the UART down to 1 second/bit and watching an LED mirror `tx` directly with the naked eye.
- Ruled out grounding, probe attenuation (10x/1x mismatch was a real, separate bug caught along the way), and pin location (resolved with a small diagnostic module that drives one pin to a clean 0V so it can be found on the physical header by elimination -- floating iCE40 pins commonly idle near 3.3V, so voltage alone can't distinguish a real signal pin from an unused neighbor).
- Switching the scope from Single to Normal trigger mode was what finally caught the fast (real 9600 baud) frame reliably.

**Scope auto-measurement (`Wid+`) read ~144µs against an expected ~104.2µs.** Traced to the auto-measurement including/averaging pulses of different widths in the capture window (idle-high time vs. a single bit), not an actual timing error -- confirmed correct by manually reading one isolated pulse against the grid (~104µs measured, matching the 9600-baud calculation).

## What's not in this repo

The FPGA -> ESP32 link is one-directional only (FPGA sends, ESP32 only receives). A UART receiver on the FPGA side (so the ESP32 or a laptop could send commands back) was considered as a stretch goal but not built for this project.
