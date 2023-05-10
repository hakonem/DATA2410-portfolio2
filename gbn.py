from header import *
import time

init_ack = "ack".encode()
timeout = 0.5  # 500ms timeout
packets = []
base = 1


#!!!!! if window is greater than num_packets set window = num_packets

def GBN(packet, clientSocket, seq_num, ip, port, window, num_packets):
    #initializes window variables (upper and lower window bounds, position of next seq number)
    global base
    if(window > num_packets):
        window = num_packets - 1

    while True:
            print("Vi kom hit")
            print(seq_num)
            print(window + base)
            #	check if the window is full
            if(seq_num<window + base):
                clientSocket.sendto(packet, (ip, port))
                #print(packet)
                print(f'Sent packet with sequence number {seq_num}')
                #		append packet to packets
                # packets.append(packet)
                if((window + base) ==  num_packets + 1):
                    while(ack_seq_num < num_packets):
                        try:
                            clientSocket.sendto(init_ack, (ip, port))
                            #Receive ACK packet from server
                            ack_packet,address = clientSocket.recvfrom(1472)
                            ack_seq_num, ack_ack_num, ack_flags, ack_win = parse_header(ack_packet[:12])
                
                             # Check if received packet is an ACK for the packet just sent
                            if ack_ack_num == ack_seq_num:
                                print(f'Received ACK for packet with sequence number {ack_seq_num}')
                                #Sliding window
                                base = base + 1    
                                #packets.pop(0)
                            else:
                                print(f'Received duplicate ACK for packet with sequence number {ack_seq_num}')
                        except error as e:
                            print(e)
                            # Resend packet if timeout occurs
                            print(f'Timeout occurred. Resending packet with sequence number {seq_num}')
                        if(ack_seq_num == num_packets):
                            break
                    break
                else: break
                       
        
            try:
                clientSocket.sendto(init_ack, (ip, port))
                #Receive ACK packet from server
                ack_packet,address = clientSocket.recvfrom(1472)
                ack_seq_num, ack_ack_num, ack_flags, ack_win = parse_header(ack_packet[:12])
    
                 # Check if received packet is an ACK for the packet just sent
                if ack_ack_num == ack_seq_num:
                    print(f'Received ACK for packet with sequence number {ack_seq_num}')
                    #Sliding window
                    base = base + 1    
                    #packets.pop(0)
                else:
                    print(f'Received duplicate ACK for packet with sequence number {ack_seq_num}')

            except error as e:
                print(e)
                # Resend packet if timeout occurs
                print(f'Timeout occurred. Resending packet with sequence number {seq_num}')
                break
