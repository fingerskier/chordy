"""Micropython firmware for Raspberry Pi Pico W BLE chorded keyboard.

This script configures the Pico W as a Bluetooth Low Energy HID keyboard
with six digital inputs (GP0-GP5). Each unique combination of pressed
buttons maps to a specific keyboard output. The firmware debounces button
presses, maintains the current chord state, and transmits HID key reports
when a chord changes.
"""
from micropython import const
import bluetooth
import machine
import struct
import utime

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)

_HID_INFO = struct.pack("<HHBB", 0x0111, 0x0000, 0x01, 0x01)

# HID report map defining a simple keyboard with one input report.
_HID_REPORT_MAP = bytes(
    (
        0x05,
        0x01,  # USAGE_PAGE (Generic Desktop)
        0x09,
        0x06,  # USAGE (Keyboard)
        0xA1,
        0x01,  # COLLECTION (Application)
        0x85,
        0x01,  #   REPORT_ID (1)
        0x05,
        0x07,  #   USAGE_PAGE (Keyboard)
        0x19,
        0xE0,  #   USAGE_MINIMUM (Keyboard LeftControl)
        0x29,
        0xE7,  #   USAGE_MAXIMUM (Keyboard Right GUI)
        0x15,
        0x00,  #   LOGICAL_MINIMUM (0)
        0x25,
        0x01,  #   LOGICAL_MAXIMUM (1)
        0x75,
        0x01,  #   REPORT_SIZE (1)
        0x95,
        0x08,  #   REPORT_COUNT (8)
        0x81,
        0x02,  #   INPUT (Data,Var,Abs)
        0x95,
        0x01,  #   REPORT_COUNT (1)
        0x75,
        0x08,  #   REPORT_SIZE (8)
        0x81,
        0x01,  #   INPUT (Const,Array,Abs) - Reserved byte
        0x95,
        0x06,  #   REPORT_COUNT (6)
        0x75,
        0x08,  #   REPORT_SIZE (8)
        0x15,
        0x00,  #   LOGICAL_MINIMUM (0)
        0x25,
        0x65,  #   LOGICAL_MAXIMUM (101)
        0x05,
        0x07,  #   USAGE_PAGE (Keyboard)
        0x19,
        0x00,  #   USAGE_MINIMUM (Reserved)
        0x29,
        0x65,  #   USAGE_MAXIMUM (Keyboard Application)
        0x81,
        0x00,  #   INPUT (Data,Ary,Abs)
        0xC0,
    )
)

# UUID definitions for the HID service and characteristics.
_HID_UUID = bluetooth.UUID(0x1812)
_HID_REPORT_CHAR = (
    bluetooth.UUID(0x2A4D),
    bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,
)
_HID_REPORT_MAP_CHAR = (bluetooth.UUID(0x2A4B), bluetooth.FLAG_READ)
_HID_INFO_CHAR = (bluetooth.UUID(0x2A4A), bluetooth.FLAG_READ)
_HID_CONTROL_POINT_CHAR = (
    bluetooth.UUID(0x2A4C),
    bluetooth.FLAG_WRITE_NO_RESPONSE,
)

_HID_SERVICE = (
    _HID_UUID,
    (
        _HID_REPORT_CHAR,
        _HID_REPORT_MAP_CHAR,
        _HID_INFO_CHAR,
        _HID_CONTROL_POINT_CHAR,
    ),
)

# HID key codes for common keys.
KEY_CODES = {
    "A": 0x04,
    "B": 0x05,
    "C": 0x06,
    "D": 0x07,
    "E": 0x08,
    "F": 0x09,
    "G": 0x0A,
    "H": 0x0B,
    "I": 0x0C,
    "J": 0x0D,
    "K": 0x0E,
    "L": 0x0F,
    "M": 0x10,
    "N": 0x11,
    "O": 0x12,
    "P": 0x13,
    "Q": 0x14,
    "R": 0x15,
    "S": 0x16,
    "T": 0x17,
    "U": 0x18,
    "V": 0x19,
    "W": 0x1A,
    "X": 0x1B,
    "Y": 0x1C,
    "Z": 0x1D,
    "1": 0x1E,
    "2": 0x1F,
    "3": 0x20,
    "4": 0x21,
    "5": 0x22,
    "6": 0x23,
    "7": 0x24,
    "8": 0x25,
    "9": 0x26,
    "0": 0x27,
    "ENTER": 0x28,
    "ESC": 0x29,
    "BACKSPACE": 0x2A,
    "TAB": 0x2B,
    "SPACE": 0x2C,
}

