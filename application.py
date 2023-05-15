#Import libraries required for the program to work
import argparse
import sys
from socket import *
from header import *
from stop_and_wait import stop_and_wait
from gbn import GBN
from SR import SR


#Create argparse object with program description
parser = argparse.ArgumentParser(description='Run a DRTP file transfer application')
#Create optional arguments and assign flags. Help text describes each argument. Required input types are set, and default values set where necessary.
parser.add_argument('-s', '--server', help='Runs tool in server mode', action='store_true')
parser.add_argument('-c', '--client', help='Runs tool in client mode', action='store_true')
parser.add_argument('-i', '--ip_address', help='Server IP address', type=str, default='127.0.0.1')
parser.add_argument('-p', '--port', help='Server port number', type=int, default=8088)
parser.add_argument('-f', '--file', help='Name of file to transfer', type=str)
parser.add_argument('-r', '--reliable_method', help='Choose a reliable method.Server and client must use the same method', choices=['stop_and_wait', 'GBN', 'SR'], type=str)
parser.add_argument('-t', '--test_case', help='Runs the specified test case', choices=['skip_ack', 'skip_seq'], type=str)


#Run the parser
args = parser.parse_args()


#MAIN FUNCTION
def main():
    #Get global varaible i
    global i

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
            while True:
                # Wait for ACK packet from client
                buffer,address = serverSocket.recvfrom(1472)
                header_from_msg = buffer[:12]
                seq, ack_nr, flags, win = parse_header(header_from_msg)
                #If ACK packet received, connection is established
                if flags == 4:
                    print("Connection established.")
                    break

            #initializes packet variables
            expectedseqnum = 1
            ack_list = []
            buffer_list = []
            prev_seq = 0
            prev_buffer = 0
            skip_ack = True

            # Open a file for writing binary data
            with open('packets.bin', 'wb') as contents:
                # Wait for data packets from client
                while True:
                    buffer,address = serverSocket.recvfrom(1472)
                    test = buffer.decode()

                    # Send ACK packet to Stop-and-Wait client
                    if args.reliable_method == 'stop_and_wait':
                        header_from_msg = buffer[:12]
                        seq, ack_nr, flags, win = parse_header(header_from_msg)
                        contents.write(buffer[12:])
                        
                        ack_nr = seq
                        # the last 4 bits:  S A F R
                        # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                        flags = 4
                        win = 64  # Receiver window advertised by server for flow control, set to 64
                        data = b''
                        ack = create_packet(seq, ack_nr, flags, win, data)
                        if args.test_case == 'skip_ack' and skip_ack:
                            print('Skipping ack...')
                            skip_ack = False
                        else:
                            serverSocket.sendto(ack, address)

                    if args.reliable_method == 'GBN':        
                        # Removes the old elements in the case of a resend cause by timeout
                        if(buffer in buffer_list):
                            for x in range(len(buffer_list)):
                                buffer_list.pop()
                                ack_list.pop()
                          
                    if ("ack" not in test):
                        buffer_list.append(buffer)
                        header_from_msg = buffer[:12]
                        seq, ack_nr, flags, win = parse_header(header_from_msg)
                        ack_list.append(header_from_msg)
                        contents.write(buffer[12:])
                    
                    elif len(ack_list) > 0:
                        if args.reliable_method == 'GBN':
                            #if "ack" in test:
                            seq, ack_nr, flags, win = parse_header(ack_list[0])

                            # Revert increase in "expectedseqnum" if packet is resent
                            if (prev_seq == seq):
                                expectedseqnum = expectedseqnum - 1

                            if args.test_case == 'skip_ack' and skip_ack:
                                print('Skipping ack...')
                                skip_ack = False
                                    
                            #check value of expected seq number against seq number received - IN ORDER
                            elif(seq == expectedseqnum):
                                print ("Received in order", expectedseqnum)

                                # If packet contains data, send ACK
                                if len(buffer_list[0]) > 12:
                                    expectedseqnum = expectedseqnum + 1
                                    ack_nr = seq
                                    #the last 4 bits:  S A F R
                                    # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                                    flags = 4
                                    win = 64                                #Receiver window advertised by server for flow control, set to 64
                                    data = b''
                                    ack = create_packet(seq, ack_nr, flags, win, data)
                                    serverSocket.sendto(ack, address)
                                    prev_seq = seq
                                    prev_buffer = buffer_list[0]
                                    ack_list.pop(0)
                                    buffer_list.pop(0)
                                    
                            else:
                                # default? discard packet and resend ACK for most recently received inorder pkt
                                print("Received out of order", seq)
                                ack_nr = seq - 1
                                #the last 4 bits:  S A F R
                                # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                                flags = 4
                                win = 64                                #Receiver window advertised by server for flow control, set to 64
                                data = b''
                                ack = create_packet(seq, ack_nr, flags, win, data)
                                serverSocket.sendto(ack, address)
                                buffer_list.clear()
                                ack_list.clear()


                        

                        # Send ACK packet to SR client
                        if args.reliable_method == 'SR':
                            #if "ack" in test:
                            seq, ack_nr, flags, win = parse_header(ack_list[0])
                            last_seq, last_ack_nr, last_flags, last_win = parse_header(ack_list[-1])

                            # Revert increase in "expectedseqnum" if packet is resent
                            if (prev_seq == seq):
                                expectedseqnum = expectedseqnum - 1

                            if args.test_case == 'skip_ack' and skip_ack:
                                print('Skipping ack...')
                                skip_ack = False
                                    
                            #check value of expected seq number against seq number received - IN ORDER
                            elif(seq == expectedseqnum):
                                print ("Received in order", expectedseqnum)

                                # If packet contains data, send ACK
                                if len(buffer_list[0]) > 12:
                                    expectedseqnum = expectedseqnum + 1
                                    ack_nr = seq
                                    #the last 4 bits:  S A F R
                                    # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                                    flags = 4
                                    win = 64                                #Receiver window advertised by server for flow control, set to 64
                                    data = b''
                                    ack = create_packet(seq, ack_nr, flags, win, data)
                                    serverSocket.sendto(ack, address)
                                    prev_seq = seq
                                    prev_buffer = buffer_list[0]
                                    
                                    # If seq appears multiple times in list
                                    if buffer_list.count(buffer_list[0]) > 1:
                                        # the removal of all occurrences of a given item using filter() and __ne__
                                        ack_list = list(filter((ack_list[0]).__ne__, ack_list))
                                        buffer_list = list(filter((buffer_list[0]).__ne__, buffer_list))
                                    else:
                                        ack_list.pop(0)
                                        buffer_list.pop(0)

                            #check value of expected seq number against seq number of the newest recieved package
                            elif(last_seq == expectedseqnum):
                                print ("Received in order", expectedseqnum)

                                # If packet contains data, send ACK
                                if len(buffer_list[-1]) > 12:
                                    expectedseqnum = expectedseqnum + 1
                                    ack_nr = last_seq
                                    #the last 4 bits:  S A F R
                                    # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                                    flags = 4
                                    win = 64                                #Receiver window advertised by server for flow control, set to 64
                                    data = b''
                                    ack = create_packet(last_seq, ack_nr, flags, win, data)
                                    serverSocket.sendto(ack, address)
                                    prev_seq = last_seq
                                    prev_buffer = buffer_list[-1]
                                    ack_list.pop(-1)
                                    buffer_list.pop(-1)

                                    
                            else:
                                # default? discard packet and resend ACK for most recently received inorder pkt
                                print("Received out of order", seq)
                                ack_nr = seq - 1
                                #the last 4 bits:  S A F R
                                # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                                flags = 4
                                win = 64                                #Receiver window advertised by server for flow control, set to 64
                                data = b''
                                ack = create_packet(seq, ack_nr, flags, win, data)
                                serverSocket.sendto(ack, address)

                
                    # If FIN packet received, data transmission is complete - send ACK back to client
                    if flags == 2:
                        print('End of transmission')
                        #Flush and close the file
                        contents.flush()
                        contents.close()
                        # Reopen the contents file in read binary mode
                        with open('packets.bin', 'rb') as contents:
                            # Read contents and print to the screen
                            print(contents.read())
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
        except socket.timeout:
            print("Error: Timed out waiting for SYN-ACK")
            clientSocket.close()
            sys.exit()

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
        skip = True
        skipSR = False
        i = 0

        #Loop through packets
        while True:
            print(i)

            if args.test_case == 'skip_seq' and i == 0 and skip == True and args.reliable_method == 'GBN':
                print("Kom meg inn i if settningen")
                i = i + 1
                skip = False

            if args.test_case == 'skip_seq' and i == 13 and skip == True and args.reliable_method == 'SR':
                print("Kom meg inn i SR settningen")
                skipSR = True
                skip = False

            #Calculate start and end points of the data in this packet
            start = i * (packet_size)
            end = min(start + 1460, len(data))
            print(f'start:{start}, end:{end}')
            #Slice the data
            packet_data = data[start:end]
            #Pack the sequence number into the header
            sequence_number = i+1
            acknowledgment_number = 0
            window = 5 # fixed window value
            flags = 0 # we are not going to set any flags when we send a data packet
            i = i + 1

            #msg now holds a packet, including our custom header and data
            msg = create_packet(sequence_number, acknowledgment_number, flags, window, packet_data)

            #RELIABLE METHODS
            #Send file contents to server
            if args.reliable_method == 'stop_and_wait':
                stop_and_wait(msg, clientSocket, sequence_number, args.ip_address, args.port)
                print('Running with stop-and-wait as reliable method')

                if i == num_packets:
                    break

            #Send file contents to server
            elif args.reliable_method == 'GBN':
                resend, end, prev_ack = GBN(msg, clientSocket, sequence_number, args.ip_address, args.port, window, num_packets)
                print('Running with GBN as reliable method')

                if resend and prev_ack > num_packets - window:
                    i = i - ((num_packets - prev_ack) + 2)
                elif resend:
                    i = i - (window + 2)
            
                if end:
                    break

            #Send file contents to server
            elif args.reliable_method == 'SR':
                end, prev_ack = SR(msg, clientSocket, sequence_number, args.ip_address, args.port, window, num_packets, skipSR)
                print('Running with SR as reliable method')

                if skipSR == True:
                    skipSR = False

                if end:
                    print('File transfer completed successfully')
                    break
            
            #Sending file content without reliable method
            else: 
                args.reliable_method = None
                print('Running without reliable method')


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
