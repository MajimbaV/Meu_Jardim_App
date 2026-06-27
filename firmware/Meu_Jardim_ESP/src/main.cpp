#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <WiFiManager.h> 

// --- BIBLIOTECA DO DUPLO RESET ---
// Define que estamos usando o ESP8266
#define ESP8266
#include <ESP_DoubleResetDetector.h>

// Tempo em segundos que para apertar o RST pela segunda vez
#define DRD_TIMEOUT 5 
// Endereço na memória RTC onde ele anota que foi reiniciado (não mude)
#define DRD_ADDRESS 0

// Cria o objeto do detector
DoubleResetDetector* drd;

// --- CONFIGURAÇÕES DO EMQX (MQTT) ---
const char* mqtt_server = "emqx.ifspb-czemnumeros.com.br";
const int mqtt_port = 1883;
// exemplo de usuário e senha do EMQX (você pode criar o seu próprio usuário e senha no painel do EMQX)
const char* mqtt_user = "esp12";
const char* mqtt_pass = "esp12";

// --- MAPEAMENTO DE PINOS ---
const int RELE1 = 12; // D6
const int RELE2 = 13; // D7

WiFiClient espClient;
PubSubClient client(espClient);

// FUNÇÃO CALLBACK (Onde o comando chega do MQTT)
void callback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (int i = 0; i < length; i++) msg += (char)payload[i];
  
  if (String(topic) == "casa/rele1") {
    if (msg == "ON") digitalWrite(RELE1, LOW); 
    else digitalWrite(RELE1, HIGH);
  } 
  else if (String(topic) == "casa/rele2") {
    if (msg == "ON") digitalWrite(RELE2, LOW);
    else digitalWrite(RELE2, HIGH);
  }
}

// FUNÇÃO DE RECONEXÃO DO MQTT
void reconnect() {
  while (!client.connected()) {
    Serial.print("Tentando conexão MQTT...");
    String clientId = "ESP8266Client-";
    clientId += String(random(0xffff), HEX);

    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      Serial.println("CONECTADO AO EMQX!");
      client.subscribe("casa/rele1");
      client.subscribe("casa/rele2");
    } else {
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  
  // Configura os pinos dos relés e inicia desligados
  pinMode(RELE1, OUTPUT);
  pinMode(RELE2, OUTPUT);
  digitalWrite(RELE1, HIGH); 
  digitalWrite(RELE2, HIGH);

  WiFiManager wifiManager;

  // Inicializa o Detector de Duplo Reset
  drd = new DoubleResetDetector(DRD_TIMEOUT, DRD_ADDRESS);

  // --- A MÁGICA ACONTECE AQUI ---
  // Verifica se o botão RST foi apertado duas vezes rapidamente
  if (drd->detectDoubleReset()) {
    Serial.println("Duplo clique no RST detectado!");
    Serial.println("Limpando as configuracoes de WiFi salvas...");
    wifiManager.resetSettings(); // Apaga o WiFi antigo da memória!
  } else {
    Serial.println("Inicializacao normal.");
  }



  // ==========================================================
  // --- INÍCIO DA PERSONALIZAÇÃO E TRADUÇÃO DA PÁGINA ---
  // ==========================================================

  // 1. LIMPAR O MENU PRINCIPAL
  std::vector<const char *> menu = {"wifi", "info", "exit"};
  wifiManager.setMenu(menu);

  // 2. INJETAR CSS (CORES) + JAVASCRIPT (TRADUÇÃO)
  String htmlPersonalizado = "<style>"
    "body { background-color: #f0f0f5; color: #333333; }"
    "button { background-color: #9932CC; color: white; border-radius: 25px; padding: 12px; font-weight: bold; border: none; box-shadow: 0px 4px 6px rgba(0,0,0,0.2); margin-bottom: 10px; }"
    "button:hover { background-color: #4B0082; }"
    /* Título Personalizado */
    "div.c h1 { display: none; }" 
    "div.c::before { content: 'NIA Automação'; display: block; font-size: 2.5em; font-weight: bold; color: #8A2BE2; margin-top: 20px; margin-bottom: 20px; }"
    /* Estilo das caixas de mensagem (Avisos) */
    ".msg { background-color: #d1c4e9; color: #311b92; border-radius: 10px; padding: 15px; font-weight: bold; }"
    "</style>"
    
    /* INÍCIO DO JAVASCRIPT DE TRADUÇÃO */
    "<script>"
    "window.onload = function() {"
      
      /* Traduz os Botões */
      "var botoes = document.querySelectorAll('button');"
      "botoes.forEach(function(btn){"
        "if(btn.innerText.includes('Save')) btn.innerText = 'Salvar';"
        "if(btn.innerText.includes('Refresh')) btn.innerText = 'Atualizar Redes';"
        "if(btn.innerText.includes('Exit')) btn.innerText = 'Sair';"
        "if(btn.innerText.includes('Configure WiFi')) btn.innerText = 'Configurar WiFi';"
        "if(btn.innerText.includes('Info')) btn.innerText = 'Informações do Sistema';"
      "});"

      /* Traduz as caixas roxas de Mensagem (originais da biblioteca) */
      "var mensagens = document.querySelectorAll('.msg');"
      "mensagens.forEach(function(msg){"
        "if(msg.innerHTML.includes('No AP set')) msg.innerHTML = 'Nenhuma rede selecionada. Clique em uma rede acima.';"
        "if(msg.innerHTML.includes('Saving Credentials')) msg.innerHTML = 'Salvando Configurações...<br><br>Tentando conectar o aparelho na sua rede.<br>Você já pode fechar esta página.';"
      "});"

      /* Traduz o texto solto 'Show Password' da caixinha de seleção */
      "var textos = document.createTreeWalker(document.body, 4, null, false);"
      "while(node = textos.nextNode()){"
        "if(node.nodeValue.includes('Show Password')) node.nodeValue = node.nodeValue.replace('Show Password', ' Mostrar Senha');"
      "}"
      
    "};"
    "</script>";
    
  // Aplica o Estilo e o Script na página
  wifiManager.setCustomHeadElement(htmlPersonalizado.c_str());

  // ==========================================================
  // --- FIM DA PERSONALIZAÇÃO E TRADUÇÃO ---
  // ==========================================================


  // Tenta conectar ou abre o Portal Cativo
  if (!wifiManager.autoConnect("NIA_Automacao")) {
    Serial.println("Falha na conexão Wi-Fi. Reiniciando...");
    delay(3000);
    ESP.restart(); 
    delay(5000);
  }

  Serial.println("\nWiFi conectado!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  // Diz para o detector que o dispositivo ligou corretamente
  // e limpa a janela de duplo clique
  drd->loop();

  if (!client.connected()) {
    reconnect();
  }
  client.loop();
}