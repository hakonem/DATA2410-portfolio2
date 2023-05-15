
import socket
from header import *

init_ack = "ack".encode()
init_reorder = "reorder".encode()
packets = []
window_seq = []
end = False
prev_ack = 0


#!!!!! if window is greater than num_packets set window = num_packets

def SR(packet, clientSocket, seq_num, ip, port, window, num_packets, skipSeq):
    #initializes window variables (upper and lower window bounds, position of next seq number)
    global packets
    global end
    global prev_ack

    clientSocket.settimeout(0.5)         #Timeout = 500ms

    if(window > num_packets):
        window = num_packets

    while True:

        #	check if the window is full
        if(len(packets) < window):
            if(skipSeq == False):
                clientSocket.sendto(packet, (ip, port))
                #print(packet)
                print(f'Sent packet with sequence number {seq_num}')

            #		append packet to packets
            packets.append(packet)
            window_seq.append(seq_num)

            #If all packeges has been sent then wait for the last ack packets
            if(seq_num) >=  num_packets:

                while(seq_num <= num_packets + 1):

                    try:
                        clientSocket.sendto(init_ack, (ip, port))
                        #Receive ACK packet from server
                        ack_packet,address = clientSocket.recvfrom(1472)
                        ack_seq_num, ack_ack_num, ack_flags, ack_win = parse_header(ack_packet[:12])

                        # Check if received packet is an ACK for the packet just sent
                        if ack_ack_num == ack_seq_num:
                            print(f'Received ACK for packet with sequence number {ack_seq_num}')
                            packets.pop(0)
                            window_seq.pop(0)
                            prev_ack = ack_ack_num

                            if ack_seq_num == num_packets:
                                end = True
                        else:
                            print(f'Received ACK out of order with packet {ack_seq_num}. Resending packeges')
                            clientSocket.sendto(packets[0], (ip, port))
                            #print(packet)
                            print(f'Sent packet with sequence number {window_seq[0]}')

                    except socket.timeout:
                        # Resend packet if timeout occurs
                        print(f'Timeout occurred. Resending lost packet in window')
                        clientSocket.sendto(packets[0], (ip, port))
                        #print(packet)
                        print(f'Resent packet with sequence number {window_seq[0]}')
 
                    if(end):
                        break
                break
            else: break

        # RECEIPT OF AN ACK
        try:
            clientSocket.sendto(init_ack, (ip, port))
            #Receive ACK packet from server
            ack_packet,address = clientSocket.recvfrom(1472)
            ack_seq_num, ack_ack_num, ack_flags, ack_win = parse_header(ack_packet[:12])

            # Check if received packet is an ACK for the packet just sent
            if ack_ack_num == ack_seq_num:
                print(f'Received ACK for packet with sequence number {ack_seq_num}')
                packets.pop(0)
                window_seq.pop(0)
            else:
                print(f'Received ACK out of order with packet {ack_seq_num}. Resending packeges')
                clientSocket.sendto(packets[0], (ip, port))
                #print(packet)
                print(f'Sent packet with sequence number {window_seq[0]}')

        #TIMEOUT
        except socket.timeout:

            # Resend packet if timeout occurs
            print(f'Timeout occurred. Resending lost packet in window')
            clientSocket.sendto(packets[0], (ip, port))
            #print(packet)
            print(f'Resent packet with sequence number {window_seq[0]}')

    return end, prev_ack
