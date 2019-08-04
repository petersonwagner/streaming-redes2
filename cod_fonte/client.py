# -*- coding: utf-8 -*-

import socket
import json
import logging
import argparse
import sys
import signal
from datetime import datetime
import threading
import queue
import collections

class Client():
  def __init__(self, server_host, server_port, log_path):

    #tratamento de sinais para "sair graciosamente"
    signal.signal( signal.SIGINT, lambda signal, frame: self.stop_client())
    signal.signal( signal.SIGTERM, lambda signal, frame: self.stop_client())

    #seta variaveis a partir dos parametros
    self.server_host = server_host
    self.server_port = server_port
    self.log_path = log_path

    #cria o logger
    self.create_logger()

    self.logger.info('Iniciando cliente')

    #cria o socket UDP
    self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.udp_socket.settimeout(5)

    self.server_address = (self.server_host, self.server_port)
    self.client_running = True

    #thread que escuta o input do usuario
    self.input_queue = queue.Queue()
    self.input_thread = threading.Thread(target=self.input_loop, args=(self.input_queue,))
    self.input_thread.daemon = True
    self.input_thread.start()

    #pequeno historico dos ultimos x itens recebidos
    #usamos collections.deque como uma lista de tamanho fixo
    self.items_history = collections.deque([], maxlen=10000)

    self.logger.info('Cliente iniciado')

    #variaveis uteis para gerar dados estatisticos
    self.total_packets_received = 0
    self.lost_messages = 0
    self.total_scrambled_packets = 0
    self.last_sequence_number = None
    self.first_sequence_number = None


  #cria um logger que printa no arquivo log/client.log
  #e ao mesmo joga na saida stdout
  def create_logger(self):
      self.logger = logging.getLogger('client')
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

  #thread que escuta o input do usuario
  #por ser uma daemon, ela morre sem condição parada junto com a aplicação
  def input_loop(self, input_queue):
    while True:
      input_queue.put(input())

  #loop principal que recebe o streaming indefinidamente
  def get_stream(self):
    self.logger.info('enviando pedido para receber o streaming')

    #requisição feita para o servidor
    request_msg = {
      'request': 'receive_streaming'
    }

    #transforma o objeto em bytes
    request_msg_bytes = json.dumps(request_msg).encode('utf-8')

    #envia a requisição para o servidor
    try:
      sent = self.udp_socket.sendto(request_msg_bytes, self.server_address)
    except Exception as exc:
      self.logger.error('Erro ao mandar requisicao ao servidor: {}'.format(exc))


    expected_sequence = None
    joined_msg_fragments = ''

    #loop de recebimento da stream
    while self.client_running:

      try:
        msg_bytes, client = self.udp_socket.recvfrom(2048)
      except socket.timeout:
        self.logger.error('Conexao com o servidor foi perdida (timeout 10 segundos)')
        break
      except Exception as exc:
        self.logger.error('Erro ao receber mensagem do servidor: {}'.format(exc))
        continue

      #decodifica a mensagem de bytes para objeto
      try:
        message = json.loads(msg_bytes.decode('utf-8'))
      except:
        self.logger.error('Erro ao decodificar mensagem do servidor')
        continue

      #printa a mensagem
      self.logger.debug(json.dumps(message, indent=3))


      #conta mensagens fora de ordem
      if expected_sequence is None:
        expected_sequence = message['sequence'] + 1

      if message['sequence'] > expected_sequence:
        self.total_scrambled_packets += 1

      expected_sequence += 1

      #informações úteis para a estatistica
      if self.first_sequence_number is None:
        self.first_sequence_number = message['sequence']

      if self.last_sequence_number is None:
        self.last_sequence_number = message['sequence']

      if message['sequence'] > self.last_sequence_number:
        self.last_sequence_number = message['sequence']


      #adiciona ao contador de mensagens recebidas
      self.total_packets_received += 1

      #reune as mensagens divididas
      joined_msg_fragments += message['data']

      if message['split_num'] == message['split_max']:
        #salva a mensagem inteira no historico
        self.items_history.append({
          'id': message['sequence'],
          'text': joined_msg_fragments
        })

        #joga na tela para o usuario ver a mensagem 
        print('[{}] {}\n\n\n'.format(message['sequence'], joined_msg_fragments))

        #zera o buffer
        joined_msg_fragments = ''

      #trata input do usuario
      if not self.input_queue.empty():
        id_to_save = self.input_queue.get()
        self.save_text(id_to_save)

    #gera estatisticas da rede
    if self.total_packets_received > 0:
      #calculamos o numero total de pacotes esperados
      #fazendo ultimo sequence_number subtraido do primeiro sequence_number recebido
      total_packets_expected = self.last_sequence_number - self.first_sequence_number + 1
      
      #o numero de pacotes perdidos é o numero total de pacotes esperados
      #subtraído do número total recebidos
      total_lost_packets = total_packets_expected - self.total_packets_received

      self.logger.info('Numero total de pacotes recebidos: {}'.format(self.total_packets_received))
      self.logger.info('Numero total de pacotes perdidos: {}'.format(total_lost_packets))
      self.logger.info('Numero total de pacotes trocados: {}'.format(self.total_scrambled_packets))

    #fecha o socket
    self.udp_socket.close()

  def save_text(self, id_to_save):
    #transforma o input do usuario em inteiro
    try:
      id_to_save = int(id_to_save)
    except ValueError:
      print ('id deve ser um número')
      return False

    #abre o arquivo de saida
    text_file = open("output.txt", "w")

    #procura pelo item pedido no historico e salva
    for item in self.items_history:
      if item['id'] == id_to_save:
        text_file.write(item['text'])
        print ('texto [{}] salvo com sucesso'.format(id_to_save))
    
    #fecha o arquivo
    text_file.close()
    return True


  #sair graciosamente
  def stop_client(self):
    self.logger.info('Fechando o cliente')
    self.client_running = False
    self.input_loop


#parametros default
default_host = 'localhost'
default_port = 55000
default_log_path = '../log/client_{}'.format(datetime.now().strftime('%d-%m-%Y_%H-%M-%S'))

#parser da linha de comando
parser = argparse.ArgumentParser(description='Cliente')
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

client = Client (
    args.host,
    args.port,
    args.log_path
)

client.get_stream()
