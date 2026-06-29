import flet as ft
import paho.mqtt.client as mqtt
import random
import datetime
import asyncio

# --- CONFIGURAÇÕES MQTT ---
MQTT_SERVER = "emqx.ifspb-czemnumeros.com.br"
MQTT_PORT = 1883
MQTT_USER = "esp12_01"
MQTT_PASS = "esp12_01"

# Dicionário global para guardar as configurações de agendamento de cada relé
automacoes = {
    "D6": {"timer_minutos": 0, "hora_agenda": "", "dias_agenda": set()},
    "D7": {"timer_minutos": 0, "hora_agenda": "", "dias_agenda": set()}
}

def main(page: ft.Page):
    page.title = "Meu Jardim - Automação"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.window_height = 700
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # --- BARRA NATIVA SUPERIOR ---
    page.appbar = ft.AppBar(
        title=ft.Text("🏡 AUTOMAÇÃO", size=22, weight=ft.FontWeight.BOLD),
        center_title=True,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
    )

    # --- STATUS DO BROKER ---
    status_led = ft.Container(width=12, height=12, bgcolor="red", border_radius=6)
    status_text = ft.Text("Desconectado", color="red", weight=ft.FontWeight.BOLD)

    # --- CONFIGURAÇÃO CLIENTE MQTT ---
    client_id = f'flet-mqtt-{random.randint(0, 1000)}'
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
    mqttc.username_pw_set(MQTT_USER, MQTT_PASS)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            status_led.bgcolor = "green"
            status_text.value = "Online"
            status_text.color = "green"
        else:
            status_led.bgcolor = "red"
            status_text.value = f"Erro {rc}"
            status_text.color = "red"
        page.update()

    mqttc.on_connect = on_connect

    try:
        mqttc.connect(MQTT_SERVER, MQTT_PORT, 60)
        mqttc.loop_start()
    except Exception:
        status_text.value = "Sem Conexão"

    def mudar_rele(e):
        topic = e.control.data
        msg = "ON" if e.control.value else "OFF"
        try:
            mqttc.publish(topic, msg)
        except Exception as err:
            print(f"Erro ao publicar: {err}")

    # --- LÓGICA DE AGENDAMENTO (BACKGROUND TASK) ---
    async def loop_verificacao_horario():
        while True:
            agora = datetime.datetime.now()
            # 0=Segunda, 1=Terça... 6=Domingo (Ajustando string para bater com os Chips)
            dias_map = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
            dia_atual_str = dias_map[agora.weekday()]
            hora_atual_str = agora.strftime("%H:%M")

            for pino, dados in automacoes.items():
                # 1. Checagem da Agenda Semanal
                if dados["hora_agenda"] == hora_atual_str and dia_atual_str in dados["dias_agenda"]:
                    # Se coincidir o dia e a hora exacta, envia comando para ligar
                    mqttc.publish(pino, "ON")
                    # Atualiza o Switch na tela se o app estiver aberto
                    if pino == "D6": switch_luz.value = True
                    if pino == "D7": switch_tomada.value = True
                    page.update()

            # Aguarda 60 segundos para checar o próximo minuto de forma assíncrona
            await asyncio.sleep(60)

    # --- FUNÇÃO PARA CRIAR O BLOCO DE AUTOMACÃO (CONTEINER EXPANSÍVEL) ---
    def criar_bloco_automacao(pino_rele):
        txt_timer = ft.TextField(label="Minutos", value="30", width=90, text_align=ft.TextAlign.CENTER, dense=True)
        txt_hora = ft.TextField(label="HH:MM", value="18:00", width=90, text_align=ft.TextAlign.CENTER, dense=True)
        
        def salvar_agenda(e):
            automacoes[pino_rele]["hora_agenda"] = txt_hora.value
            page.open(ft.SnackBar(ft.Text(f"Agenda de {pino_rele} salva para às {txt_hora.value}!")))

        def alternar_dia_chip(e):
            dia = e.control.label.value
            if e.control.selected:
                automacoes[pino_rele]["dias_agenda"].add(dia)
            else:
                automacoes[pino_rele]["dias_agenda"].discard(dia)

        dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        linha_dias = ft.Row(
            [ft.FilterChip(label=ft.Text(d), on_select=alternar_dia_chip) for d in dias_semana],
            wrap=True,
            alignment=ft.MainAxisAlignment.CENTER
        )

        return ft.ExpansionTile(
            title=ft.Text("Configurar Temporizador e Agenda", size=13, color=ft.Colors.BLUE_200),
            maintain_state=True,
            controls=[
                ft.Container(
                    padding=10,
                    bgcolor=ft.Colors.BLACK26,
                    border_radius=8,
                    content=ft.Column([
                        # Seção Timer
                        ft.Row([
                            ft.Icon(ft.Icons.TIMER, color="amber"),
                            ft.Text("Desligar em:", weight=ft.FontWeight.W_500),
                            txt_timer,
                            ft.IconButton(ft.Icons.PLAY_ARROW_ROUNDED, icon_color="green", tooltip="Iniciar Timer")
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        
                        ft.Divider(height=10, color="white10"),
                        
                        # Seção Agenda
                        ft.Row([
                            ft.Icon(ft.Icons.SCHEDULE, color="blue"),
                            ft.Text("Ligar às:", weight=ft.FontWeight.W_500),
                            txt_hora,
                            ft.IconButton(ft.Icons.SAVE, icon_color="blue", on_click=salvar_agenda, tooltip="Salvar Horário")
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Text("Dias da semana:", size=12, color="white60"),
                        linha_dias
                    ], spacing=10)
                )
            ]
        )

    # --- COMPONENTES DOS CARD PRINCIPAIS ---
    switch_luz = ft.Switch(value=False, data="D6", on_change=mudar_rele)
    switch_tomada = ft.Switch(value=False, data="D7", on_change=mudar_rele)

    card_luz = ft.Card(
        content=ft.Container(
            padding=12,
            content=ft.Column([
                ft.Row([
                    ft.Row([ft.Icon(ft.Icons.LIGHTBULB, color="amber", size=28), ft.Text("Luz (D6)", size=18, weight=ft.FontWeight.W_500)]),
                    switch_luz
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                criar_bloco_automacao("D6")
            ])
        )
    )

    card_tomada = ft.Card(
        content=ft.Container(
            padding=12,
            content=ft.Column([
                ft.Row([
                    ft.Row([ft.Icon(ft.Icons.POWER, color="blue_grey_200", size=28), ft.Text("Tomada (D7)", size=18, weight=ft.FontWeight.W_500)]),
                    switch_tomada
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                criar_bloco_automacao("D7")
            ])
        )
    )

    # --- MONTAGEM DA INTERFACE ---
    page.add(
        ft.Container(height=10),
        ft.Row([status_led, status_text], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(),
        card_luz,
        card_tomada
    )

    # Inicializa a tarefa paralela em background para checar os horários
    asyncio.run(loop_verificacao_horario())

ft.app(target=main)