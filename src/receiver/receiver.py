import sys

def check_args(args):
    if len(args) != 3:
        return 0
    return 1

if __name__ == '__main__':
    if check_args(sys.argv):
        print('Valid Receiver')
    else:
        print('Receiver Arguments not Valid')