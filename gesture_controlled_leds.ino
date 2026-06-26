const int redPin = 2;
const int yellowPin = 3;
const int greenPin = 4;

void setup() {
  // Start serial communication at 9600 baud rate
  Serial.begin(9600);
  
  pinMode(redPin, OUTPUT);
  pinMode(yellowPin, OUTPUT);
  pinMode(greenPin, OUTPUT);
}

void loop() {
  // Check if the computer has sent any data
  if (Serial.available() > 0) {
    char command = Serial.read();

    // Turn off all LEDs first to reset the state
    digitalWrite(redPin, LOW);
    digitalWrite(yellowPin, LOW);
    digitalWrite(greenPin, LOW);

    // Turn on the specific LED based on the finger count
    if (command == '1') {
      digitalWrite(redPin, HIGH);    // 1 Finger = Red
    } 
    else if (command == '2') {
      digitalWrite(yellowPin, HIGH); // 2 Fingers = Yellow
    } 
    else if (command == '3') {
      digitalWrite(greenPin, HIGH);  // 3+ Fingers = Green
    }
    // If '0' is sent, they all just remain off
  }
}