
import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton,
                             QFrame, QFileDialog, QVBoxLayout, QHBoxLayout,
                             QSizePolicy, QMessageBox, QTextEdit, QInputDialog,
                             QDialog, QGridLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QIcon
from PyQt5.QtGui import QPixmap

import requests
import xml.etree.ElementTree as ET
import webbrowser
import googlemaps
import datetime
import google.generativeai as genai

# Define a API Key do Google Maps
api_key = "APIkey"

# Define a API Key do Google AI
GOOGLE_API_KEY = "APIkey"
genai.configure(api_key=GOOGLE_API_KEY)

# Configurações de geração e segurança (opcional)
generation_config = genai.GenerationConfig(temperature=0.7)
safety_settings = {
    "HARASSMENT": "BLOCK_NONE",
    "HATE": "BLOCK_NONE",
    "SEXUAL": "BLOCK_NONE",
    "DANGEROUS": "BLOCK_NONE",
}

# Inicializa o modelo Gemini
model = genai.GenerativeModel(
    model_name="models/gemini-pro",
    generation_config=generation_config,
    safety_settings=safety_settings
)

class GeocodingService:
    #Serviço para geocodificação de endereços
    def __init__(self, api_key):
        self.gmaps = googlemaps.Client(key=api_key)

    def geocode_address(self, address):
        #Geocodifica um endereço para coordenadas
        try:
            geocode_result = self.gmaps.geocode(address)
            if geocode_result:
                return geocode_result[0]['geometry']['location']
            else:
                return None
        except Exception as e:
            print(f"Erro ao geocodificar {address}: {e}")
            return None

class NFeParser:
    #Classe para parsear arquivos XML NFe
    def __init__(self):
        self.nsNFe = {"ns": "http://www.portalfiscal.inf.br/nfe"}

    def extract_client_info(self, nfe_file):
        #Extrai as informações do cliente de um arquivo XML NFe
        tree = ET.parse(nfe_file)
        root = tree.getroot()

        nome_cliente = root.find('ns:NFe/ns:infNFe/ns:dest/ns:xNome', self.nsNFe).text
        endereco = root.find('ns:NFe/ns:infNFe/ns:dest/ns:enderDest/ns:xLgr', self.nsNFe).text
        numero = root.find('ns:NFe/ns:infNFe/ns:dest/ns:enderDest/ns:nro', self.nsNFe).text
        bairro = root.find('ns:NFe/ns:infNFe/ns:dest/ns:enderDest/ns:xBairro', self.nsNFe).text
        cep = root.find('ns:NFe/ns:infNFe/ns:dest/ns:enderDest/ns:CEP', self.nsNFe).text
        cidade = root.find('ns:NFe/ns:infNFe/ns:dest/ns:enderDest/ns:xMun', self.nsNFe).text
        estado = root.find('ns:NFe/ns:infNFe/ns:dest/ns:enderDest/ns:UF', self.nsNFe).text
        nNF = root.find('ns:NFe/ns:infNFe/ns:ide/ns:nNF', self.nsNFe).text 

        endereco_completo = f"{endereco}, {numero}, {bairro}, {cidade} - {estado}, {cep}"

        return nome_cliente, endereco_completo, nNF

    def extract_sender_info(self, nfe_file):
        #Extrai as informações do remetente de um arquivo XML NFe
        tree = ET.parse(nfe_file)
        root = tree.getroot()

        nome_remetente = root.find('ns:NFe/ns:infNFe/ns:emit/ns:xNome', self.nsNFe).text
        endereco = root.find('ns:NFe/ns:infNFe/ns:emit/ns:enderEmit/ns:xLgr', self.nsNFe).text
        numero = root.find('ns:NFe/ns:infNFe/ns:emit/ns:enderEmit/ns:nro', self.nsNFe).text
        bairro = root.find('ns:NFe/ns:infNFe/ns:emit/ns:enderEmit/ns:xBairro', self.nsNFe).text
        cep = root.find('ns:NFe/ns:infNFe/ns:emit/ns:enderEmit/ns:CEP', self.nsNFe).text
        cidade = root.find('ns:NFe/ns:infNFe/ns:emit/ns:enderEmit/ns:xMun', self.nsNFe).text
        estado = root.find('ns:NFe/ns:infNFe/ns:emit/ns:enderEmit/ns:UF', self.nsNFe).text

        endereco_completo = f"{endereco}, {numero}, {bairro}, {cidade} - {estado}, {cep}"

        return nome_remetente, endereco_completo

