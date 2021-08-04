import json
import sys
from socket import *

sys.path.append('../common')
from PTPPacket import *

START_SEQUENCE_NO = 100
MAX_PACKET_SIZE = 64000

class Receiver:
    def __init__(self, receiverPort, fileReceive):
        self.receiverPort = receiverPort
        self.fileReceive = fileReceive
        self.receiverSocket = None

        self.seqNo = START_SEQUENCE_NO
        self.ackNo = 0

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

    def handshake(self):
        # Get the initial response
        senderMessage, senderAddress = self.receiverSocket.recvfrom(MAX_PACKET_SIZE)
        parsedMessage = json.loads(senderMessage.decode())
        print(f'Got initially from sender: {parsedMessage}')

        # Respond with a SYN_ACK
        if parsedMessage['syn'] == 1:
            packet = create_packet(seq_no=self.seqNo, ack=1, ack_no=parsedMessage['seq_no']+1, syn=1)
            self.receiverSocket.sendto(json.dumps(packet).encode(), senderAddress)
        else:
            print('Receiver handshaking failed')

        # Receive final ACK fromsender
        packet, responseAddress = self.receiverSocket.recvfrom(MAX_PACKET_SIZE)
        parsedResponse = json.loads(packet.decode())
        print(f'Got ifinally from sender: {parsedResponse}')
        if parsedResponse['ack'] == 1:
            print('Handshake Complete!')
        else:
            print('Handshake Failed!')
            sys.exit()

def check_args(args):
    if len(args) != 3:
        return 0
    return 1

if __name__ == '__main__':
    if check_args(sys.argv):
        
        # Setup Socket
        receiver = Receiver(int(sys.argv[1]), sys.argv[2])
        receiver.setup_connection()

        # Perform handshake
        receiver.handshake()

    else:
        print('Receiver Arguments not Valid')