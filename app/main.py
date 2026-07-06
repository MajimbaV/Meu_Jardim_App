import flet as ft
import paho.mqtt.client as mqtt
import random
import datetime
import threading
import time
import json
import os
import tempfile  # Garante um diretório com permissão de escrita em qualquer SO

# --- CONFIGURAÇÕES MQTT ---
MQTT_SERVER = "emqx.ifspb-czemnumeros.com.br"
MQTT_PORT = 1883
MQTT_USER = "esp12_01"
MQTT_PASS = "esp12_01"

# Dicionário global para controlar o estado das automações
automacoes = {
    "casa/rele1": {"timer_minutos": 0, "hora_agenda": "18:00", "dias_agenda": set(), "timer_objeto": None},
    "casa/rele2": {"timer_minutos": 0, "hora_agenda": "18:00", "dias_agenda": set(), "timer_objeto": None}
}

# --- DEFINIÇÃO DO CAMINHO COMPATÍVEL MULTIPLATAFORMA ---
# tempfile.gettempdir() aponta para uma pasta com permissões totais tanto no PC quanto no Android/iOS
CONFIG_FILE = os.path.join(tempfile.gettempdir(), "config_automacoes_jardim.json")
print(f"DEBUG: Caminho seguro utilizado = {CONFIG_FILE}")

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
    mqttc = mqtt.Client(client_id=client_id)
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
                "casa/rele1": {
                    "timer_minutos": automacoes["casa/rele1"]["timer_minutos"],
                    "hora_agenda": automacoes["casa/rele1"]["hora_agenda"],
                    "dias_agenda": list(automacoes["casa/rele1"]["dias_agenda"])
                },
                "casa/rele2": {
                    "timer_minutos": automacoes["casa/rele2"]["timer_minutos"],
                    "hora_agenda": automacoes["casa/rele2"]["hora_agenda"],
                    "dias_agenda": list(automacoes["casa/rele2"]["dias_agenda"])
                }
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(dados_para_salvar, f)
            print("DEBUG: Dados guardados em segurança!")
        except Exception as e:
            print(f"Erro ao salvar dados: {e}")

    # --- LÓGICA DO TEMPORIZADOR (TIMER) ---
    def desligar_por_timeout(pino_rele, switch_componente):
        try:
            mqttc.publish(pino_rele, "OFF")
            switch_componente.value = False
            automacoes[pino_rele]["timer_objeto"] = None
            automacoes[pino_rele]["timer_minutos"] = 0
            
            switch_componente.page.snack_bar = ft.SnackBar(ft.Text(f"⏰ {pino_rele} desligado! Tempo terminou."))
            switch_componente.page.snack_bar.open = True
            switch_componente.page.update()
        except Exception as e:
            print(f"Erro no timeout do timer: {e}")

    def acionar_temporizador(pino_rele, txt_timer, switch_componente):
        try:
            minutos = int(txt_timer.value)
        except ValueError:
            switch_componente.page.snack_bar = ft.SnackBar(ft.Text("Insira um número válido de minutos!"))
            switch_componente.page.snack_bar.open = True
            switch_componente.page.update()
            return

        if minutos <= 0:
            switch_componente.page.snack_bar = ft.SnackBar(ft.Text("O tempo deve ser maior que zero!"))
            switch_componente.page.snack_bar.open = True
            switch_componente.page.update()
            return

        if automacoes[pino_rele]["timer_objeto"] is not None:
            automacoes[pino_rele]["timer_objeto"].cancel()

        mqttc.publish(pino_rele, "ON")
        switch_componente.value = True
        
        switch_componente.page.snack_bar = ft.SnackBar(ft.Text(f"⏱️ Temporizador iniciado por {minutos} minuto(s)"))
        switch_componente.page.snack_bar.open = True
        switch_componente.page.update()

        segundos = minutos * 60
        t = threading.Timer(segundos, desligar_por_timeout, args=[pino_rele, switch_componente])
        automacoes[pino_rele]["timer_objeto"] = t
        automacoes[pino_rele]["timer_minutos"] = minutos
        t.start()
        
        salvar_dados_no_disco()

    # --- INPUTS VISUAIS ---
    txt_timer_d6 = ft.TextField(label="Minutos", value="30", width=90, text_align="center", dense=True)
    txt_hora_d6 = ft.TextField(label="HH:MM", value="18:00", width=90, text_align="center", dense=True)
    buttons_d6 = {}

    txt_timer_d7 = ft.TextField(label="Minutos", value="30", width=90, text_align="center", dense=True)
    txt_hora_d7 = ft.TextField(label="HH:MM", value="18:00", width=90, text_align="center", dense=True)
    buttons_d7 = {}

    switch_luz = ft.Switch(value=False, data="casa/rele1", on_change=mudar_rele)
    switch_tomada = ft.Switch(value=False, data="casa/rele2", on_change=mudar_rele)

    # --- CARREGA DADOS DO ARQUIVO ANTES DE CRIAR INTERFACE ---
    def carregar_dados_local():
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    dados_dict = json.load(f)
                    print(f"DEBUG: Dados carregados: {dados_dict}")
                    
                for pino in ["casa/rele1", "casa/rele2"]:
                    if pino in dados_dict:
                        automacoes[pino]["hora_agenda"] = dados_dict[pino].get("hora_agenda", "18:00")
                        automacoes[pino]["timer_minutos"] = dados_dict[pino].get("timer_minutos", 0)
                        dias_carregados = dados_dict[pino].get("dias_agenda", [])
                        automacoes[pino]["dias_agenda"] = set(dias_carregados)
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
    
    carregar_dados_local()

