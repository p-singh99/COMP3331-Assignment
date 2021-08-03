from socket import AF_INET, SOCK_DGRAM
import sys
from socket import *

class Sender:
    def __init__(self, argv):
        self.recvHost = argv[1]
        self.recvPort = int(argv[2])
        self.file = argv[3]
        self.MWS = int(argv[4])
        self.MSS = int(argv[5])
        self.timeout = int(argv[6])
        self.pDrop = int(argv[7])
        self.seed = int(argv[8])
        self.senderSocket = None

    def setup_connection(self):
        try:
            self.senderSocket = socket(AF_INET, SOCK_DGRAM)
        except:
            print('Error creating Sender socket')
            sys.exit()

def check_args(args):
    if len(args) != 9:
        return 0
    return 1

if __name__ == "__main__":
    if check_args(sys.argv):
        sender = Sender(sys.argv)
        sender.setup_connection()
        msg = 'Hello Receiver'
        sender.senderSocket.sendto(msg.encode(), ('localhost', sender.recvPort))
    else:
        print('Arguments not Valid');