import socket
from header import *

init_ack = "ack".encode()
packets = []
window_seq = []
base = 1

# SR combined with GBN
def SR(packet, clientSocket, seq_num, ip, port, window, num_packets):
    global base
    global packets
    global window_seq

    clientSocket.settimeout(0.5)         #Timeout = 500ms
    window_size = min(window, num_packets)  # Window size does not exceed number of packets
    receive_buffer = [None] * num_packets  # Store received packets in correct order

    while True:
        # Check if the window is full
        if seq_num < window + base:
            clientSocket.sendto(packet, (ip, port))
            # Print(packet)
            print(f'Sent packet with sequence number {seq_num}')
            # Append packet to packets
            packets.append(packet)
            window_seq.append(seq_num)

            if base == num_packets + 1:
                while True:
                    try:
                        clientSocket.sendto(init_ack, (ip, port))
                        # Receive ACK packet from server
                        ack_packet, address = clientSocket.recvfrom(1472)
                        ack_seq_num, ack_ack_num, ack_flags, ack_win = parse_header(ack_packet[:12])

                        # Check if received packet is an ACK for the packet just sent
                        if ack_ack_num == ack_seq_num:
                            print(f'Received ACK for packet with sequence number {ack_seq_num}')
                            packets.pop(0)
                            window_seq.pop(0)
                            receive_buffer[ack_ack_num - 1] = packet
                            # Slide receive window and output received packets
                            while receive_buffer[0] is not None:
                                print(f'Received packet with sequence number {base}')
                                receive_buffer.pop(0)
                                receive_buffer.append(None)
                                base += 1
                        else:
                            print(f'Received duplicate ACK for packet with sequence number {ack_seq_num}')
                    except socket.timeout:
                        # Resend packet if timeout occurs
                        print(f'Timeout occurred. Resending packets in window')
                        for i in range(len(packets)):
                            clientSocket.sendto(packets[i], (ip, port))
                            # Print(packet)
                            print(f'Sent packet with sequence number {window_seq[i]}')
                            break

            else:
                break

        # RECEIPT OF AN ACK
        try:
            clientSocket.sendto(init_ack, (ip, port))
            ack_packet, address = clientSocket.recvfrom(1472)
            ack_seq_num, ack_ack_num, ack_flags, ack_win = parse_header(ack_packet[:12])

            # Check if received packet is an ACK for the packet just sent
            if ack_ack_num >= base and ack_ack_num < base + window_size:
                print(f'Received ACK for packet with sequence number {ack_seq_num}')
                packets.pop(window_seq.index(ack_ack_num))
                window_seq.remove(ack_ack_num)
                receive_buffer[ack_ack_num - 1] = packet
                # Slide receive window and output received packets
                while receive_buffer[0] is not None:
                    print(f'Received packet with sequence number {base}')
                    receive_buffer.pop(0)
                    receive_buffer.append(None)
                    base += 1
            else:
                print(f'Received duplicate ACK for packet with sequence number {ack_seq_num}')
                raise Exception
        #TIMEOUT
        except socket.timeout:
            # Resend packet if timeout occurs
            print(f'Timeout occurred. Resending packets in window')
            for i in range(len(packets)):
                clientSocket.sendto(packets[i], (ip, port))
                # Print(packet)
                print(f'Sent packet with sequence number {window_seq[i]}')
