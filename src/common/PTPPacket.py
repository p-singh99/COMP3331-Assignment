def create_packet(syn=0, ack=0, fin=0, payload=0, seq_no=0, ack_no=0, message=""):
    packet = {
        "syn": syn,
        "ack": ack,
        "fin": fin,
        "payload": payload,
        "seq_no": seq_no,
        "ack_no": ack_no,
        "message": message
    }
    return packet

def is_ack(packet):
    return packet['ack'] == 1

def is_syn(packet):
    return packet['syn'] == 1

def is_fin(packet):
    return packet['fin'] == 1

def is_data(packet):
    return packet['payload'] == 1

def get_ack_no(packet):
    return packet['ack_no']

def get_seq_no(packet):
    return packet['seq_no']