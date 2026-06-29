import flet as ft
import paho.mqtt.client as mqtt
import random

# --- CONFIGURAÇÕES ---
MQTT_SERVER = "emqx.ifspb-czemnumeros.com.br"
MQTT_PORT = 1883
MQTT_USER = "esp12_01"
MQTT_PASS = "esp12_01"

def main(page: ft.Page):
    page.title = "Meu Jardim - Automação"
    page.theme_mode = ft.ThemeMode.DARK # Tema escuro
    page.window_width = 400
    page.window_height = 600
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Barra nativa do topo para evitar que os elementos fiquem cortados no Android 16
    page.appbar = ft.AppBar(
        title=ft.Text("🏡 AUTOMAÇÃO", size=22, weight=ft.FontWeight.BOLD),
        center_title=True,
        bgcolor=ft.colors.SURFACE_CONTAINER_HIGHEST, 
    )

    # Círculo de status feito com um Container customizado
    status_led = ft.Container(width=12, height=12, bgcolor="red", border_radius=6)
    status_text = ft.Text("Desconectado", color="red", weight=ft.FontWeight.W_500)

    # Configuração do Cliente MQTT
    client_id = f"Meu-Jardim-app-{random.randint(0, 999)}"
    
    try:
        mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
    except:
        mqttc = mqtt.Client(client_id=client_id)

    mqttc.username_pw_set(MQTT_USER, MQTT_PASS)

    # Função segura para atualizar a interface a partir de eventos externos (Thread-safe)
    def atualizar_status(texto, cor):
        status_text.value = texto
        status_text.color = cor
        status_led.bgcolor = cor
        page.update()

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            # Usando uma abordagem limpa para atualizar o Flet de fora da thread principal
            atualizar_status("Online", "green")
        else:
            atualizar_status(f"Erro {rc}", "red")

    mqttc.on_connect = on_connect

    try:
        mqttc.connect(MQTT_SERVER, MQTT_PORT)
        mqttc.loop_start()
    except:
        status_text.value = "Sem Conexão"

    def mudar_rele(e):
        topic = e.control.data
        msg = "ON" if e.control.value else "OFF"
        # Boa prática: publicar em background para a interface não travar caso o broker oscile
        try:
            mqttc.publish(topic, msg)
        except Exception as err:
            print(f"Erro ao publicar: {err}")

    # Interface Visual (Removido o título duplicado daqui de dentro)
    page.add(
        ft.Row(
            [status_led, status_text], 
            alignment=ft.MainAxisAlignment.CENTER,
            padding=ft.padding.only(top=15, bottom=10) # Um leve respiro abaixo da AppBar
        ),
        ft.Divider(),
        
        # Card Relé 1
        ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Row([
                    ft.Text("💡", size=30), 
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
                    ft.Text("🔌", size=30), 
                    ft.Text("Tomada (D7)", size=20, expand=True),
                    ft.Switch(data="casa/rele2", on_change=mudar_rele),
                ])
            )
        ),
    )

if __name__ == "__main__":
    ft.app(target=main)