# -*- coding: utf-8 -*-

import pickle, random

#gerador de abstracts aleatorios
class LeroLeroGenerator():
    def __init__(self):
        pass
    
    def generate_trigram(self, words):
        if len(words) < 3:
            return
        for i in xrange(len(words) - 2):
            yield (words[i], words[i+1], words[i+2])

    def generate_chain(self, keywords_path="sample_of_10000.txt"):
        keywords_file = open("sample_of_10000.txt", "r")

        self.chain = {}
        
        for line in keywords_file.readlines():
            words = line.split()
            for word1, word2, word3 in generate_trigram(words):
                key = (word1, word2)
                if key in chain:
                    self.chain[key].append(word3)
                else:
                    self.chain[key] = [word3]

        self.chain

    def save_chain(self, path="chain.p"):
        pickle.dump(chain, open(path, "wb"))

    def load_chain(self, path="chain.p"):
        self.chain = pickle.load(open(path, "rb"))

    def generate(self):
        lerolero = []
        sword1 = "BEGIN"
        sword2 = "NOW"
        
        while sword2 != 'END':
            sword1, sword2 = sword2, random.choice(self.chain[(sword1, sword2)])
            lerolero.append(sword2)

        return ' '.join(lerolero)

def teste_lerolero():
    lerolerogen = LeroLeroGenerator()
    lerolerogen.load_chain()
    review = lerolerogen.generate()

    print(review)

if __name__ == '__main__':
    teste_lerolero()

'''
#abre o arquivo de keywords
fh = open("sample_of_10000.txt", "r")

chain = {}

def generate_trigram(words):
    if len(words) < 3:
        return
    for i in xrange(len(words) - 2):
        yield (words[i], words[i+1], words[i+2])
 
for line in fh.readlines():
    words = line.split()
    for word1, word2, word3 in generate_trigram(words):
        key = (word1, word2)
        if key in chain:
            chain[key].append(word3)
        else:
            chain[key] = [word3]

#salva o modelo em um arquivo
pickle.dump(chain, open("chain.p", "wb" ))

parser = argparse.ArgumentParser()
parser.add_argument('--period', type=str, help='Intervalo de tempo entre o envio de cada mensagem.', required=True)
parser.add_argument('--host', type=str, help='Endereço IP do servidor', required=True)
parser.add_argument('--port', type=int, help='Porta do servidor', required=True)

args = parser.parse_args()
'''

'''
def generate_review(chain):
    new_review = []
    sword1 = "BEGIN"
    sword2 = "NOW"
    
    while sword2 != 'END':
        sword1, sword2 = sword2, random.choice(chain[(sword1, sword2)])
        new_review.append(sword2)

    return new_review
    
chain = pickle.load(open("chain.p", "rb"))


while True: 
    print (' '.join(generate_review(chain)))
    print ('\n***\n')
'''
