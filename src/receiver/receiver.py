import json
import sys
from socket import *
from threading import current_thread
import time

sys.path.append('../common')
from PTPPacket import *
from logger import *

START_SEQUENCE_NO = 100
MAX_PACKET_SIZE = 64000

class Receiver:
    def __init__(self, receiverPort, fileReceive):
        self.receiverPort = receiverPort
        self.fileReceive = fileReceive
        self.receiverSocket = None

        self.logger = Logger('Receiver_log.txt')
        self.startTime = 0
        self.receivedDataSize = 0
        self.dataSegmentsCount = 0
        self.duplicateCount = 0
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

        self.startTime = time.time()

        # Get the initial response
        senderMessage, senderAddress = self.receiverSocket.recvfrom(MAX_PACKET_SIZE)
        parsedMessage = json.loads(senderMessage.decode())
        currTime = time.time()
        logTime = (currTime - self.startTime) * 1000
        self.logger.create_log_entry("rcv", logTime, 'S', get_seq_no(parsedMessage), len(get_data(parsedMessage)), get_ack_no(parsedMessage))
        print(f'Got initially from sender: {parsedMessage}')

        # Respond with a SYN_ACK
        if parsedMessage['syn'] == 1:
            packet = create_packet(seq_no=self.seqNo, ack=1, ack_no=get_seq_no(parsedMessage)+1, syn=1)
            self.receiverSocket.sendto(json.dumps(packet).encode(), senderAddress)
            currTime = time.time()
            logTime = (currTime - self.startTime) * 1000
            self.logger.create_log_entry("snd", logTime, 'SA', get_seq_no(packet), len(get_data(packet)), get_ack_no(packet))
            self.seqNo += 1
            self.ackNo = get_ack_no(packet)
            print(f'Sending syn: {packet}')
        else:
            print('Receiver handshaking failed')

        # Receive final ACK fromsender
        packet, responseAddress = self.receiverSocket.recvfrom(MAX_PACKET_SIZE)
        parsedResponse = json.loads(packet.decode())
        currTime = time.time()
        logTime = (currTime - self.startTime) * 1000
        self.logger.create_log_entry("rcv", logTime, 'S', get_seq_no(parsedResponse), len(get_data(parsedResponse)), get_ack_no(parsedResponse))
        
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
            currTime = time.time()
            logTime = (currTime - self.startTime) * 1000
            self.logger.create_log_entry("rcv", logTime, 'F', get_seq_no(parsedMsg), len(get_data(parsedMsg)), get_ack_no(parsedMsg))

            if (is_fin(parsedMsg)):
                print('Received FIN, starting teardown.....')

                # Send ACK
                ackPacket = create_packet(ack=1, ack_no=get_seq_no(parsedMsg) + 1)
                self.receiverSocket.sendto(json.dumps(ackPacket).encode(), senderAddress)
                currTime = time.time()
                logTime = (currTime - self.startTime) * 1000
                self.logger.create_log_entry("snd", logTime, 'A', get_seq_no(ackPacket), len(get_data(ackPacket)), get_ack_no(ackPacket))

                # Send FIN
                finPacket = create_packet(fin=1, seq_no=self.seqNo)
                self.receiverSocket.sendto(json.dumps(finPacket).encode(), senderAddress)
                currTime = time.time()
                logTime = (currTime - self.startTime) * 1000
                self.logger.create_log_entry("snd", logTime, 'FA', get_seq_no(finPacket), len(get_data(finPacket)), get_ack_no(finPacket))
                self.logger.print_receiver_details(self.receivedDataSize, self.dataSegmentsCount, self.duplicateCount)
                self.receiverSocket.close()
                print('Socket Closed')
                break

            elif get_seq_no(parsedMsg) == self.expectedSeqNo:
                
                self.dataSegmentsCount += 1
                self.receivedDataSize += len(get_data(parsedMsg))
                # Write to the file
                writeFile.write(get_data(parsedMsg).encode())
                self.expectedSeqNo += len(get_data(parsedMsg))
                self.receivedPackets.append(get_data(parsedMsg))
                currTime = time.time()
                logTime = (currTime - self.startTime) * 1000
                self.logger.create_log_entry("rcv", logTime, 'D', get_seq_no(parsedMsg), len(get_data(parsedMsg)), get_ack_no(parsedMsg))
                
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
                    self.duplicateCount += 1
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
            currTime = time.time()
            logTime = (currTime - self.startTime) * 1000
            self.logger.create_log_entry("snd", logTime, 'A', get_seq_no(ackResponse), len(get_data(ackResponse)), get_ack_no(ackResponse))

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