class RouteOptimizer:
    #Classe para otimizar a rota de entrega
    def __init__(self, starting_point, destinations, geocoding_service):
        self.starting_point = starting_point
        self.destinations = destinations
        self.optimized_route = []
        self.geocoding_service = geocoding_service

    def optimize_route(self):
        #Obtém a rota otimizada usando a API do Google Maps Directions
        self.optimized_route = []
        if len(self.destinations) > 1:
            # Otimiza a ordem dos destinos a partir do ponto de partida
            self.destinations = sorted(
                self.destinations,
                key=lambda destination: self.calculate_distance(
                    self.starting_point, destination
                )
            )
            # Inclui o ponto de partida no início da rota
            self.optimized_route = [self.starting_point] + self.destinations
        else:
            self.optimized_route = [self.starting_point, self.destinations[0]]

        # Converte os endereços para coordenadas geográficas
        self.optimized_route = self.convert_addresses_to_coordinates(
            self.optimized_route
        )

    def calculate_distance(self, origin, destination):
        #Calcula a distância entre dois endereços usando a API Geocoding
        try:
            origin_coords = self.geocoding_service.geocode_address(origin)
            destination_coords = self.geocoding_service.geocode_address(destination)
            if origin_coords and destination_coords:
                distancia = self.geocoding_service.gmaps.distance_matrix(
                    origins=[origin_coords],
                    destinations=[destination_coords],
                    mode='driving'
                )['rows'][0]['elements'][0]['distance']['value']
                return distancia
            else:
                return float('inf')
        except Exception as e:
            print(f"Erro ao calcular a distância: {e}")
            return float('inf')

    def convert_addresses_to_coordinates(self, address_list):
        #Converte uma lista de endereços para coordenadas
        coordinates = []
        for address in address_list:
            coordinates.append(self.geocoding_service.geocode_address(address))
        return coordinates

    