# --- CONSTRUTOR DE BLOCOS ---
# --- CONSTRUTOR DE BLOCOS ---
def criar_bloco_automacao(pino_rele, txt_timer, txt_hora, buttons_dict, switch_componente):
    def salvar_agenda(e):
        automacoes[pino_rele]["hora_agenda"] = txt_hora.value
        salvar_dados_no_disco()
        switch_componente.page.snack_bar = ft.SnackBar(ft.Text(f"Agenda de {pino_rele} salva para as {txt_hora.value}!"))
        switch_componente.page.snack_bar.open = True
        switch_componente.page.update()

    def alternar_dia_btn(e):
        container_alvo = e.control.content
        dia = container_alvo.data
        texto_alvo = container_alvo.content

        if dia in automacoes[pino_rele]["dias_agenda"]:
            automacoes[pino_rele]["dias_agenda"].discard(dia)
            container_alvo.bgcolor = "transparent"
            container_alvo.border = ft.Border(
                ft.BorderSide(1, "white30"), ft.BorderSide(1, "white30"),
                ft.BorderSide(1, "white30"), ft.BorderSide(1, "white30")
            )
            texto_alvo.color = "white"
        else:
            automacoes[pino_rele]["dias_agenda"].add(dia)
            container_alvo.bgcolor = "blue"
            container_alvo.border = ft.Border(
                ft.BorderSide(1, "blue"), ft.BorderSide(1, "blue"),
                ft.BorderSide(1, "blue"), ft.BorderSide(1, "blue")
            )
            texto_alvo.color = "white"

        salvar_dados_no_disco()
        switch_componente.page.update()

    dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    lista_botoes = []

    for d in dias_semana:
        esta_selecionado = d in automacoes[pino_rele]["dias_agenda"]
        bgcolor = "blue" if esta_selecionado else "transparent"
        cor_borda = "blue" if esta_selecionado else "white30"

        container_chip = ft.Container(
            content=ft.Text(d, size=11, weight="bold", color="white"),
            alignment="center",
            padding=8,
            width=45,
            height=32,
            border_radius=6,
            border=ft.Border(
                ft.BorderSide(1, cor_borda), ft.BorderSide(1, cor_borda),
                ft.BorderSide(1, cor_borda), ft.BorderSide(1, cor_borda)
            ),
            bgcolor=bgcolor,
            data=d
        )

        detector_clique = ft.GestureDetector(
            content=container_chip,
            on_tap=alternar_dia_btn
        )

        buttons_dict[d] = container_chip
        lista_botoes.append(detector_clique)

    txt_hora.value = automacoes[pino_rele]["hora_agenda"]
    if automacoes[pino_rele]["timer_minutos"] > 0:
        txt_timer.value = str(automacoes[pino_rele]["timer_minutos"])

    return ft.ExpansionTile(
        title=ft.Text("Configurar Temporizador e Agenda", size=13, color="blue200"),
        maintain_state=True,
        controls=[
            ft.Container(
                padding=10,
                bgcolor="white10",  # Opacidade branca leve e segura sobre o fundo escuro do app
                border_radius=8,
                content=ft.Column([
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
                    
                    ft.Row([
                        ft.Icon(ft.Icons.SCHEDULE, color="blue"),
                        ft.Text("Ligar às:", weight="w500"),
                        txt_hora,
                        ft.IconButton(icon=ft.Icons.SAVE, icon_color="blue", on_click=salvar_agenda)
                    ], alignment="spaceBetween"),
                    
                    ft.Text("Dias da semana:", size=12, color="white60"),
                    ft.Row(lista_botoes, wrap=True, alignment="center", spacing=5) # Removido container com bug de tamanho fixo
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
                criar_bloco_automacao("casa/rele1", txt_timer_d6, txt_hora_d6, buttons_d6, switch_luz)
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
                criar_bloco_automacao("casa/rele2", txt_timer_d7, txt_hora_d7, buttons_d7, switch_tomada)
            ])
        )
    )

    # --- RENDERIZAÇÃO DA INTERFACE ---
    # Colocamos tudo dentro de uma Column com scroll para nunca quebrar no Android
    conteudo_principal = ft.Column(
        controls=[
            ft.Container(height=15),
            ft.Row([status_led, status_text], alignment="center"),
            ft.Divider(),
            card_luz,
            card_tomada
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )
    
    page.add(conteudo_principal)
    page.update()


    # --- PROCESSAMENTO ASSÍNCRONO EM BACKGROUND THREAD ---
    def conectar_mqtt_e_agendar():
        try:
            mqttc.connect(MQTT_SERVER, MQTT_PORT, 60)
            mqttc.loop_start()
        except Exception:
            pass

    def loop_verificacao_horario():
        while True:
            agora = datetime.datetime.now()
            dias_map = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
            dia_atual_str = dias_map[agora.weekday()]
            hora_atual_str = agora.strftime("%H:%M")

            for pino, dados in automacoes.items():
                if dados["hora_agenda"] == hora_atual_str and dia_atual_str in dados["dias_agenda"]:
                    mqttc.publish(pino, "ON")
                    if pino == "casa/rele1":
                        switch_luz.value = True
                    if pino == "casa/rele2":
                        switch_tomada.value = True
                    page.update()
import flet as ft
import paho.mqtt.client as mqtt
import random
import datetime
import threading
import time
import json
import os
import tempfile  # Garante um diretório com permissão de escrita em qualquer SO

# --- CONFIGURAÇÕES MQTT ---
MQTT_SERVER = "emqx.ifspb-czemnumeros.com.br"
MQTT_PORT = 1883
MQTT_USER = "esp12_01"
MQTT_PASS = "esp12_01"

# Dicionário global para controlar o estado das automações
automacoes = {
    "casa/rele1": {"timer_minutos": 0, "hora_agenda": "18:00", "dias_agenda": set(), "timer_objeto": None},
    "casa/rele2": {"timer_minutos": 0, "hora_agenda": "18:00", "dias_agenda": set(), "timer_objeto": None}
}

# --- DEFINIÇÃO DO CAMINHO COMPATÍVEL MULTIPLATAFORMA ---
# tempfile.gettempdir() aponta para uma pasta com permissões totais tanto no PC quanto no Android/iOS
CONFIG_FILE = os.path.join(tempfile.gettempdir(), "config_automacoes_jardim.json")
print(f"DEBUG: Caminho seguro utilizado = {CONFIG_FILE}")

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
    mqttc = mqtt.Client(client_id=client_id)
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
                "casa/rele1": {
                    "timer_minutos": automacoes["casa/rele1"]["timer_minutos"],
                    "hora_agenda": automacoes["casa/rele1"]["hora_agenda"],
                    "dias_agenda": list(automacoes["casa/rele1"]["dias_agenda"])
                },
                "casa/rele2": {
                    "timer_minutos": automacoes["casa/rele2"]["timer_minutos"],
                    "hora_agenda": automacoes["casa/rele2"]["hora_agenda"],
                    "dias_agenda": list(automacoes["casa/rele2"]["dias_agenda"])
                }
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(dados_para_salvar, f)
            print("DEBUG: Dados guardados em segurança!")
        except Exception as e:
            print(f"Erro ao salvar dados: {e}")

    # --- LÓGICA DO TEMPORIZADOR (TIMER) ---
    def desligar_por_timeout(pino_rele, switch_componente):
        try:
            mqttc.publish(pino_rele, "OFF")
            switch_componente.value = False
            automacoes[pino_rele]["timer_objeto"] = None
            automacoes[pino_rele]["timer_minutos"] = 0
            
            page.snack_bar = ft.SnackBar(ft.Text(f"⏰ {pino_rele} desligado! Tempo terminou."))
            page.snack_bar.open = True
            page.update()
        except Exception as e:
            print(f"Erro no timeout do timer: {e}")

    def acionar_temporizador(pino_rele, txt_timer, switch_componente):
        try:
            minutos = int(txt_timer.value)
        except ValueError:
            page.snack_bar = ft.SnackBar(ft.Text("Insira um número válido de minutos!"))
            page.snack_bar.open = True
            page.update()
            return

        if minutos <= 0:
            page.snack_bar = ft.SnackBar(ft.Text("O tempo deve ser maior que zero!"))
            page.snack_bar.open = True
            page.update()
            return

        if automacoes[pino_rele]["timer_objeto"] is not None:
            automacoes[pino_rele]["timer_objeto"].cancel()

        mqttc.publish(pino_rele, "ON")
        switch_componente.value = True
        
        page.snack_bar = ft.SnackBar(ft.Text(f"⏱️ Temporizador iniciado por {minutos} minuto(s)"))
        page.snack_bar.open = True
        page.update()

        segundos = minutos * 60
        t = threading.Timer(segundos, desligar_por_timeout, args=[pino_rele, switch_componente])
        automacoes[pino_rele]["timer_objeto"] = t
        automacoes[pino_rele]["timer_minutos"] = minutos
        t.start()
        
        salvar_dados_no_disco()

    # --- INPUTS VISUAIS ---
    txt_timer_d6 = ft.TextField(label="Minutos", value="30", width=90, text_align="center", dense=True)
    txt_hora_d6 = ft.TextField(label="HH:MM", value="18:00", width=90, text_align="center", dense=True)
    buttons_d6 = {}

    txt_timer_d7 = ft.TextField(label="Minutos", value="30", width=90, text_align="center", dense=True)
    txt_hora_d7 = ft.TextField(label="HH:MM", value="18:00", width=90, text_align="center", dense=True)
    buttons_d7 = {}

    switch_luz = ft.Switch(value=False, data="casa/rele1", on_change=mudar_rele)
    switch_tomada = ft.Switch(value=False, data="casa/rele2", on_change=mudar_rele)

    # --- CARREGA DADOS DO ARQUIVO ANTES DE CRIAR INTERFACE ---
    def carregar_dados_local():
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    dados_dict = json.load(f)
                    print(f"DEBUG: Dados carregados: {dados_dict}")
                    
                for pino in ["casa/rele1", "casa/rele2"]:
                    if pino in dados_dict:
                        automacoes[pino]["hora_agenda"] = dados_dict[pino].get("hora_agenda", "18:00")
                        automacoes[pino]["timer_minutos"] = dados_dict[pino].get("timer_minutos", 0)
                        dias_carregados = dados_dict[pino].get("dias_agenda", [])
                        automacoes[pino]["dias_agenda"] = set(dias_carregados)
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
    
    carregar_dados_local()

    # --- CONSTRUTOR DE BLOCOS ---
    def criar_bloco_automacao(pino_rele, txt_timer, txt_hora, buttons_dict, switch_componente):
        def salvar_agenda(e):
            automacoes[pino_rele]["hora_agenda"] = txt_hora.value
            salvar_dados_no_disco()
            page.snack_bar = ft.SnackBar(ft.Text(f"Agenda de {pino_rele} salva para as {txt_hora.value}!"))
            page.snack_bar.open = True
            page.update()

        def alternar_dia_btn(e):
            container_alvo = e.control.content
            dia = container_alvo.data
            
            if dia in automacoes[pino_rele]["dias_agenda"]:
                automacoes[pino_rele]["dias_agenda"].discard(dia)
                container_alvo.bgcolor = "transparent"
                container_alvo.border = ft.Border(
                    ft.BorderSide(1, "white30"), ft.BorderSide(1, "white30"),
                    ft.BorderSide(1, "white30"), ft.BorderSide(1, "white30")
                )
            else:
                automacoes[pino_rele]["dias_agenda"].add(dia)
                container_alvo.bgcolor = "blue"
                container_alvo.border = ft.Border(
                    ft.BorderSide(1, "blue"), ft.BorderSide(1, "blue"),
                    ft.BorderSide(1, "blue"), ft.BorderSide(1, "blue")
                )
            
            salvar_dados_no_disco()
            page.update()

        dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        lista_botoes = []
        
        for d in dias_semana:
            esta_selecionado = d in automacoes[pino_rele]["dias_agenda"]
            bgcolor = "blue" if esta_selecionado else "transparent"
            cor_borda = "blue" if esta_selecionado else "white30"
            
            container_chip = ft.Container(
                content=ft.Text(d, size=11, weight="bold", color="white"),
                alignment="center",
                padding=8,
                width=45,
                height=32,
                border_radius=6,
                border=ft.Border(
                    ft.BorderSide(1, cor_borda), ft.BorderSide(1, cor_borda),
                    ft.BorderSide(1, cor_borda), ft.BorderSide(1, cor_borda)
                ),
                bgcolor=bgcolor,
                data=d
            )
            
            detector_clique = ft.GestureDetector(
                content=container_chip,
                on_tap=alternar_dia_btn
            )
            
            buttons_dict[d] = container_chip
            lista_botoes.append(detector_clique)

        txt_hora.value = automacoes[pino_rele]["hora_agenda"]
        if automacoes[pino_rele]["timer_minutos"] > 0:
            txt_timer.value = str(automacoes[pino_rele]["timer_minutos"])

        return ft.ExpansionTile(
            title=ft.Text("Configurar Temporizador e Agenda", size=13, color="blue200"),
            maintain_state=True,
            controls=[
                ft.Container(
                    padding=10,
                    bgcolor="black26",
                    border_radius=8,
                    content=ft.Column([
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
                        
                        ft.Row([
                            ft.Icon(ft.Icons.SCHEDULE, color="blue"),
                            ft.Text("Ligar às:", weight="w500"),
                            txt_hora,
                            ft.IconButton(icon=ft.Icons.SAVE, icon_color="blue", on_click=salvar_agenda)
                        ], alignment="spaceBetween"),
                        
                        ft.Text("Dias da semana:", size=12, color="white60"),
                        ft.Container(
                            height=100,
                            content=ft.Row(lista_botoes, wrap=True, alignment="center", spacing=5)
                        )
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
                criar_bloco_automacao("casa/rele1", txt_timer_d6, txt_hora_d6, buttons_d6, switch_luz)
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
                criar_bloco_automacao("casa/rele2", txt_timer_d7, txt_hora_d7, buttons_d7, switch_tomada)
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
    def conectar_mqtt_e_agendar():
        try:
            mqttc.connect(MQTT_SERVER, MQTT_PORT, 60)
            mqttc.loop_start()
        except Exception:
            pass

    def loop_verificacao_horario():
        while True:
            agora = datetime.datetime.now()
            dias_map = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
            dia_atual_str = dias_map[agora.weekday()]
            hora_atual_str = agora.strftime("%H:%M")

            for pino, dados in automacoes.items():
                if dados["hora_agenda"] == hora_atual_str and dia_atual_str in dados["dias_agenda"]:
                    mqttc.publish(pino, "ON")
                    if pino == "casa/rele1":
                        switch_luz.value = True
                    if pino == "casa/rele2":
                        switch_tomada.value = True
                    page.update()

            time.sleep(60)

    threading.Thread(target=conectar_mqtt_e_agendar, daemon=True).start()
    threading.Thread(target=loop_verificacao_horario, daemon=True).start()

ft.app(main)
            time.sleep(60)

    threading.Thread(target=conectar_mqtt_e_agendar, daemon=True).start()
    threading.Thread(target=loop_verificacao_horario, daemon=True).start()

ft.app(main)