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
        self.receivedPackets = []
        self.bufferList = []
        self.expectedSeqNo = 0

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

    def handshake(self):
        # Get the initial response
        senderMessage, senderAddress = self.receiverSocket.recvfrom(MAX_PACKET_SIZE)
        parsedMessage = json.loads(senderMessage.decode())
        print(f'Got initially from sender: {parsedMessage}')

        # Respond with a SYN_ACK
        if parsedMessage['syn'] == 1:
            packet = create_packet(seq_no=self.seqNo, ack=1, ack_no=get_seq_no(parsedMessage)+1, syn=1)
            self.receiverSocket.sendto(json.dumps(packet).encode(), senderAddress)
            self.seqNo += 1
            self.ackNo = get_ack_no(packet)
            print(f'Sending syn: {packet}')
        else:
            print('Receiver handshaking failed')

        # Receive final ACK fromsender
        packet, responseAddress = self.receiverSocket.recvfrom(MAX_PACKET_SIZE)
        parsedResponse = json.loads(packet.decode())
        print(f'Got ifinally from sender: {parsedResponse}')
        if is_ack(parsedResponse) == 1:
            print('Handshake Complete!')
            self.ackNo = get_seq_no(parsedResponse) + 1
        else:
            print('Handshake Failed!')
            sys.exit()
        
        self.seq_no = get_ack_no(parsedResponse)
        self.expectedSeqNo = get_seq_no(parsedResponse)

    def listen(self):
        
        # Open the file to write to
        writeFile = open(self.fileReceive, 'wb')
        
        while 1:
            msg, senderAddress = self.receiverSocket.recvfrom(MAX_PACKET_SIZE)
            parsedMsg = json.loads(msg.decode())
            if (is_fin(parsedMsg)):
                print('Received FIN, starting teardown.....')

                # Send ACK
                ackPacket = create_packet(ack=1, ack_no=get_seq_no(parsedMsg) + 1)
                self.receiverSocket.sendto(json.dumps(ackPacket).encode(), senderAddress)

                # Send FIN
                finPacket = create_packet(fin=1, seq_no=self.seqNo)
                self.receiverSocket.sendto(json.dumps(finPacket).encode(), senderAddress)
                self.receiverSocket.close()
                print('Socket Closed')
                break

            elif get_seq_no(parsedMsg) == self.expectedSeqNo:
                
                # Write to the file
                writeFile.write(get_data(parsedMsg).encode())
                self.expectedSeqNo += len(get_data(parsedMsg))
                self.receivedPackets.append(get_data(parsedMsg))
                print(f'Writing data: {msg.decode()}')
                
                # Check whether there are any packets in bufferList.
                # That are the next expected sequences.
                i = 0
                while i < len(self.bufferList):
                    if get_seq_no(self.bufferList[i]) == self.expectedSeqNo:
                        writeFile.write(get_data(self.bufferList[i]).encode())
                        expectedSeqNo += len(get_data(self.bufferList[i]))
                        print(f'Writing data: {get_data(self.bufferList[i])}')
                        self.bufferList.pop(i)
                        i-=1
                    i+=1
                    
            else:   # Sequence is not in correct order
                
                # You get a duplicate packet
                if (get_seq_no(parsedMsg) in self.receivedPackets) or (get_seq_no(parsedMsg) in self.bufferList):
                    print('Got duplicate packet')
                else:
                    if len(self.bufferList) == 0:
                        self.bufferList.append(parsedMsg)
                    else:
                        # Insert the packet at the right index
                        i = 0
                        while i < len(self.bufferList):
                            if get_seq_no(self.bufferList[i]) > get_seq_no(parsedMsg):
                                self.bufferList.insert(i, parsedMsg)
                                break
                            
                            if i == len(self.bufferList) - 1:
                                self.bufferList.append(parsedMsg)
                                break
                            i+=1

            # Send the right Ack Packet
            ackResponse = create_packet(ack=1, seq_no=self.seq_no, ack_no=self.expectedSeqNo)
            self.receiverSocket.sendto(json.dumps(ackResponse).encode(), senderAddress)
    
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

        # Listen on port
        receiver.listen()

    else:
        print('Receiver Arguments not Valid')