class MainWindow(QWidget):
    #Janela principal da aplicação
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nome da empresa")
        self.setWindowIcon(QIcon('icone.png'))
        self.nfe_files = []
        self.destinations = []
        self.client_names = set()
        self.sender_name = None
        self.starting_point = None
        self.nNFs = [] 
        self.geocoding_service = GeocodingService(api_key)
        self.nfe_parser = NFeParser()
        self.chat_context = []
        self.chat_history = []
        self.chat_model = model

        self.setup_ui()

    def setup_ui(self):
        
        font = QFont("Ubuntu", 10)
        font.setBold(True)
        app.setFont(font)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)  
        image = QLabel(self)
        pixmap = QPixmap('imgbg2.png')
        image.setPixmap(pixmap.scaledToWidth(300))
        image.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(image)

        # Frame para botão "Selecionar Arquivos"
        file_frame = QFrame(self)
        file_layout = QHBoxLayout()
        file_layout.setContentsMargins(0, 0, 0, 0)
        select_button = QPushButton("Selecionar Arquivos XML", file_frame)
        select_button.clicked.connect(self.select_files)
        select_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        file_layout.addWidget(select_button)
        file_frame.setLayout(file_layout)
        main_layout.addWidget(file_frame)

        # Frame para botão "Carregar Destinos"
        load_frame = QFrame(self)
        load_layout = QHBoxLayout()
        load_layout.setContentsMargins(0, 0, 0, 0)
        load_button = QPushButton("Carregar Destinos", load_frame)
        load_button.clicked.connect(self.load_destinations)
        load_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        load_layout.addWidget(load_button)
        load_frame.setLayout(load_layout)
        main_layout.addWidget(load_frame)

        # Frame para exibir as informações
        info_frame = QFrame(self)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        self.info_label = QLabel("Informações:", info_frame)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setWordWrap(True)  # Quebra de linha automática
        info_layout.addWidget(self.info_label)
        info_frame.setLayout(info_layout)
        main_layout.addWidget(info_frame)

        # Botão "Iniciar Chat"
        chat_button = QPushButton("Iniciar Chat IA", self)
        chat_button.clicked.connect(self.open_chat_window)
        chat_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(chat_button)

        # Botão "Processar Rota"
        process_button = QPushButton("Processar Rota", self)
        process_button.clicked.connect(self.process_route)
        process_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(process_button)

        self.setLayout(main_layout)
        self.setFixedSize(400, 500) 

    def select_files(self):
        #Abre uma caixa de diálogo para o usuário selecionar arquivos XML.
        self.nfe_files, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecione os arquivos XML NFe",
            "",
            "Arquivos XML (*.xml);;Todos os arquivos (*)"
        )

    def load_destinations(self):
        #Carrega os destinos dos arquivos XML e exibe os nomes dos clientes.
        if self.nfe_files:
            self.destinations = []
            self.client_names = set()
            self.sender_name = None
            self.starting_point = None
            self.nNFs = []
            for file in self.nfe_files:
                sender_name, starting_point = self.nfe_parser.extract_sender_info(file)
                if self.sender_name is None:
                    self.sender_name = sender_name
                    self.starting_point = starting_point

                client_name, address, nNF = self.nfe_parser.extract_client_info(file)
                self.client_names.add(client_name)  # Adiciona o nome do cliente sem duplicação
                if address not in self.destinations:  # Verifica se o endereço já está na lista
                    self.destinations.append(address)
                self.nNFs.append(nNF)  # Armazena o nNF na lista

            # Atualiza a lista de nomes de clientes na interface
            self.info_label.setText(
                f"Remetente:\n{self.sender_name}\n\nDestinatários:\n{'\n'.join(self.client_names)}"
            )
        else:
            QMessageBox.warning(self, "Aviso", "Selecione os arquivos XML NFe primeiro.")

    def process_route(self):
        #Processa a rota otimizada e gera o arquivo de log.
        if self.nfe_files:
            if self.starting_point:
                route = RouteOptimizer(
                    self.starting_point,
                    self.destinations,
                    self.geocoding_service
                )
                route.optimize_route()
                # route.print_route() - A função "print_route" foi removida

                if route.optimized_route:
                    route_url = self.display_route_on_google_maps(
                        route.optimized_route
                    )
                    self.generate_route_log(self.nNFs, route_url)
                else:
                    QMessageBox.warning(self, "Aviso", "A rota otimizada não foi encontrada.")
            else:
                QMessageBox.warning(self, "Aviso", "O ponto de partida não foi encontrado nos arquivos XML.")
        else:
            QMessageBox.warning(self, "Aviso", "Selecione os arquivos XML NFe primeiro.")

    def generate_google_maps_url(self, optimized_route):
        #Gera a URL completa do Google Maps com a rota e marcadores.
        # Obtém as coordenadas do ponto de partida
        starting_point_coords = optimized_route[0]

        # Cria a lista de waypoints a partir dos destinos (sem o ponto de partida)
        waypoints = '|'.join(
            f"{point['lat']},{point['lng']}" for point in optimized_route[1:-1]
        )

        # Monta a URL do Google Maps, incluindo o ponto de partida como waypoint
        url = f"https://www.google.com/maps/dir/?api=1&origin=&destination={optimized_route[-1]['lat']},{optimized_route[-1]['lng']}&waypoints={starting_point_coords['lat']},{starting_point_coords['lng']}%7C{waypoints}"

        return url

    def display_route_on_google_maps(self, optimized_route):
        #Exibe a rota no Google Maps com marcadores para o ponto de partida e destinos
        url = self.generate_google_maps_url(optimized_route)
        webbrowser.open_new_tab(url)
        return url

    def generate_route_log(self, nNFs, route_url):
        #Gera um arquivo de log TXT com os dados da rota.
        current_date = datetime.datetime.now().strftime("%d.%m.%Y")
        file_name = f"log_rotas_{current_date}.txt"

        with open(file_name, "a", encoding='utf-8') as file:
            if file.tell() > 0:
                file.write("\n")

            file.write(f"Data da Rota: {current_date}\n")
            file.write(f"NFes:\n")
            for nNF in nNFs:
                file.write(f"- {nNF}\n")
            file.write(f"URL da Rota: {route_url}\n")

    def open_chat_window(self):
        """Abre a janela de chat."""
        self.chat_window = ChatWindow()
        self.chat_window.show()
        

