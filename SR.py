
#Import libraries required for the program to work
import socket
from header import *

#Encoded message that will be sent when we want a ack from server
init_ack = "ack".encode()
#Empty list that will hold all packets in window
packets = []
#Empty list that will hold all seq numbers in window
window_seq = []
#Booleen that will update to True when all ack for the packages have been received
end = False

#Function that sends and recives packages by using the SR method
def SR(packet, clientSocket, seq_num, ip, port, window, num_packets, skipSeq):
    #initializes window variables (upper and lower window bounds, position of next seq number)
    global packets
    global end

    clientSocket.settimeout(0.5)         #Timeout = 500ms

    #Change value of window variable if window is bigger then number of packages
    if(window > num_packets):
        window = num_packets

    while True:

        #	check if the window is full
        if(len(packets) < window):
            #Sends packet to server if skipSeq is False
            if(skipSeq == False):
                clientSocket.sendto(packet, (ip, port))
                #print(packet)
                print(f'Sent packet with sequence number {seq_num}')

            #Append packet to the packets list
            packets.append(packet)
            #Append seq to the window_seq list
            window_seq.append(seq_num)

            #If all packeges has been sent then wait for the last ack packets
            if(seq_num) >=  num_packets:

                #While loop that listen for ack messages after all packages is sent
                while(seq_num <= num_packets + 1):

                    # RECEIPT OF AN ACK
                    try:
                        #Send encrpyted "ack" message to server to aks for ack for a package
                        clientSocket.sendto(init_ack, (ip, port))
                        #Receive ACK packet from server
                        ack_packet,address = clientSocket.recvfrom(1472)
                        #Extracts the 12 byte header and saves the content of header into corresponding variables
                        ack_seq_num, ack_ack_num, ack_flags, ack_win = parse_header(ack_packet[:12])

                        # Check if received packet is an ACK for the first packet in window
                        if ack_ack_num == ack_seq_num:
                            #Print recieved message
                            print(f'Received ACK for packet with sequence number {ack_seq_num}')
                            #Removes first element from the lists
                            packets.pop(0)
                            window_seq.pop(0)
                            
                            #If we got ACK for the last package then set end booleen to True
                            if ack_seq_num == num_packets:
                                end = True
                        #If received ACK is out of order
                        else:
                            #Print out of order message
                            print(f'Received ACK out of order with packet {ack_seq_num}. Resending packeges')
                            #Resends first package from the packets list
                            clientSocket.sendto(packets[0], (ip, port))
                            print(f'Sent packet with sequence number {window_seq[0]}')

                    except socket.timeout:
                        # Resend packet if timeout occurs
                        print(f'Timeout occurred. Resending lost packet in window')
                        #Resends first package from the packets list
                        clientSocket.sendto(packets[0], (ip, port))
                        print(f'Resent packet with sequence number {window_seq[0]}')

                    #If end is TRUE then stop break until we end function
                    if(end):
                        break
                break
            else: break

        # RECEIPT OF AN ACK
        try:
            #Send encrpyted "ack" message to server to aks for ack for a package
            clientSocket.sendto(init_ack, (ip, port))
            #Receive ACK packet from server
            ack_packet,address = clientSocket.recvfrom(1472)
            #Extracts the 12 byte header and saves the content of header into corresponding variables
            ack_seq_num, ack_ack_num, ack_flags, ack_win = parse_header(ack_packet[:12])

            # Check if received packet is an ACK for the packet just sent
            if ack_ack_num == ack_seq_num:
                #Print recieved message
                print(f'Received ACK for packet with sequence number {ack_seq_num}')
                #Removes first element from the lists
                packets.pop(0)
                window_seq.pop(0)
            #If received ACK is out of order
            else:
                #Print out of order message
                print(f'Received ACK out of order with packet {ack_seq_num}. Resending packeges')
                #Resends first package from the packets list
                clientSocket.sendto(packets[0], (ip, port))
                print(f'Sent packet with sequence number {window_seq[0]}')

        #TIMEOUT
        except socket.timeout:
            # Resend packet if timeout occurs
            print(f'Timeout occurred. Resending lost packet in window')
            #Resends first package from the packets list
            clientSocket.sendto(packets[0], (ip, port))
            print(f'Resent packet with sequence number {window_seq[0]}')
    
    #Returns end variable to show that all packages have been sent and recieved
    return end
