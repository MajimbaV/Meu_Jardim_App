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

# Dicionário global para controlar o estado das automações
automacoes = {
    "D6": {"timer_minutos": 0, "hora_agenda": "18:00", "dias_agenda": set(), "timer_objeto": None},
    "D7": {"timer_minutos": 0, "hora_agenda": "18:00", "dias_agenda": set(), "timer_objeto": None}
}

def main(page: ft.Page):
    page.title = "Meu Jardim - Automação"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.window_height = 700
    page.horizontal_alignment = "center"

    # --- BARRA SUPERIOR ---
    page.appbar = ft.AppBar(
        title=ft.Text("🏡 AUTOMAÇÃO", size=22, weight="bold"),
        center_title=True,
        bgcolor="surface",
    )

    # --- STATUS DO BROKER ---
    status_led = ft.Container(width=12, height=12, bgcolor="red", border_radius=6)
    status_text = ft.Text("Desconectado", color="red", weight="bold")

    # --- CLIENTE MQTT ---
    client_id = f'flet-mqtt-{random.randint(0, 1000)}'
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.V1, client_id=client_id)
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

    # --- FUNÇÃO ATUADORA (MUDAR RELE) ---
    def mudar_rele(e):
        topic = e.control.data
        msg = "ON" if e.control.value else "OFF"
        
        if msg == "OFF" and automacoes[topic]["timer_objeto"] is not None:
            try:
                automacoes[topic]["timer_objeto"].cancel()
                automacoes[topic]["timer_objeto"] = None
            except Exception:
                pass

        try:
            mqttc.publish(topic, msg)
        except Exception as err:
            print(f"Erro MQTT: {err}")

    # --- PERSISTÊNCIA LOCAL ---
    def salvar_dados_no_disco():
        try:
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
            print(f"Erro ao salvar: {e}")

    # --- LÓGICA DO TEMPORIZADOR (TIMER) ---
    def desligar_por_timeout(pino_rele, switch_componente):
        try:
            mqttc.publish(pino_rele, "OFF")
            switch_componente.value = False
            automacoes[pino_rele]["timer_objeto"] = None
            page.update()
        except Exception as e:
            print(f"Erro no timeout do timer: {e}")

    def acionar_temporizador(pino_rele, txt_timer, switch_componente):
        try:
            minutos = int(txt_timer.value)
        except ValueError:
            page.open(ft.SnackBar(ft.Text("Insira um número válido de minutos!")))
            return

        if minutos <= 0:
            page.open(ft.SnackBar(ft.Text("O tempo deve ser maior que zero!")))
            return

        if automacoes[pino_rele]["timer_objeto"] is not None:
            automacoes[pino_rele]["timer_objeto"].cancel()

        mqttc.publish(pino_rele, "ON")
        switch_componente.value = True
        page.update()

        segundos = minutos * 60
        t = threading.Timer(segundos, desligar_por_timeout, args=[pino_rele, switch_componente])
        automacoes[pino_rele]["timer_objeto"] = t
        automacoes[pino_rele]["timer_minutos"] = minutos
        t.start()
        
        salvar_dados_no_disco()
        page.open(ft.SnackBar(ft.Text(f"{pino_rele} ligado! Vai desligar em {minutos} min.")))

    # --- INPUTS VISUAIS ---
    txt_timer_d6 = ft.TextField(label="Minutos", value="30", width=90, text_align="center", dense=True)
    txt_hora_d6 = ft.TextField(label="HH:MM", value="18:00", width=90, text_align="center", dense=True)
    buttons_d6 = {}

    txt_timer_d7 = ft.TextField(label="Minutos", value="30", width=90, text_align="center", dense=True)
    txt_hora_d7 = ft.TextField(label="HH:MM", value="18:00", width=90, text_align="center", dense=True)
    buttons_d7 = {}

    switch_luz = ft.Switch(value=False, data="D6", on_change=mudar_rele)
    switch_tomada = ft.Switch(value=False, data="D7", on_change=mudar_rele)

    # --- CONSTRUTOR DE BLOCOS ---
    def criar_bloco_automacao(pino_rele, txt_timer, txt_hora, buttons_dict, switch_componente):
        def salvar_agenda(e):
            automacoes[pino_rele]["hora_agenda"] = txt_hora.value
            salvar_dados_no_disco()
            page.open(ft.SnackBar(ft.Text(f"Agenda de {pino_rele} salva para as {txt_hora.value}!")))

        def alternar_dia_btn(e):
            # Como usamos GestureDetector, o controle clicado é o Container interno (content)
            container_alvo = e.control.content
            dia = container_alvo.data
            
            if dia in automacoes[pino_rele]["dias_agenda"]:
                automacoes[pino_rele]["dias_agenda"].discard(dia)
                container_alvo.bgcolor = "transparent"
                container_alvo.border = ft.border.all(1, "white30")
            else:
                automacoes[pino_rele]["dias_agenda"].add(dia)
                container_alvo.bgcolor = "blue"
                container_alvo.border = ft.border.all(1, "blue")
            
            salvar_dados_no_disco()
            page.update()

        dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        lista_botoes = []
        
        for d in dias_semana:
            # Criando chips customizados usando Containers puros dentro de um detector de cliques
            container_chip = ft.Container(
                content=ft.Text(d, size=11, weight="bold", color="white"),
                alignment=ft.alignment.CENTER,
                padding=8,
                width=45,
                height=32,
                border_radius=6,
                border=ft.border.all(1, "white30"),
                bgcolor="transparent",
                data=d # Guarda o dia da semana aqui
            )
            
            detector_clique = ft.GestureDetector(
                content=container_chip,
                on_tap=alternar_dia_btn
            )
            
            # Mapeamos o container para conseguir alterar sua cor depois via persistência de dados
            buttons_dict[d] = container_chip
            lista_botoes.append(detector_clique)

        return ft.ExpansionTile(
            title=ft.Text("Configurar Temporizador e Agenda", size=13, color="blue200"),
            maintain_state=True,
            controls=[
                ft.Container(
                    padding=10,
                    bgcolor="black26",
                    border_radius=8,
                    content=ft.Column([
                        # Linha do Temporizador
                        ft.Row([
                            ft.Icon(ft.Icons.TIMER, color="amber"),
                            ft.Text("Desligar em:", weight="w500"),
                            txt_timer,
                            ft.IconButton(
                                icon=ft.Icons.PLAY_ARROW_ROUNDED, 
                                icon_color="green",
                                on_click=lambda e: acionar_temporizador(pino_rele, txt_timer, switch_componente)
                            )
                        ], alignment="spaceBetween"),
                        
                        ft.Divider(height=10, color="white10"),
                        
                        # Linha da Agenda
                        ft.Row([
                            ft.Icon(ft.Icons.SCHEDULE, color="blue"),
                            ft.Text("Ligar às:", weight="w500"),
                            txt_hora,
                            ft.IconButton(icon=ft.Icons.SAVE, icon_color="blue", on_click=salvar_agenda)
                        ], alignment="spaceBetween"),
                        
                        ft.Text("Dias da semana:", size=12, color="white60"),
                        ft.Row(lista_botoes, wrap=True, alignment="center", spacing=5)
                    ], spacing=10)
                )
            ]
        )

    # --- MONTAGEM DOS CARDS ---
    card_luz = ft.Card(
        content=ft.Container(
            padding=12,
            content=ft.Column([
                ft.Row([
                    ft.Row([ft.Icon(ft.Icons.LIGHTBULB, color="amber", size=28), ft.Text("Luz (D6)", size=18, weight="w500")]),
                    switch_luz
                ], alignment="spaceBetween"),
                criar_bloco_automacao("D6", txt_timer_d6, txt_hora_d6, buttons_d6, switch_luz)
            ])
        )
    )

    card_tomada = ft.Card(
        content=ft.Container(
            padding=12,
            content=ft.Column([
                ft.Row([
                    ft.Row([ft.Icon(ft.Icons.POWER, color="blueGrey200", size=28), ft.Text("Tomada (D7)", size=18, weight="w500")]),
                    switch_tomada
                ], alignment="spaceBetween"),
                criar_bloco_automacao("D7", txt_timer_d7, txt_hora_d7, buttons_d7, switch_tomada)
            ])
        )
    )

    # --- RENDERIZAÇÃO DA INTERFACE ---
    page.add(
        ft.Container(height=15),
        ft.Row([status_led, status_text], alignment="center"),
        ft.Divider(),
        card_luz,
        card_tomada
    )
    page.update()

    # --- PROCESSAMENTO ASSÍNCRONO EM BACKGROUND THREAD ---
    def carregar_dados_e_conectar_mqtt():
        time.sleep(0.2)
        try:
            mqttc.connect(MQTT_SERVER, MQTT_PORT, 60)
            mqttc.loop_start()
        except Exception:
            pass

        try:
            dados_salvos = page.client_storage.get("config_automacoes")
            if dados_salvos:
                dados_dict = json.loads(dados_salvos)
                
                for pino, txt_hora_comp, txt_timer_comp, btns_dict in [("D6", txt_hora_d6, txt_timer_d6, buttons_d6), ("D7", txt_hora_d7, txt_timer_d7, buttons_d7)]:
                    if pino in dados_dict:
                        automacoes[pino]["hora_agenda"] = dados_dict[pino].get("hora_agenda", "18:00")
                        automacoes[pino]["timer_minutos"] = dados_dict[pino].get("timer_minutos", 0)
                        automacoes[pino]["dias_agenda"] = set(dados_dict[pino].get("dias_agenda", []))
                        
                        txt_hora_comp.value = automacoes[pino]["hora_agenda"]
                        if automacoes[pino]["timer_minutos"] > 0:
                            txt_timer_comp.value = str(automacoes[pino]["timer_minutos"])
                        
                        # Restaura o estado visual dos containers customizados
                        for dia, container_obj in btns_dict.items():
                            if dia in automacoes[pino]["dias_agenda"]:
                                container_obj.bgcolor = "blue"
                                container_obj.border = ft.border.all(1, "blue")
                            else:
                                container_obj.bgcolor = "transparent"
                                container_obj.border = ft.border.all(1, "white30")
                
                page.update()
        except Exception as e:
            print(f"Erro ao recuperar dados: {e}")

    # --- ENGINE DE AGENDAMENTO SEMANAL ---
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

    threading.Thread(target=carregar_dados_e_conectar_mqtt, daemon=True).start()
    threading.Thread(target=loop_verificacao_horario, daemon=True).start()

ft.app(main)