# Combination map: tuples of pressed button indices -> (modifier, [keycodes])
# Buttons are indexed according to their order in BUTTON_PINS.
COMBO_MAP = {
    (0,): (0x00, [KEY_CODES["F"]]),
    (1,): (0x00, [KEY_CODES["J"]]),
    (2,): (0x00, [KEY_CODES["D"]]),
    (3,): (0x00, [KEY_CODES["K"]]),
    (4,): (0x00, [KEY_CODES["S"]]),
    (5,): (0x00, [KEY_CODES["L"]]),
    (0, 1): (0x00, [KEY_CODES["SPACE"]]),
    (2, 3): (0x00, [KEY_CODES["ENTER"]]),
    (4, 5): (0x00, [KEY_CODES["TAB"]]),
    (0, 2): (0x02, [KEY_CODES["A"]]),  # Shift + A
    (1, 3): (0x02, [KEY_CODES["H"]]),  # Shift + H
    (0, 5): (0x00, [KEY_CODES["BACKSPACE"]]),
}

BUTTON_PINS = (0, 1, 2, 3, 4, 5)
DEBOUNCE_MS = const(25)
POLL_INTERVAL_MS = const(10)


class BLEKeyboard:
    """Minimal BLE HID keyboard implementation."""

    def __init__(self, ble, name="ChordyPad"):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._report_handle, self._report_map_handle, self._info_handle, self._control_handle),) = self._ble.gatts_register_services(
            (_HID_SERVICE,)
        )
        self._ble.gatts_write(self._report_map_handle, _HID_REPORT_MAP)
        self._ble.gatts_write(self._info_handle, _HID_INFO)
        self._connections = set()
        self._payload = advertising_payload(name=name, services=[_HID_UUID])
        self._advertise()

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.discard(conn_handle)
            self._advertise()

    def _advertise(self):
        self._ble.gap_advertise(100_000, adv_data=self._payload)

    def send_report(self, report):
        for conn_handle in self._connections:
            self._ble.gatts_notify(conn_handle, self._report_handle, report)

    def key_press(self, modifier, keycodes):
        """Send a key press report with given modifier and up to six keycodes."""
        padded = keycodes + [0x00] * (6 - len(keycodes))
        report = struct.pack("<BB6B", 0x01, modifier, *padded)
        self.send_report(report)

    def release_all(self):
        report = struct.pack("<BB6B", 0x01, 0x00, 0, 0, 0, 0, 0, 0)
        self.send_report(report)


def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None):
    payload = bytearray()
    def _append(ad_type, value):
        payload.extend((len(value) + 1, ad_type))
        payload.extend(value)

    if name:
        _append(0x09, name.encode())
    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                _append(0x03, b)
            elif len(b) == 16:
                _append(0x07, b)
    return payload


def create_buttons(pins):
    return [machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP) for pin in pins]


def scan_buttons(buttons):
    pressed = [index for index, pin in enumerate(buttons) if not pin.value()]
    return tuple(pressed)


def main():
    ble = bluetooth.BLE()
    keyboard = BLEKeyboard(ble)
    buttons = create_buttons(BUTTON_PINS)
    last_state = ()
    last_change = utime.ticks_ms()

    while True:
        state = scan_buttons(buttons)
        now = utime.ticks_ms()

        if state != last_state and utime.ticks_diff(now, last_change) > DEBOUNCE_MS:
            last_state = state
            last_change = now
            keyboard.release_all()

            combo = COMBO_MAP.get(state)
            if combo:
                modifier, keycodes = combo
                keyboard.key_press(modifier, keycodes)

        utime.sleep_ms(POLL_INTERVAL_MS)


if __name__ == "__main__":
    main()
