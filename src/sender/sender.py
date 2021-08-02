import sys

class Sender:
    def __init__(self, argv):
        self.recvHost = argv[1]
        self.recvPort = argv[2]
        self.file = argv[3]
        self.MWS = argv[4]
        self.MSS = argv[5]
        self.timeout = argv[6]
        self.pDrop = argv[7]
        self.seed = argv[8]

def check_args(args):
    if len(args) != 9:
        return 0
    return 1

if __name__ == "__main__":
    if check_args(sys.argv):
        print('Valid Arguments')
        sender = Sender(sys.argv)
    else:
        print('Arguments not Valid');