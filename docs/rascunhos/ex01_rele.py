import flet as ft
import paho.mqtt.client as mqtt

# --- CONFIGURAÇÕES DO MQTT (Idênticas ao ESP8266) ---
MQTT_BROKER = "emqx.ifspb-czemnumeros.com.br"
MQTT_PORT = 1883
MQTT_USER = "esp12_01"
MQTT_PASS = "esp12_01"

TOPIC_RELE1 = "casa/rele1"
TOPIC_RELE2 = "casa/rele2"

def main(page: ft.Page):
    # --- CONFIGURAÇÕES DA TELA DO APP ---
    page.title = "NIA Automação - Meu Jardim"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.padding = 30
    page.window.width = 400  # Tamanho simulando tela de celular no PC
    page.window.height = 700

    # Textos da Interface
    titulo = ft.Text("Meu Jardim", size=32, weight=ft.FontWeight.BOLD, color="#8A2BE2")
    status_text = ft.Text("Conectando...", color=ft.colors.ORANGE, italic=True)

    # --- FUNÇÕES MQTT ---
    # Função chamada quando o app consegue conectar no servidor
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            status_text.value = "🟢 Conectado ao Servidor"
            status_text.color = ft.colors.GREEN
        else:
            status_text.value = f"🔴 Erro de conexão: {rc}"
            status_text.color = ft.colors.RED
        page.update()

    # Configurando o Cliente MQTT
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "AppCelular_MeuJardim")
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    
    # Inicia a conexão em segundo plano (para não travar o app)
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        status_text.value = f"🔴 Erro: {e}"
        page.update()

    # --- AÇÕES DOS BOTÕES (SWITCHES) ---
    def acionar_rele1(e):
        comando = "ON" if switch1.value else "OFF"
        client.publish(TOPIC_RELE1, comando)
        print(f"Relê 1 -> {comando}")

    def acionar_rele2(e):
        comando = "ON" if switch2.value else "OFF"
        client.publish(TOPIC_RELE2, comando)
        print(f"Relê 2 -> {comando}")

    # --- ELEMENTOS VISUAIS (BOTÕES) ---  #### está dando erro na versão do flet, então usei o Switch"
    switch1 = ft.Switch(label="Válvula de Água (Relê 1)", on_change=acionar_rele1, scale=1.5)
    switch2 = ft.Switch(label="Iluminação (Relê 2)", on_change=acionar_rele2, scale=1.5)

    # Adiciona tudo na tela
    page.add(
        titulo,
        status_text,
        ft.Divider(height=40, color=ft.colors.TRANSPARENT), # Espaço vazio
        switch1,
        ft.Divider(height=20, color=ft.colors.TRANSPARENT), # Espaço vazio
        switch2
    )

# Roda o aplicativo
ft.app(target=main)