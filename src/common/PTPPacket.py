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