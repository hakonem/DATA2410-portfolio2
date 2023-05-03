from header import *

#Stop and wait protocol
def stop_and_wait(packet, address, clientSocket, seq_num):
    #Initialize variables
    ack_received = False
    packet_sent = False
    timeout = 0.5  # 500ms timeout

    #Loop until ACK received
    while not ack_received:
        #If packet not sent, send packet
        if not packet_sent:
            #Send packet to address
            clientSocket.sendto(packet, address)
            print(f'Sent packet with sequence number {seq_num}')
            packet_sent = True

        try:
            #Receive ACK packet from server
            ack_packet, server_address = clientSocket.recvfrom(1472)
            ack_seq_num, ack_ack_num, ack_flags, ack_win = parse_header(ack_packet[:12])

            # Check if received packet is an ACK for the packet just sent
            if ack_ack_num == seq_num + len(packet[12:]):
                print(f'Received ACK for packet with sequence number {seq_num}')
                ack_received = True
            elif ack_ack_num == seq_num:
                print(f'Received duplicate ACK for packet with sequence number {seq_num}')

        except timeout:
            # Resend packet if timeout occurs
            print(f'Timeout occurred. Resending packet with sequence number {seq_num}')
            packet_sent = False

    #Return True if packet was successfully sent and acknowledged, False otherwise
    return ack_received
