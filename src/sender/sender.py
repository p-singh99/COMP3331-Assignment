import os
from socket import AF_INET, SOCK_DGRAM
import sys
import random
from socket import *
sys.path.append('../common')
from PTPPacket import *
from logger import *
import json
import threading
import time

START_SEQUENCE_NO = 0
MAX_PACKET_SIZE = 64000

STATE_STARTING = 0
STATE_CONNECTED = 1 
STATE_SENDING_DATA = 2
STATE_FINISHED = 3
STATE_STOPPED = 4
STATE_TERMINATE = 5
STATE_CLOSE = 6

LOCK = threading.Condition()

class Sender:
    def __init__(self, argv):
        self.recvHost = argv[1]
        self.recvPort = int(argv[2])
        self.file = argv[3]
        self.MWS = int(argv[4])
        self.MSS = int(argv[5])
        self.timeout = int(argv[6])
        self.pDrop = float(argv[7])
        self.seed = int(argv[8])
        self.senderSocket = None

        self.logger = Logger("Sender_log.txt")
        self.state = STATE_STARTING
        self.fileStat = 0
        self.seqNo = START_SEQUENCE_NO
        self.latestPacketAcked = START_SEQUENCE_NO
        self.ackNo = 0
        self.latestAckedByte = 0
        self.handShakeSeqNo = 0
        self.windowBase = self.seqNo
        self.segmentsCount = 0
        self.retransmissions = 0
        self.packetsDropped = 0
        self.duplicateAcks = 0
        self.fileRead = []
        self.startTime = 0
        self.timerStarted = False
        self.timerStartTime = 0
        self.timerStopTime = 0
        self.sentPackets = []
        self.receivedPackets = []
        self.finishedReceiving = False

    def setup_connection(self):
        if self.state == STATE_STARTING:
            try:
                self.senderSocket = socket(AF_INET, SOCK_DGRAM)
            except:
                print('Error creating Sender socket')
                sys.exit()

    def handshake(self):
        if self.state == STATE_STARTING:

            self.startTime = time.time()

            # Send the initial SYN packet
            synSegment = create_packet(syn=1, seq_no=self.seqNo);
            self.senderSocket.sendto(json.dumps(synSegment).encode(), (self.recvHost, self.recvPort))
            currTime = time.time()
            logTime = (currTime - self.startTime) * 1000
            self.logger.create_log_entry("snd", logTime, 'S', get_seq_no(synSegment), len(get_data(synSegment)), 0)

            # Get response from receiver
            msg, receiverAddress = self.senderSocket.recvfrom(MAX_PACKET_SIZE)
            parsedResponse = json.loads(msg.decode())
            currTime = time.time()
            logTime = (currTime - self.startTime) * 1000
            self.logger.create_log_entry("rcv", logTime, 'SA', get_seq_no(parsedResponse), len(get_data(parsedResponse)), get_ack_no(parsedResponse))

            print(f'Got from receiver: {parsedResponse}')

            # Final Acknowledgement
            if parsedResponse['syn'] == 1 and parsedResponse['ack'] == 1:
                ackSegment = create_packet(seq_no=self.seqNo+1, ack=1, ack_no=get_seq_no(parsedResponse)+1)
                self.senderSocket.sendto(json.dumps(ackSegment).encode(), (self.recvHost, self.recvPort))
                currTime = time.time()
                logTime = (currTime - self.startTime) * 1000
                self.logger.create_log_entry('snd', logTime, 'A', get_seq_no(ackSegment), len(get_data(ackSegment)), get_ack_no(ackSegment))

            else:
                print("Handshake failed!!")
                self.senderSocket.close()
                sys.exit()
            
            self.seqNo = get_seq_no(ackSegment)
            self.latestPacketAcked = get_seq_no(ackSegment)
            self.ackNo = get_ack_no(ackSegment)
            self.state = STATE_CONNECTED
            self.windowBase = self.seqNo
            self.latestAckedByte = self.seqNo

    def read_file(self):
        print(f'File is: {self.file}')
        f = open(self.file, 'rb')
        self.fileStat = os.stat(self.file)
        seqNo = self.seqNo
        fileSegment = 0

        while (fileSegment < self.fileStat.st_size):
            data = f.read(self.MSS)
            packet = create_packet(seq_no=seqNo, ack_no=self.ackNo, payload=1, message=data.decode())
            self.fileRead.append(packet)
            seqNo += self.MSS
            fileSegment += self.MSS
        
        ''' DELETE THIS LATER '''
        checkFile = open('result.txt', 'w')
        for packet in self.fileRead:
            checkFile.write(json.dumps(packet))
            checkFile.write('\n')
        
        checkFile.close()
        f.close()

        # Returns bytes read
        return self.fileStat.st_size

    def PLModule(self, packet):
        random.seed(self.seed)
        randNum = random.random()

        if (randNum > self.pDrop):
            self.senderSocket.sendto(packet, (self.recvHost, self.recvPort))
            return 1
        else:
            return 0

    def handle_timeout(self): 
        # Find out which segment to send.
        segmentNo = int((self.latestAckedByte - self.handShakeSeqNo) / self.MSS)
        print(f'The value of segNo is: {segmentNo}')
        print('-----------------------------------')
        print(f'Data: {self.fileRead[segmentNo]}')
        print('------------------------------------')
        if segmentNo < len(self.fileRead):
            PLResult = self.PLModule(json.dumps(self.fileRead[segmentNo]).encode())
            currTime = time.time()
            logTime = (currTime - self.startTime) * 1000
            if PLResult:
                self.logger.create_log_entry('snd', logTime, 'D', get_seq_no(self.fileRead[segmentNo]), len(get_data(self.fileRead[segmentNo])), get_ack_no(self.fileRead[segmentNo]))
                self.retransmissions+=1
            else:
               self.logger.create_log_entry('drop', logTime, 'D', get_seq_no(self.fileRead[segmentNo]), len(get_data(self.fileRead[segmentNo])), get_ack_no(self.fileRead[segmentNo]))
               self.packetsDropped+=1

            threading.Thread(target=self.timer_thread).start()

    def timer_thread(self):
        global LOCK
    
        while self.timerStarted == True:
            with LOCK:
                currTime = time.time()
                print(f'TimerStarted: {self.timerStarted}, currTime: {currTime - self.timerStartTime}')
                if (currTime - self.timerStartTime >= (self.timeout / 1000)):
                    print('Timeout happened')
                    self.timerStarted = False
                    self.handle_timeout()
                LOCK.notify()
            time.sleep(0.1)

    def sender_thread(self):
        global LOCK
        
        #print(f'Value: {self.seqNo}')
        i = 0
        while True:
         #   print('Got inside the while loop')
            with LOCK:
                while (self.seqNo - self.windowBase) <= self.MWS and i < len(self.fileRead):
                    if (self.seqNo + len(self.fileRead[i]['message']) - self.windowBase) > self.MWS:
                        break
                    PLResult = self.PLModule(json.dumps(self.fileRead[i]).encode())
                    self.segmentsCount+=1
                    currTime = time.time()
                    logTime = (currTime - self.startTime) * 1000
                    
                    if PLResult:
                        self.logger.create_log_entry('snd', logTime, 'D', get_seq_no(self.fileRead[i]), len(get_data(self.fileRead[i])), get_ack_no(self.fileRead[i]))
                    else:
                       self.logger.create_log_entry('drop', logTime, 'D', get_seq_no(self.fileRead[i]), len(get_data(self.fileRead[i])), get_ack_no(self.fileRead[i]))
                       self.packetsDropped+=1
                    
                    if self.timerStarted == False:
                        self.timerStarted = True
                        self.timerStartTime = time.time()
                        timerThread = threading.Thread(target=self.timer_thread)
                        timerThread.daemon = True
                        timerThread.start()

                    self.seqNo += len(self.fileRead[i]['message'])
                    i+=1
                
                if self.finishedReceiving == True:
                    break
            
                LOCK.notify()
            time.sleep(0.1)
                        
    def receiver_thread(self):
        global LOCK
        global MAX_PACKET_SIZE
        
        dupAckCount = 0
        while True:
            with LOCK:
                try:
                    print('before receive')
                    try:
                        msg, receiverAddress = self.senderSocket.recvfrom(MAX_PACKET_SIZE)
                    except Exception as e:
                        print(e)
                        
                    print('after receive')
                    parsedResponse = json.loads(msg.decode())
        
                    if is_ack(parsedResponse):
                        self.latestAckedByte = get_ack_no(parsedResponse)
        
                        # Cumulative Ack
                        if get_ack_no(parsedResponse) > self.windowBase:
                            currTime = time.time()
                            logTime = (currTime - self.startTime) * 1000
                            self.logger.create_log_entry('rcv', logTime, 'A', get_seq_no(parsedResponse), len(get_data(parsedResponse)), get_ack_no(parsedResponse))
                            self.windowBase = get_ack_no(parsedResponse)
                            dupAckCount = 1
        
                            # If there are still unacknowledged packets. Reset Timer.
                            # The timer thread will be running already.
                            # We just have to change the timerStartTime
                            if self.seqNo != self.windowBase:
                                self.timerStarted = True
                                self.timerStartTime = time.time()
                                
                        else:
                            dupAckCount+=1
                            self.duplicateAcks+=1
                            if dupAckCount == 3:
                                dupAckCount = 0
                                # Find out which segment to send.
                                segmentNo = int((self.latestAckedByte - self.handShakeSeqNo) / self.MSS)
                                self.PLModule(json.dumps(self.fileRead[segmentNo]).encode())
                                currTime = time.time()
                                logTime = (currTime - self.startTime) * 1000
                                self.logger.create_log_entry('rcv', logTime, 'A', get_seq_no(self.fileRead[segmentNo]), len(get_data(self.fileRead[segmentNo]), get_ack_no(self.fileRead[segmentNo])))

                                if self.timerStarted == False:
                                    self.timerStarted = True
                                    self.timerStartTime = time.time()
                                    
                    if get_ack_no(parsedResponse) >= self.handShakeSeqNo + self.fileStat.st_size:
                        self.finishedReceiving = True
                        break
                        
                    LOCK.notify()
                except Exception as e:
                    print(e)
            time.sleep(0.5)

    def send_data(self):

        self.windowBase = self.seqNo
        currSegment = self.seqNo
        
        # Read the file and store it each segment in a list
        fileSize = self.read_file()


        # Start Sending thread
        senderThread = threading.Thread(target=self.sender_thread)
        senderThread.daemon = True
        senderThread.start()
        
        # Start the Receiver Thread
        receiverThread = threading.Thread(target=self.receiver_thread)
        receiverThread.daemon = True
        receiverThread.start()
        
        # self.sender_thread()        
        senderThread.join()
        receiverThread.join()

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
                self.logger.print_sender_details(self.fileStat.st_size, self.segmentsCount, self.packetsDropped, self.retransmissions, self.duplicateAcks)
                self.logger.close_file()
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
        sender.send_data()

        # Terminate connection
        sender.terminate_connection()

    else:
        print('Arguments not Valid');