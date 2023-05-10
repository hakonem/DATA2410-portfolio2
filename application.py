#Import libraries required for the program to work
import argparse
import sys
import time
from socket import *
from header import *
from stop_and_wait import stop_and_wait
from gbn import GBN


#Create argparse object with program description
parser = argparse.ArgumentParser(description='Run simpleperf network performance tool')
#Create optional arguments and assign flags. Help text describes each argument. Required input types are set, and default values set where necessary.
parser.add_argument('-s', '--server', help='Runs tool in server mode', action='store_true')
parser.add_argument('-c', '--client', help='Runs tool in client mode', action='store_true')
parser.add_argument('-i', '--ip_address', help='Server IP address', type=str, default='127.0.0.1')
parser.add_argument('-p', '--port', help='Server port number', type=int, default=8088)
parser.add_argument('-f', '--file', help='Name of file to transfer', type=str)
parser.add_argument('-r', '--reliable_method', help='Reliable method: stop_and_wait, GBN or SR. Server and client must use the same method', type=str)
parser.add_argument('-t', '--test_case', help='Runs the specified test case', type=str)


#Run the parser
args = parser.parse_args()


#MAIN FUNCTION
def main():
    #ERROR HANDLING IF NEITHER/BOTH MODES SELECTED
    if (not args.client and not args.server) or (args.client and args.server):
        sys.exit('Error: you must run either in server or client mode')
    

    #Run server first
    elif args.server:
        serverSocket = socket(AF_INET, SOCK_DGRAM)              #Prepare a UDP server socket
        try:
            serverSocket.bind((args.ip_address, args.port))
            #EXCEPTION HANDLING
        except:
            print('Bind failed. Error: ')                       #Print error message and terminate program if socket binding fails
            sys.exit()
        print(f'Ready to receive...')                           #Print message when socket ready to receive

        while True:
            #Wait for SYN packet from client
            buffer,address = serverSocket.recvfrom(1472)
            header_from_msg = buffer[:12]
            seq, ack_nr, flags, win = parse_header(header_from_msg)
            print(f'seq={seq}, ack={ack_nr}, flags={flags}, receiver-window={win}')
            #If SYN packet received, send SYN-ACK packet to client
            if flags == 8:
                seq = 0
                ack_nr = 0
                #the last 4 bits:  S A F R
                # 1 1 0 0  SYN flag set, and the decimal equivalent is 12
                flags = 12
                win = 64                                #Receiver window advertised by server for flow control, set to 64
                data = b''
                synack = create_packet(seq, ack_nr, flags, win, data)
                serverSocket.sendto(synack, address)

            # Wait for ACK packet from client
            buffer,address = serverSocket.recvfrom(1472)
            header_from_msg = buffer[:12]
            seq, ack_nr, flags, win = parse_header(header_from_msg)
            #If ACK packet received, connection is established
            if flags == 4:
                print("Connection established.")

            #initializes packet variables 
            expectedseqnum = 1
            #ACK=1
            ack_list = []
            buffer_list = []

            # Wait for data packets from client
            while True:
                    buffer,address = serverSocket.recvfrom(1472)
                    test = buffer.decode()
                    if ("ack" not in test):
                        buffer_list.append(buffer)
                        header_from_msg = buffer[:12]
                        final_seq, final_ack_nr, final_flags, final_win = parse_header(header_from_msg)
                        ack_list.append(header_from_msg)


                    # If FIN packet received, data transmission is complete - send ACK back to client
                    if final_flags == 2:
                        print('End of transmission')
                        seq = 0
                        ack_nr = 0
                        #the last 4 bits:  S A F R
                        # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                        flags = 4
                        win = 0
                        data = b''
                        ack = create_packet(seq, ack_nr, flags, win, data)
                        serverSocket.sendto(ack, address)
                        # Close socket after all data has been sent and received
                        print('Server connection closed')
                        break

                    if("ack" in test):
                        print(ack_list[0])
                        seq, ack_nr, flags, win = parse_header(ack_list[0])
                        
                        #check value of expected seq number against seq number received - IN ORDER 
                        if(seq == expectedseqnum):
                            print ("Received in order", expectedseqnum)
                            # If packet contains data, send ACK
                            if len(buffer_list[0]) > 12:
                                #print(f'seq nr: {seq}, {buffer}')
                                expectedseqnum = expectedseqnum + 1
                                ack_nr = seq
                                #the last 4 bits:  S A F R
                                # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                                flags = 4
                                win = 64                                #Receiver window advertised by server for flow control, set to 64
                                data = b''
                                ack = create_packet(seq, ack_nr, flags, win, data)
                                serverSocket.sendto(ack, address)
                                ack_list.pop(0)
                                buffer_list.pop(0)
                        else:
                            # default? discard packet and resend ACK for most recently received inorder pkt 
                            print("Recieved out of order", seq)
                            ack_nr = seq - 1
                            #the last 4 bits:  S A F R
                            # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                            flags = 4
                            win = 64                                #Receiver window advertised by server for flow control, set to 64
                            data = b''
                            ack = create_packet(seq, ack_nr, flags, win, data)
                            serverSocket.sendto(ack, address)
                            print ("Ack", expectedseqnum)
                            buffer_list.clear()
                            ack_list.clear()

            serverSocket.close()
            sys.exit()


    #Then run client
    else:
        clientSocket = socket(AF_INET, SOCK_DGRAM)              #Prepare a UDP server socket
        #Client initiates three-way handshake with server to establish reliable connection
        #Send SYN packet to server
        seq = 0
        ack_nr = 0
        #the last 4 bits:  S A F R
        # 1 0 0 0  SYN flag set, and the decimal equivalent is 8
        flags = 8
        win = 0
        data = b''
        syn = create_packet(seq, ack_nr, flags, win, data)
        clientSocket.sendto(syn, (args.ip_address, args.port))

        #Wait for SYN-ACK packet from server
        #Throw error if SYN-ACK doesn't arrive before timeout
        try:
            clientSocket.settimeout(0.5)                     #Timeout = 500ms
            buffer,address = clientSocket.recvfrom(1472)
            header_from_msg = buffer[:12]
            seq, ack_nr, flags, win = parse_header(header_from_msg)
            print(f'flags: {flags}')
        except socket.timeout:
            print("Error: Timed out waiting for SYN-ACK")
            clientSocket.close()
            sys.exit()

        # Test case: skip ACK
        if args.test_case == "skip_ack":
            # Not sending ACK packet to the server
            print('Skipping ACK')
            pass
            time.sleep(2)
            # Retransmitting ACK packet
            print('Retransmitting')
            ack = create_packet(0, 0, 4, 0, b'')
            clientSocket.sendto(ack, (args.ip_address, args.port))

        else:
            # Send ACK packet to server
            seq = 0
            ack_nr = 0
            #the last 4 bits:  S A F R
            # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
            flags = 4
            win = 0
            data = b''
            ack = create_packet(seq, ack_nr, flags, win, data)
            clientSocket.sendto(ack, (args.ip_address, args.port))

        #Open the file and read contents to a buffer
        with open(args.file, 'rb') as f:
            data = bytearray(f.read())
        print(f'app data for size ={len(data)}')
        packet_size = 1460                                              #Set packet size (without header)
        num_packets = (len(data) + packet_size - 1) // packet_size      #Calculate number of packets
        print(f'number of packets={num_packets}')

        #Loop through packets
        for i in range(num_packets):
            #Calculate start and end points of the data in this packet
            start = i * (packet_size)
            end = min(start + 1460, len(data))
            print(f'start:{start}, end:{end}')
            #Slice the data
            packet_data = data[start:end]
            #Pack the sequence number into the header
            sequence_number = i+1
            print(sequence_number)
            acknowledgment_number = 0
            window = 3 # window value should always be sent from the receiver-side
            flags = 0 # we are not going to set any flags when we send a data packet

            #msg now holds a packet, including our custom header and data
            msg = create_packet(sequence_number, acknowledgment_number, flags, window, packet_data)
            if not args.reliable_method:
                print(f'seq nr: {sequence_number}, msg: {msg}')

            #RELIABLE METHODS
            #Send file contents to server
            if args.reliable_method == 'stop_and_wait':
                stop_and_wait(msg, clientSocket, sequence_number, args.ip_address, args.port)
                print('Running with stop-and-wait as reliable method')
            
            #Send file contents to server
            if args.reliable_method == 'GBN':
                GBN(msg, clientSocket, sequence_number, args.ip_address, args.port, window, num_packets)




        # When data transmission is complete, send FIN packet to server
        seq = 0
        ack_nr = 0
        #the last 4 bits:  S A F R
        # 0 0 1 0  FIN flag set, and the decimal equivalent is 2
        flags = 2
        win = 0
        data = b''
        fin = create_packet(seq, ack_nr, flags, win, data)
        clientSocket.sendto(fin, (args.ip_address, args.port))

        # Wait for ACK packet from server
        buffer,address = clientSocket.recvfrom(1472)
        header_from_msg = buffer[:12]
        seq, ack_nr, flags, win = parse_header(header_from_msg)
        if flags == 4:
            # Close socket after all data has been sent and received
            print('Client connection closed')
            clientSocket.close()


if __name__ == '__main__':
    main()                                  #Execution of module begins with main()
