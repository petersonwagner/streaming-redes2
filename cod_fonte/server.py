# -*- coding: utf-8 -*-

import socket
import json
import logging
import argparse
import time
import threading
import lerolero
import random
import sys, signal
from datetime import datetime

class Server():
    def __init__(self, host, port, interval, log_path):
        #tratamento de sinais para "sair graciosamente"
        signal.signal( signal.SIGINT, lambda signal, frame: self.stop_server())
        signal.signal( signal.SIGTERM, lambda signal, frame: self.stop_server())

        #seta variaveis a partir dos parametros
        self.host = host
        self.port = port
        self.interval = interval
        self.log_path = log_path

        #cria o logger
        self.create_logger()

        self.logger.info('Criando servidor com parametros host: {}, port:{}, interval: {}'.format(self.host, self.port, self.interval))

        #cria o socket UDP
        self.logger.info('Criando socket UDP')
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.logger.info('Binding server no endereço ({},{})'.format(self.host, self.port))
        self.server_address = (self.host, self.port)
        self.udp_socket.settimeout(1)
        self.udp_socket.bind(self.server_address)
        
        #isso serve como uma lista thread-safe para o nosso servidor
        self.active_clients = []

        #flag de parada
        self.server_running = True

        #inicia as threads de loops principais do servidor
        self.listen_thread = threading.Thread(target=self.listen_loop, args=(self.active_clients,))
        self.stream_thread = threading.Thread(target=self.stream_loop, args=(self.active_clients,))

        #inicia o gerador de lerolero
        self.logger.info('iniciando gerador de lerolero')
        self.lerolero = lerolero.LeroLeroGenerator()
        self.lerolero.load_chain()
        self.logger.info('gerador de lerolero iniciado')

    #inicia o servidor
    def start_server(self):
        self.logger.info('Iniciando servidor')
        
        self.logger.info('Iniciando thread de listening')
        self.listen_thread.start()

        self.logger.info('Iniciando thread de streaming')
        self.stream_thread.start()
        
        self.logger.info('Servidor iniciado')

    #cria um logger que printa no arquivo log/server.log
    #e ao mesmo joga na saida stdout
    def create_logger(self):
        self.logger = logging.getLogger('server') 
        self.logger.setLevel(logging.INFO)
 
        #cria um formatter de log
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s') 
        
        #cria um manipulador de arquivo (para o arquivo.log)
        file_handler = logging.FileHandler(self.log_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        #cria um manipulador de string (para stdout)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
 
        #adiciona os manipuladores ao logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    #loop de listening, recebe pedidos dos clientes para receber o streaming
    def listen_loop(self, active_clients):
        while self.server_running:
            #recebe do socket os dados e o endereço de quem enviou
            try:
                data_bytes, client_address = self.udp_socket.recvfrom(2048)
            except:
                continue
            
            #transforma de bytes para string
            data_string = data_bytes.decode('utf-8')

            #transforma em objeto
            data_json = json.loads(data_string)
            
            self.logger.info('Dados recebidos do endereço {}: {}'.format(client_address, data_json))
            
            #se for uma requisição para receber o streaming
            if data_json.get('request') == 'receive_streaming':
                self.logger.info('novo cliente: {}'.format(client_address))

                #adiciona o endereço do cliente na
                #lista de endereços para mandar o streaming
                active_clients.append(client_address)
                self.logger.info('lista de clientes ativos: {}'.format(active_clients))


    #retorna uma lista com pedaços de tamanho <= n da lista data
    def split_data(self, data, split_size):
        split_size = max(1, split_size)
        return [data[i:i+split_size] for i in range(0, len(data), split_size)]

    #loop de envio de dados
    def stream_loop(self, active_clients):
        #começa com um numero de sequencia aleatorio
        sequence_number = random.randint(0,1024)
        
        while self.server_running:

            #nao faz nada se nao tiver clientes ativos
            if not self.active_clients:
                continue
            
            #obtem uma string de lerolero
            data = self.lerolero.generate()
            self.logger.debug ('len(lerolero): {}'.format(len(data)))

            #divide a string em pedaços de 1024 caracteres
            #exemplo:
            #'string_gigante' => ['strin', 'g_gig', 'ante']
            splits = self.split_data(data, 1024)
            
            #para cada pedaço dessa string
            for split_num, split in enumerate(splits):
                sequence_number += 1
                
                #formato da mensagem              #exemplo: 'g_gig'
                message = {
                    'sequence': sequence_number,  #numero de sequencia
                    'data': split,                #dados do pedaço,   ex: 'g_gig'
                    'split_num': split_num,       #numero do pedaço,  ex: pedaço numero 1 de 2
                    'split_max': len(splits)-1    #numero de pedaços, ex: 2
                }

                #transforma o objeto message em bytes
                data_bytes = bytes(json.dumps(message), encoding='utf-8')

                self.logger.debug('Mandando dados para os clientes ativos')
                
                #manda para todos os clientes ativos
                for client_address in active_clients:
                    self.logger.info('sending message(id:{}) to {}'.format(sequence_number, client_address))

                    #envia a mensagem o cliente
                    try:
                        self.udp_socket.sendto (data_bytes, client_address)
                    except Exception as exc:
                        self.logger.error('erro ao enviar para o cliente: {}'.format(exc))


                #espera o intervalo de tempo para mandar novamente
                time.sleep(self.interval)
            


    #sair graciosamente
    def stop_server(self):
        self.server_running = False
        self.logger.info('stream_thread.join()')
        self.stream_thread.join()
        self.udp_socket.close()
        self.logger.info('listen_thread.join()')
        self.listen_thread.join()


#parametros default
hostname = socket.gethostname()
default_host = socket.gethostbyname(hostname)
default_port = 55000
default_interval = 0.5
default_log_path = '../log/server_{}'.format(datetime.now().strftime('%d-%m-%Y_%H-%M-%S'))

#parser da linha de comando
parser = argparse.ArgumentParser(description='Servidor')
parser.add_argument('--interval', type=float,
    help='Intervalo de tempo entre o envio de cada mensagem.',
    action = 'store', dest = 'interval', default = default_interval)

parser.add_argument('--host', type=str,
    help='Endereço IP do servidor', action = 'store',
    dest = 'host', default = default_host)

parser.add_argument('--port', type=int,
    help='Porta do servidor', action = 'store',
    dest = 'port', default = default_port)

parser.add_argument('--log_path', type=str,
    help='Path do log gerado', action = 'store',
    dest = 'log_path', default = default_log_path)

if sys.version_info.major != 3:
    print ('Esta aplicação suporta apenas python3')
    sys.exit(1)

args = parser.parse_args()


server = Server (
    args.host,
    args.port,
    args.interval,
    args.log_path
)
 
server.start_server()