class ChatWindow(QDialog):
    #Janela de chat com a IA.
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat IA")
        self.chat_context = []
        self.chat_history = []
        self.chat_model = model
        self.setup_ui()
        self.setWindowIcon(QIcon('icone.png'))

    def setup_ui(self):
        
        font = QFont("Ubuntu", 10)
        font.setBold(True)
        app.setFont(font)

        # Cria o layout principal
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)

        # Adiciona a caixa de texto do chat
        self.chat_edit = QTextEdit(self)
        self.chat_edit.setReadOnly(True)
        self.chat_edit.setStyleSheet("background-color: #262D35; border: none")
        self.chat_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.chat_edit)

        # Adiciona o campo de entrada
        self.input_layout = QHBoxLayout()
        self.input_edit = QTextEdit(self)
        self.input_edit.setPlaceholderText("Digite sua mensagem...")
        self.input_edit.setStyleSheet("background-color: #262D35; border: none")
        self.input_layout.addWidget(self.input_edit)
        self.input_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_edit.setMaximumHeight(40)

        # Botão para enviar a mensagem
        self.send_button = QPushButton("Enviar", self)
        self.send_button.clicked.connect(self.send_message)
        self.input_layout.addWidget(self.send_button)

        main_layout.addLayout(self.input_layout)
        self.setLayout(main_layout)
        self.setFixedSize(400, 300)

        # Iniciar o chat IA
        self.start_chat_ia()

    def start_chat_ia(self):
        #Inicia o chat com a IA
        self.chat_context = []
        self.chat_history = []
        self.chat_model = model
        self.chat_edit.setText(
            """Mensagem de saudação do inicio do chat\n"""
        )

    def send_message(self):
        #Envia a mensagem para a IA.
        user_input = self.input_edit.toPlainText().strip()
        if user_input:
            self.chat_history.append(user_input)
            self.process_chat_response(user_input)
            self.input_edit.clear()

    def process_chat_response(self, user_input):
        #Processa a resposta do usuário no chat.
        self.chat_context.append(f"{self.chat_history[-1]} {user_input}")

        # Contexto
        prompt = f"""
        Definição de contexto para orientação de abordagem da IA, como definição de persona ou input
        de informações especificas.
        Contexto: {self.chat_context}
        """
        response = self.chat_model.start_chat().send_message(prompt)
        self.chat_history.append(response.text)
        self.chat_edit.append(f"Você: {user_input}\n\nChatIA: {response.text}\n\n")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Define as cores da interface
    app.setStyleSheet("""
        QWidget { 
            ;
            background-repeat: no-repeat;
            background-position: center;
            background-color: #161F28; /* Preto */
            color: #FFFFFF; /* Branco */
            font-family: 'Ubuntu';
        }
        QPushButton {
            background-color: #E27532; /* Laranja */
            color: #FFFFFF; /* Branco */
            border: none;
            padding: 10px 20px;
            font-weight: bold;
            border-radius: 5px; /* Arredondamento suave */
        }
        QPushButton:hover {
            background-color: #E27532; /* Laranja */
            color: #F1F0F0; /* Branco gelo */
        }
        QTextEdit {
            background-color: #262D35; /* Cinza escuro */
            border: none;
            color: #FFFFFF; /* Branco */
            font-family: 'Ubuntu';
            font-size: 12px;
            padding: 10px;
        }
        QTextEdit::placeholder {
            color: #777777; /* Cinza claro */
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())