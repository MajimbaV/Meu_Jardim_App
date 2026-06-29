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

# Dicionário global básico (Mudado dias_agenda para list para evitar erros de conversão de set)
automacoes = {
    "D6": {"timer_minutos": 0, "hora_agenda": "18:00", "dias_agenda": []},
    "D7": {"timer_minutos": 0, "hora_agenda": "18:00", "dias_agenda": []}
}

def main(page: ft.Page):
    page.title = "Meu Jardim - Automação"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.window_height = 700
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # --- BARRA SUPERIOR ---
    page.appbar = ft.AppBar(
        title=ft.Text("🏡 AUTOMAÇÃO", size=22, weight=ft.FontWeight.BOLD),
        center_title=True,
        bgcolor=ft.Colors.SURFACE_VARIANT,
    )

    # --- STATUS DO BROKER ---
    status_led = ft.Container(width=12, height=12, bgcolor="red", border_radius=6)
    status_text = ft.Text("Desconectado", color="red", weight=ft.FontWeight.BOLD)

    # --- CLIENTE MQTT ---
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

    def mudar_rele(e):
        topic = e.control.data
        msg = "ON" if e.control.value else "OFF"
        try:
            mqttc.publish(topic, msg)
        except Exception as err:
            print(f"Erro MQTT: {err}")

    # --- PERSISTÊNCIA LOCAL SIMPLIFICADA ---
    def salvar_dados_no_disco():
        try:
            page.client_storage.set("config_automacoes", json.dumps(automacoes))
        except Exception as e:
            print(f"Erro ao salvar: {e}")

    # --- COMPONENTES VISUAIS DOS CORES/INPUTS ---
    txt_timer_d6 = ft.TextField(label="Minutos", value="30", width=90, text_align=ft.TextAlign.CENTER, dense=True)
    txt_hora_d6 = ft.TextField(label="HH:MM", value="18:00", width=90, text_align=ft.TextAlign.CENTER, dense=True)
    chips_d6 = {}

    txt_timer_d7 = ft.TextField(label="Minutos", value="30", width=90, text_align=ft.TextAlign.CENTER, dense=True)
    txt_hora_d7 = ft.TextField(label="HH:MM", value="18:00", width=90, text_align=ft.TextAlign.CENTER, dense=True)
    chips_d7 = {}

    def criar_bloco_automacao(pino_rele, txt_timer, txt_hora, chips_dict):
        def salvar_agenda(e):
            automacoes[pino_rele]["hora_agenda"] = txt_hora.value
            salvar_dados_no_disco()
            page.open(ft.SnackBar(ft.Text(f"Agenda de {pino_rele} salva!")))

        def alternar_dia_chip(e):
            dia = e.control.label.value
            if e.control.selected:
                if dia not in automacoes[pino_rele]["dias_agenda"]:
                    automacoes[pino_rele]["dias_agenda"].append(dia)
            else:
                if dia in automacoes[pino_rele]["dias_agenda"]:
                    automacoes[pino_rele]["dias_agenda"].remove(dia)
            salvar_dados_no_disco()

        dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        lista_chips = []
        
        for d in dias_semana:
            ch = ft.Chip(
                label=ft.Text(d), 
                selectable=True,
                selected=False,
                on_select=alternar_dia_chip
            )
            chips_dict[d] = ch
            lista_chips.append(ch)

        return ft.ExpansionTile(
            title=ft.Text("Configurar Temporizador e Agenda", size=13, color=ft.Colors.BLUE_200),
            maintain_state=True,
            controls=[
                ft.Container(
                    padding=10,
                    bgcolor=ft.Colors.BLACK26,
                    border_radius=8,
                    content=ft.Column([
                        # Linha do Timer (Corrigidos os parâmetros do IconButton)
                        ft.Row([
                            ft.Icon(ft.Icons.TIMER, color="amber"),
                            ft.Text("Desligar em:", weight=ft.FontWeight.W_500),
                            txt_timer,
                            ft.IconButton(icon=ft.Icons.PLAY_ARROW_ROUNDED, icon_color="green")
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        
                        ft.Divider(height=10, color="white10"),
                        
                        # Linha da Agenda (Corrigidos os parâmetros do IconButton)
                        ft.Row([
                            ft.Icon(ft.Icons.SCHEDULE, color="blue"),
                            ft.Text("Ligar às:", weight=ft.FontWeight.W_500),
                            txt_hora,
                            ft.IconButton(icon=ft.Icons.SAVE, icon_color="blue", on_click=salvar_agenda)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        
                        ft.Text("Dias da semana:", size=12, color="white60"),
                        ft.Row(lista_chips, wrap=True, alignment=ft.MainAxisAlignment.CENTER)
                    ], spacing=10)
                )
            ]
        )

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
                criar_bloco_automacao("D6", txt_timer_d6, txt_hora_d6, chips_d6)
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
                criar_bloco_automacao("D7", txt_timer_d7, txt_hora_d7, chips_d7)
            ])
        )
    )

    # --- ADICIONA TUDO NA TELA DIRETAMENTE ---
    page.add(
        ft.Container(height=10),
        ft.Row([status_led, status_text], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(),
        card_luz,
        card_tomada
    )
    page.update()

    # --- INICIALIZAÇÃO SECUNDÁRIA (BACKGROUND THREAD) ---
    def carregar_dados_e_conectar_mqtt():
        time.sleep(0.2)
        # Conexão MQTT
        try:
            mqttc.connect(MQTT_SERVER, MQTT_PORT, 60)
            mqttc.loop_start()
        except Exception:
            pass

        # Recuperação do storage local
        try:
            dados_salvos = page.client_storage.get("config_automacoes")
            if dados_salvos:
                dados_dict = json.loads(dados_salvos)
                
                # Sincroniza dados da Luz D6
                if "D6" in dados_dict:
                    automacoes["D6"]["hora_agenda"] = dados_dict["D6"].get("hora_agenda", "18:00")
                    automacoes["D6"]["timer_minutos"] = dados_dict["D6"].get("timer_minutos", 0)
                    automacoes["D6"]["dias_agenda"] = dados_dict["D6"].get("dias_agenda", [])
                    
                    txt_hora_d6.value = automacoes["D6"]["hora_agenda"]
                    if automacoes["D6"]["timer_minutos"] > 0:
                        txt_timer_d6.value = str(automacoes["D6"]["timer_minutos"])
                    for dia, chip_obj in chips_d6.items():
                        chip_obj.selected = dia in automacoes["D6"]["dias_agenda"]

                # Sincroniza dados da Tomada D7
                if "D7" in dados_dict:
                    automacoes["D7"]["hora_agenda"] = dados_dict["D7"].get("hora_agenda", "18:00")
                    automacoes["D7"]["timer_minutos"] = dados_dict["D7"].get("timer_minutos", 0)
                    automacoes["D7"]["dias_agenda"] = dados_dict["D7"].get("dias_agenda", [])
                    
                    txt_hora_d7.value = automacoes["D7"]["hora_agenda"]
                    if automacoes["D7"]["timer_minutos"] > 0:
                        txt_timer_d7.value = str(automacoes["D7"]["timer_minutos"])
                    for dia, chip_obj in chips_d7.items():
                        chip_obj.selected = dia in automacoes["D7"]["dias_agenda"]
                
                page.update()
        except Exception:
            pass

    # --- LOOP DO RELÓGIO DA AGENDA ---
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

    # Dispara as duas rotinas sem travar a interface
    threading.Thread(target=carregar_dados_e_conectar_mqtt, daemon=True).start()
    threading.Thread(target=loop_verificacao_horario, daemon=True).start()

ft.app(target=main)