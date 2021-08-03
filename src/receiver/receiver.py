import sys
from socket import *

class Receiver:
    def __init__(self, receiverPort, fileReceive):
        self.receiverPort = receiverPort
        self.fileReceive = fileReceive
        self.receiverSocket = None

    def setup_connection(self):
        try:
            self.receiverSocket = socket(AF_INET, SOCK_DGRAM)
        except:
            print('Error creating a Receiver socket.')
            sys.exit()

        try:
            self.receiverSocket.bind(('localhost', self.receiverPort))
        except:
            print(f'Error binding to port - {self.receiverPort}')
            sys.exit()

    def listen(self):
        while 1:
            msg, serverAddress = self.receiverSocket.recvfrom(64000)
            print(f'Received data: {msg.decode()}')


def check_args(args):
    if len(args) != 3:
        return 0
    return 1

if __name__ == '__main__':
    if check_args(sys.argv):
        
        # Setup Socket
        receiver = Receiver(int(sys.argv[1]), sys.argv[2])
        receiver.setup_connection()
        receiver.listen()

    else:
        print('Receiver Arguments not Valid')