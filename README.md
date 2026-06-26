
# 🖐️ LED Gesture Controller

A complete hardware and software ecosystem that uses live computer vision to control physical LEDs via hand gestures. 

This project utilizes a **"Smart Brain / Dumb Minion" architecture**: a Python desktop application (built with CustomTkinter and MediaPipe) handles all the complex AI image processing and rule mapping, while an Arduino UNO acts purely as a hardware driver, listening for serial commands.

## ✨ Features
* **Live Vision System:** Uses OpenCV and Google's MediaPipe for highly accurate, real-time hand skeleton tracking.
* **Dynamic Rule Builder:** A sleek GUI allows you to map specific hand poses (e.g., "Peace Sign", "Spider-Man") to specific hardware actions (ON, OFF, BLINK, CLEAR) without writing a single line of code.
* **Persistent Configuration:** User mappings are automatically saved to a `config.json` file.
* **Smart Anti-Spam & Latching:** The system intelligently sends commands only when a gesture changes, and safely turns off all LEDs if the hand leaves the frame.
* **Asynchronous Hardware:** The Arduino firmware uses non-blocking logic (`millis()`), allowing multiple LEDs to blink at completely different frequencies simultaneously.

---

## 🛠️ Hardware Setup

### Components Needed
* 1x Arduino UNO R3
* 1x Breadboard
* 2x Red LEDs
* 1x Yellow LED
* 2x Green LEDs
* 3x 220Ω Resistors
* Jumper Wires

### Circuit Wiring
* **Pin 2 (Red):** Connect to the Anodes of **both Red LEDs** (wired in parallel). Cathodes connect to Ground via a 220Ω resistor.
* **Pin 3 (Yellow):** Connect to the Anode of the **Yellow LED**. Cathode connects to Ground via a 220Ω resistor.
* **Pin 4 (Green):** Connect to the Anodes of **both Green LEDs** (wired in parallel). Cathodes connect to Ground via a 220Ω resistor.
* **GND:** Connect Arduino Ground to the breadboard's negative rail.

*(Note: Ensure you do not exceed the Arduino's 40mA per-pin current limit when wiring LEDs in parallel!)*

---

## 💻 Software Installation

### 1. The Arduino Firmware ("Dumb Minion")
1. Open the Arduino IDE.
2. Flash the provided universal serial controller sketch to your Arduino UNO.
3. Close the Arduino IDE (the Python app needs exclusive access to the USB port).

### 2. The Python Backend ("Smart Brain")
Ensure you have Python 3.8+ installed on your system.
1. Clone this repository:
   ```bash
   git clone [https://github.com/yourusername/led-gesture-controller.git](https://github.com/yourusername/led-gesture-controller.git)
   cd led-gesture-controller
