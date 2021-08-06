class Logger:
    def __init__(self, logFile):
        self.logFile = logFile
        self.openedFile = None
        self.open_file()

    def open_file(self):
        try:    
            self.openedFile = open(self.logFile, 'w')
        except IOError:
            print(f'Error opening file {self.logFile} for logging')

    def create_log_entry(self, eventType, time, packetType, seqNo, bytesToWrite, ackNo):
        try:
            self.openedFile.write("{}   {:.3f}  {}  {}  {}  {}\n".format(eventType, time,  packetType, seqNo, bytesToWrite, ackNo))
        except IOError:
            print(f'Error writing to file {self.logFile}')

    def print_sender_details(self, dataTransferred, segmentCount, packetsDropped, retransmissions, duplicateAcksCount):
        self.openedFile.write(f'Amount of (original) Data Transferred (in bytes): {dataTransferred}\n')
        self.openedFile.write(f'Number of Data Segments Sent (excluding retransmissions) : {segmentCount}\n')
        self.openedFile.write(f'Number of (all) Packets Dropped (by the PL module): {packetsDropped}\n')
        self.openedFile.write(f'Number of Retransmitted Segments: {retransmissions}\n')
        self.openedFile.write(f'Number of Duplicate Acknowledgements received: {duplicateAcksCount}\n')

    def print_receiver_details(self, dataReceived, dataSegmentsCount, duplicateSegments):
        self.openedFile.write(f'Amount of (original) Data Received (in bytes): {dataReceived}\n')
        self.openedFile.write(f'Number of (original) Data Segments Received: {dataSegmentsCount}\n')
        self.openedFile.write(f'Number of duplicate segments received (if any): {duplicateSegments}\n')

    def close_file(self):
        self.openedFile.close()
