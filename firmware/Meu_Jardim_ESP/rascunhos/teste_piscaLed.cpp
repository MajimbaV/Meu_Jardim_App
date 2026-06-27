#include <Arduino.h>

// O pino 2 é onde fica o LED azul embutido na placa da maioria dos ESP8266
#define PINO_LED 2 

void setup() {
  // Inicia o monitor serial na mesma velocidade que você configurou no .ini
  Serial.begin(115200);
  
  // Dá um pequeno tempo para o serial estabilizar
  delay(1000); 
  
  // Configura o pino do LED como saída (a lógica será a mesma para o relê depois)
  pinMode(PINO_LED, OUTPUT);
  
  Serial.println("\n--- Sistema Meu Jardim Iniciado! ---");
}

void loop() {
  // No ESP8266, o estado LOW (baixo) geralmente LIGA o LED embutido
  digitalWrite(PINO_LED, LOW);
  Serial.println("Rega LIGADA");
  delay(2000); // Fica ligado por 2 segundos
  
  // O estado HIGH (alto) DESLIGA o LED embutido
  digitalWrite(PINO_LED, HIGH);
  Serial.println("Rega DESLIGADA");
  delay(2000); // Fica desligado por 2 segundos
}