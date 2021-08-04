from socket import AF_INET, SOCK_DGRAM
import sys
from socket import *
sys.path.append('../common')
from PTPPacket import *
import json

START_SEQUENCE_NO = 0
MAX_PACKET_SIZE = 64000

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


        self.seqNo = START_SEQUENCE_NO
        self.ackNo = 0
        self.receivedPackets = []

    def setup_connection(self):
        try:
           self.senderSocket = socket(AF_INET, SOCK_DGRAM)
        except:
            print('Error creating Sender socket')
            sys.exit()

    def handshake(self):
        # Send the initial SYN packet
        synSegment = create_packet(syn=1, seq_no=self.seqNo);
        self.senderSocket.sendto(json.dumps(synSegment).encode(), (self.recvHost, self.recvPort))

        # Get response from receiver
        msg, receiverAddress = self.senderSocket.recvfrom(MAX_PACKET_SIZE)
        parsedResponse = json.loads(msg.decode())
        print(f'Got from receiver: {parsedResponse}')

        # Final Acknowledgement
        if parsedResponse['syn'] == 1 and parsedResponse['ack'] == 1:
            ackSegment = create_packet(seq_no=self.seqNo+1, ack=1, ack_no=parsedResponse['seq_no']+1)
            self.senderSocket.sendto(json.dumps(ackSegment).encode(), (self.recvHost, self.recvPort))
        else:
            print("Handshake failed!!")
            self.senderSocket.close()
            sys.exit()
        
        self.seqNo = ackSegment['seq_no']
        self.ackNo = ackSegment['ack_no']

def check_args(args):
    if len(args) != 9:
        return 0
    return 1

if __name__ == "__main__":
    if check_args(sys.argv):
        
        # Initialize a Sender
        sender = Sender(sys.argv)
        sender.setup_connection()
        
        # Perform Handshaking
        sender.handshake()

    else:
        print('Arguments not Valid');