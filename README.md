# chordy
A six-button, one-handed, portable keyboard

## Elements

* Momentary switches
* Raspberry Pi Pico W
* Battery
* Charger shim

## Bill of Materials

| Item | Qty | Description | Notes |
| --- | --- | --- | --- |
| Raspberry Pi Pico W | 1 | Dual-core microcontroller board with Wi-Fi | Main controller for the keyboard. |
| Momentary pushbutton switches | 6 | Low-profile, normally-open tactile switches | Primary input keys; choose caps to suit ergonomics. |
| LiPo battery | 1 | 3.7 V rechargeable lithium polymer cell (≥500 mAh) | Capacity determines runtime; ensure it fits the enclosure. |
| LiPo charger shim | 1 | Pico-compatible charging interface (e.g., Pimoroni LiPo SHIM) | Handles safe charging and power management. |
| Power switch (optional) | 1 | SPST slide or toggle switch | Allows hard power cutoff when transporting the device. |
| 3D printed enclosure | 1 | Printed from `model/flat_pipe_with_finger_grooves.scad` | Customize print settings for comfort and durability. |
| Hookup wire / ribbon cable | As needed | 28–30 AWG stranded wire | Connects switches to the Pico; consider color-coding rows/columns. |

