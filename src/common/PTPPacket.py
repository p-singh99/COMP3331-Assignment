class PTPPacket:
    def __init__(self, senderPort, receiverPort, seqNum, ackNum, data):
        self.senderPort = senderPort
        self.receiverPort = receiverPort
        self.seqNum = seqNum
        self.ackNum = ackNum
        self.data = data