import flet as ft
import paho.mqtt.client as mqtt
import random
import datetime
import threading
import time
import json

# --- CONFIGURAÇÕES MQTT ---
MQTT_SERVER = "emqx.ifspb-czemnumeros.com.br"
MQTT_PORT = 1883
MQTT_USER = "esp12_01"
MQTT_PASS = "esp12_01"

# Dicionário padrão na memória RAM
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

    # --- CARREGAR DADOS SALVOS DO DISCO DO CELULAR ---
    def carregar_dados_persistidos():
        try:
            dados_salvos = page.client_storage.get("config_automacoes")
            if dados_salvos:
                dados_dict = json.loads(dados_salvos)
                for pino in ["D6", "D7"]:
                    if pino in dados_dict:
                        automacoes[pino]["timer_minutos"] = dados_dict[pino].get("timer_minutos", 0)
                        automacoes[pino]["hora_agenda"] = dados_dict[pino].get("hora_agenda", "")
                        automacoes[pino]["dias_agenda"] = set(dados_dict[pino].get("dias_agenda", []))
        except Exception as e:
            print(f"Erro ao carregar dados locais: {e}")

    carregar_dados_persistidos()

    # --- FUNÇÃO PARA SALVAR NO DISCO DO CELULAR ---
    def salvar_dados_no_disco():
        try:
            # Convertemos o 'set' para 'list' para o JSON conseguir serializar
            dados_para_salvar = {
                "D6": {
                    "timer_minutos": automacoes["D6"]["timer_minutos"],
                    "hora_agenda": automacoes["D6"]["hora_agenda"],
                    "dias_agenda": list(automacoes["D6"]["dias_agenda"])
                },
                "D7": {
                    "timer_minutos": automacoes["D7"]["timer_minutos"],
                    "hora_agenda": automacoes["D7"]["hora_agenda"],
                    "dias_agenda": list(automacoes["D7"]["dias_agenda"])
                }
            }
            page.client_storage.set("config_automacoes", json.dumps(dados_para_salvar))
        except Exception as e:
            print(f"Erro ao persistir dados: {e}")

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

    # --- LÓGICA DE AGENDAMENTO (BACKGROUND THREAD) ---
    def loop_verificacao_horario():
        while True:
            agora = datetime.datetime.now()
            dias_map = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
            dia_atual_str = dias_map[agora.weekday()]
            hora_atual_str = agora.strftime("%H:%M")

            for pino, dados in automacoes.items():
                if dados["hora_agenda"] == hora_atual_str and dia_atual_str in dados["dias_agenda"]:
                    mqttc.publish(pino, "ON")
                    if pino == "D6":
                        switch_luz.value = True
                    if pino == "D7":
                        switch_tomada.value = True
                    page.update()

            time.sleep(60)

    # --- FUNÇÃO PARA CRIAR O CONTEINER EXPANSÍVEL DE AUTOMACÃO ---
    def criar_bloco_automacao(pino_rele):
        # Carrega os valores previamente salvos para preencher a interface visual
        v_hora = automacoes[pino_rele]["hora_agenda"] if automacoes[pino_rele]["hora_agenda"] else "18:00"
        v_timer = str(automacoes[pino_rele]["timer_minutos"]) if automacoes[pino_rele]["timer_minutos"] > 0 else "30"

        txt_timer = ft.TextField(label="Minutos", value=v_timer, width=90, text_align=ft.TextAlign.CENTER, dense=True)
        txt_hora = ft.TextField(label="HH:MM", value=v_hora, width=90, text_align=ft.TextAlign.CENTER, dense=True)
        
        def salvar_agenda(e):
            automacoes[pino_rele]["hora_agenda"] = txt_hora.value
            salvar_dados_no_disco() # Grava no armazenamento físico
            page.open(ft.SnackBar(ft.Text(f"Agenda de {pino_rele} salva para às {txt_hora.value}!")))

        def alternar_dia_chip(e):
            dia = e.control.label.value
            if e.control.selected:
                automacoes[pino_rele]["dias_agenda"].add(dia)
            else:
                automacoes[pino_rele]["dias_agenda"].discard(dia)
            salvar_dados_no_disco() # Atualiza os dias selecionados no disco

        dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        
        # Reconstrói a linha de chips marcando como 'selected' os dias que já estavam salvos
        linha_dias = ft.Row(
            [
                ft.Chip(
                    label=ft.Text(d), 
                    selectable=True,
                    selected=d in automacoes[pino_rele]["dias_agenda"],
                    on_select=alternar_dia_chip
                ) for d in dias_semana
            ],
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
                        # Estrutura do Timer
                        ft.Row([
                            ft.Icon(ft.Icons.TIMER, color="amber"),
                            ft.Text("Desligar em:", weight=ft.FontWeight.W_500),
                            txt_timer,
                            ft.IconButton(ft.Icons.PLAY_ARROW_ROUNDED, icon_color="green", tooltip="Iniciar Timer")
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        
                        ft.Divider(height=10, color="white10"),
                        
                        # Estrutura da Agenda
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

    # --- COMPONENTES DOS CARDS PRINCIPAIS ---
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

    # --- MONTAGEM DA INTERFACE NA TELA ---
    page.add(
        ft.Container(height=10),
        ft.Row([status_led, status_text], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(),
        card_luz,
        card_tomada
    )

    page.update()

    # Dispara o loop de checagem em paralelo
    t = threading.Thread(target=loop_verificacao_horario, daemon=True)
    t.start()

ft.app(target=main)