from socket import AF_INET, SOCK_DGRAM
import sys
from socket import *
sys.path.append('../common')
from PTPPacket import *
import json

START_SEQUENCE_NO = 0
MAX_PACKET_SIZE = 64000

STATE_STARTING = 0
STATE_CONNECTED = 1 
STATE_SENDING_DATA = 2
STATE_FINISHED = 3
STATE_STOPPED = 4
STATE_TERMINATE = 5
STATE_CLOSE = 6


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

        self.state = STATE_STARTING
        self.seqNo = START_SEQUENCE_NO
        self.ackNo = 0
        self.receivedPackets = []

    def setup_connection(self):
        if self.state == STATE_STARTING:
            try:
                self.senderSocket = socket(AF_INET, SOCK_DGRAM)
            except:
                print('Error creating Sender socket')
                sys.exit()

    def handshake(self):
        if self.state == STATE_STARTING:
            # Send the initial SYN packet
            synSegment = create_packet(syn=1, seq_no=self.seqNo);
            self.senderSocket.sendto(json.dumps(synSegment).encode(), (self.recvHost, self.recvPort))

            # Get response from receiver
            msg, receiverAddress = self.senderSocket.recvfrom(MAX_PACKET_SIZE)
            parsedResponse = json.loads(msg.decode())
            print(f'Got from receiver: {parsedResponse}')

            # Final Acknowledgement
            if parsedResponse['syn'] == 1 and parsedResponse['ack'] == 1:
                ackSegment = create_packet(seq_no=self.seqNo+1, ack=1, ack_no=get_seq_no(parsedResponse)+1)
                self.senderSocket.sendto(json.dumps(ackSegment).encode(), (self.recvHost, self.recvPort))
            else:
                print("Handshake failed!!")
                self.senderSocket.close()
                sys.exit()
            
            self.seqNo = get_seq_no(ackSegment)
            self.ackNo = get_ack_no(ackSegment)
            self.state = STATE_CONNECTED

    def terminate_connection(self):
        # Send the initial FIN packet
        finSegment = create_packet(fin=1, seq_no=self.seqNo)
        self.senderSocket.sendto(json.dumps(finSegment).encode(), (self.recvHost, self.recvPort))
        self.state = STATE_STOPPED
        self.seqNo += 1

        while True:
            # Get the ACK from Receiver
            receiverResponse, receiverAddress = self.senderSocket.recvfrom(MAX_PACKET_SIZE)
            parsedResponse = json.loads(receiverResponse.decode())
            if self.state == STATE_STOPPED and is_ack(parsedResponse) and get_ack_no(parsedResponse) == self.seqNo:
                self.state = STATE_TERMINATE
            elif self.state == STATE_TERMINATE and is_fin(parsedResponse):
                ackSegment = create_packet(ack=1, ack_no=get_seq_no(parsedResponse) + 1, seq_no=self.seqNo)
                self.senderSocket.sendto(json.dumps(ackSegment).encode(), (self.recvHost, self.recvPort))
                self.state = STATE_CLOSE
                self.senderSocket.close()
                break                
            else:
                print('Error terminating')

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

        # Read and send data

        # Terminate connection
        sender.terminate_connection()

    else:
        print('Arguments not Valid');