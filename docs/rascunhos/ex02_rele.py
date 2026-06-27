import flet as ft
import paho.mqtt.client as mqtt
import random

# --- CONFIGURAÇÕES ---
MQTT_SERVER = "emqx.ifspb-czemnumeros.com.br"
MQTT_PORT = 1883
MQTT_USER = "esp12"
MQTT_PASS = "esp12"

def main(page: ft.Page):
    page.title = "Controle ESP12"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.window_height = 600
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Círculo de status feito com um Container (Não usa ícone, deu problema de vesão do flet no meu PC)
    status_led = ft.Container(width=12, height=12, bgcolor="red", border_radius=6)
    status_text = ft.Text("Desconectado", color="red")

    # Configuração do Cliente MQTT
    client_id = f"python-app-{random.randint(0, 999)}"
    
    # Suporte para Paho-MQTT v1 e v2
    try:
        mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
    except:
        mqttc = mqtt.Client(client_id=client_id)

    mqttc.username_pw_set(MQTT_USER, MQTT_PASS)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            status_text.value = "Online"
            status_text.color = "green"
            status_led.bgcolor = "green"
        else:
            status_text.value = f"Erro {rc}"
        page.update()

    mqttc.on_connect = on_connect

    try:
        mqttc.connect(MQTT_SERVER, MQTT_PORT)
        mqttc.loop_start()
    except:
        status_text.value = "Sem Conexão"

    def mudar_rele(e):
        topic = e.control.data
        msg = "ON" if e.control.value else "OFF"
        mqttc.publish(topic, msg)

    # Interface Visual
    page.add(
        ft.Text("🏠 AUTOMAÇÃO", size=30, weight="bold"),
        ft.Row([status_led, status_text], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(),
        
        # Card Relé 1
        ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Row([
                    ft.Text("💡", size=30), # Emoji no lugar de ícone, tive problema com o uso de ícone na versão do flet do meu PC
                    ft.Text("Luz (D6)", size=20, expand=True),
                    ft.Switch(data="casa/rele1", on_change=mudar_rele),
                ])
            )
        ),

        # Card Relé 2
        ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Row([
                    ft.Text("🔌", size=30), # Emoji no lugar de ícone, o ícone deu problema na versão do flet no meu PC 
                    ft.Text("Tomada (D7)", size=20, expand=True),
                    ft.Switch(data="casa/rele2", on_change=mudar_rele),
                ])
            )
        ),
    )

if __name__ == "__main__":
    ft.app(target=main)