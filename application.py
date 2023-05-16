#Import libraries required for the program to work
import argparse
import sys
from socket import *
import time
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
            #Wait for SYN packet from client and saves the packet in the buffer variable and address in the address varaible
            buffer,address = serverSocket.recvfrom(1472)
            #Extracts the 12 byte header from the buffer and saves in in variabal
            header_from_msg = buffer[:12]
            #Saves the content of header into corresponding variables
            seq, ack_nr, flags, win = parse_header(header_from_msg)
            #Prints out the varaible values
            print(f'seq={seq}, ack={ack_nr}, flags={flags}, receiver-window={win}')
            #If SYN packet received (1000),  send SYN-ACK packet (1100) to client 
            if flags == 8: 
                #Gives seq variable a unrelevant value   
                seq = 0 
                #Gives ack_nr varaible a unrelevant value
                ack_nr = 0
                #the last 4 bits:  S A F R
                # 1 1 0 0  SYN flag set, and the decimal equivalent is 12
                flags = 12
                #Receiver window advertised by server for flow control, set to 64
                win = 64  
                #Set data variable to an empty byte string               
                data = b''
                #Creates the SYN_ACK package and saves it in synack variable
                synack = create_packet(seq, ack_nr, flags, win, data)
                #Send SYN_ACK package to the connected client
                serverSocket.sendto(synack, address)
            while True:
                #Wait for ACK packet from client and saves the packet in the buffer variable and address in the address varaible
                buffer,address = serverSocket.recvfrom(1472)
                #Extracts the 12 byte header from the buffer and saves in in variabal
                header_from_msg = buffer[:12]
                #Saves the content of header into corresponding variables
                seq, ack_nr, flags, win = parse_header(header_from_msg)
                #If ACK packet received (0100), connection is established
                if flags == 4:
                    #Prints connected message
                    print("Connection established.")
                    break

            #initializes packet variables
            expectedseqnum = 1    #Variable that keeps track of seq for next expected package from client
            ack_list = []         #Empty list that will hold the headers from the received packages
            buffer_list = []      #Empty list that will hold the buffer variables from the received packages
            prev_seq = 0          #Variable that keep seq nr form received package
            skip_ack = True       #Variable that is True if we want to skip sending an ack message to client

            # Open a file for writing binary data
            with open('packets.bin', 'wb') as contents:
                while True:
                    # Wait for data packets from client and saves the packet in the buffer variable and address in the address varaible
                    buffer,address = serverSocket.recvfrom(1472)
                    #Varaible that will hold the decoded value of the buffer variable
                    test = buffer.decode()

                    # Send ACK packet to Stop-and-Wait client
                    if args.reliable_method == 'stop_and_wait':
                        #Extracts the 12 byte header from the buffer and saves in in variabal
                        header_from_msg = buffer[:12]
                        #Saves the content of header into corresponding variables
                        seq, ack_nr, flags, win = parse_header(header_from_msg)
                        #Writes the content of buffer (without header) to file
                        contents.write(buffer[12:])
                        
                        #Gives ack_nr the value of the seq variable
                        ack_nr = seq
                        # the last 4 bits:  S A F R
                        # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                        flags = 4
                        # Receiver window advertised by server for flow control, set to 64
                        win = 64  
                        #Set data variable to an empty byte string
                        data = b''
                        #Creates the ACK package and saves it in ack variable
                        ack = create_packet(seq, ack_nr, flags, win, data)
                        #If sentence that skips ack message if test_case agurment == 'skip_ack' and skip_ack booleen is True
                        if args.test_case == 'skip_ack' and skip_ack:
                            #Print skipping ack message
                            print('Skipping ack...')
                            #Set skip_ack booleen to False 
                            skip_ack = False
                        else:
                            #Send ACK package to the connected client
                            serverSocket.sendto(ack, address)
                    
                    #if the test variable contain the "ack" message or not      
                    if "ack" not in test:     
                        # If resent packet has already been received and is in the buffer list
                        if(buffer in buffer_list):
                            pass
                        else: 
                            #Add current value of buffer to buffer_list
                            buffer_list.append(buffer)
                            #Extracts the 12 byte header from the buffer and saves in in variabal
                            header_from_msg = buffer[:12]
                            #Saves the content of header into corresponding variables
                            seq, ack_nr, flags, win = parse_header(header_from_msg)
                            #Add current header to ack_list
                            ack_list.append(header_from_msg)
                            #Writes the content of buffer (without header) to file
                            contents.write(buffer[12:])
                    
                    elif len(ack_list) > 0:
                        #if reliable method == 'GBN' handle packages received and ack response with GBN method
                        if args.reliable_method == 'GBN':
                            #Saves the content of the first element in ack_list into corresponding variables
                            seq, ack_nr, flags, win = parse_header(ack_list[0])

                            # Revert increase in "expectedseqnum" if packet is resent
                            if (prev_seq == seq):
                                expectedseqnum = expectedseqnum - 1

                            #If sentence that skips ack message if test_case agurment == 'skip_ack' and skip_ack booleen is True
                            if args.test_case == 'skip_ack' and skip_ack:
                                #Print skipping ack message
                                print('Skipping ack...')
                                #Set skip_ack booleen to False
                                skip_ack = False

                            #check value of expected seq number against seq number received - IN ORDER
                            elif(seq == expectedseqnum):
                                print ("Received in order", expectedseqnum)

                                # If packet (first buffer in buffer_list) contains data, send ACK
                                if len(buffer_list[0]) > 12:
                                    #Increase expectedseqnum variable by 1
                                    expectedseqnum = expectedseqnum + 1
                                    #Gives ack_nr the value of the seq varible
                                    ack_nr = seq
                                    #the last 4 bits:  S A F R
                                    # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                                    flags = 4
                                    #Receiver window advertised by server for flow control, set to 64
                                    win = 64     
                                    #Set data variable to an empty byte string                           
                                    data = b''
                                    #Creates the ACK package and saves it in ack variable
                                    ack = create_packet(seq, ack_nr, flags, win, data)
                                    #Send ACK package to the connected client
                                    serverSocket.sendto(ack, address)
                                    #Updates value of prev_seq
                                    prev_seq = seq
                                    #Removes the first element from the lists
                                    ack_list.pop(0)
                                    buffer_list.pop(0)
                            #Packet recieved out of order. Send a NACK and delete all elements from the lists        
                            else:
                                print("Received out of order", seq)
                                #Gives ack_nr varaible a unrelevant value
                                ack_nr = 0
                                #the last 4 bits:  S A F R
                                # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                                flags = 4
                                #Receiver window advertised by server for flow control, set to 64
                                win = 64    
                                #Set data variable to an empty byte string                            
                                data = b''
                                #Creates the ACK package and saves it in ack variable
                                ack = create_packet(seq, ack_nr, flags, win, data)
                                #Send ACK package to the connected client
                                serverSocket.sendto(ack, address)
                                #Delete all elements form the lists
                                buffer_list.clear()
                                ack_list.clear()                      


                        

                        #if reliable method == 'SR' handle packages received and ack response with GBN method
                        if args.reliable_method == 'SR':
                            #Saves the content of the first element in ack_list into corresponding variables
                            seq, ack_nr, flags, win = parse_header(ack_list[0])
                            #Saves the content of the last element in ack_list into corresponding variables
                            last_seq, last_ack_nr, last_flags, last_win = parse_header(ack_list[-1])

                            # Revert increase in "expectedseqnum" if packet is resent
                            if (prev_seq == seq):
                                expectedseqnum = expectedseqnum - 1

                            #If sentence that skips ack message if test_case agurment == 'skip_ack' and skip_ack booleen is True    
                            if args.test_case == 'skip_ack' and skip_ack:
                                #Print skipping ack message
                                print('Skipping ack...')
                                #Set skip_ack booleen to False
                                skip_ack = False
                                    
                            #check value of expected seq number against seq number received - IN ORDER
                            elif(seq == expectedseqnum):
                                print ("Received in order", expectedseqnum)

                                # If packet (first buffer in buffer_list) contains data, send ACK
                                if len(buffer_list[0]) > 12:
                                    #Increase expectedseqnum variable by 1
                                    expectedseqnum = expectedseqnum + 1
                                    #Gives ack_nr the value of the seq variable
                                    ack_nr = seq
                                    #the last 4 bits:  S A F R
                                    # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                                    flags = 4
                                    #Receiver window advertised by server for flow control, set to 64
                                    win = 64     
                                    #Set data variable to an empty byte string                            
                                    data = b''
                                    #Creates the ACK package and saves it in ack variable
                                    ack = create_packet(seq, ack_nr, flags, win, data)
                                    #Send ACK package to the connected client
                                    serverSocket.sendto(ack, address)
                                    #Updates value of prev_seq
                                    prev_seq = seq
                                    
                                    # If seq from the first element in buffer_list appears multiple times in list
                                    if buffer_list.count(buffer_list[0]) > 1:
                                        # the removal of all occurrences of a given item using filter() and __ne__
                                        ack_list = list(filter((ack_list[0]).__ne__, ack_list))
                                        buffer_list = list(filter((buffer_list[0]).__ne__, buffer_list))
                                    else:
                                        #Removes the first element from the lists
                                        ack_list.pop(0)
                                        buffer_list.pop(0)

                            #check value of expected seq number against seq number of the newest recieved package
                            elif(last_seq == expectedseqnum):
                                print ("Received in order", expectedseqnum)

                                # If packet (last buffer in buffer_list) contains data, send ACK
                                if len(buffer_list[-1]) > 12:
                                    #Increase expectedseqnum variable by 1
                                    expectedseqnum = expectedseqnum + 1
                                    #Gives ack_nr the value of last_seq varaible
                                    ack_nr = last_seq
                                    #the last 4 bits:  S A F R
                                    # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                                    flags = 4
                                    #Receiver window advertised by server for flow control, set to 64
                                    win = 64   
                                    #Set data variable to an empty byte string                             
                                    data = b''
                                    #Creates the ACK package and saves it in ack variable
                                    ack = create_packet(last_seq, ack_nr, flags, win, data)
                                    #Send ACK package to the connected client
                                    serverSocket.sendto(ack, address)
                                    #Updates value of prev_seq
                                    prev_seq = last_seq
                                    #Removes the last element from the lists
                                    ack_list.pop(-1)
                                    buffer_list.pop(-1)

                            #Packet recieved out of order. Send a NACK and delete all elements from the lists         
                            else:
                                print("Received out of order", seq)
                                #Gives ack_nr varaible a unrelevant value
                                ack_nr = 0
                                #the last 4 bits:  S A F R
                                # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                                flags = 4
                                #Receiver window advertised by server for flow control, set to 64
                                win = 64   
                                #Set data variable to an empty byte string                              
                                data = b''
                                #Creates the ACK package and saves it in ack variable
                                ack = create_packet(seq, ack_nr, flags, win, data)
                                #Send ACK package to the connected client
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
                            c = contents.read()
                            print(c)
                            print(f'Bytes received: {len(c)}')
                        #Gives seq varaible a unrelevant value
                        seq = 0
                        #Gives ack_nr varaible a unrelevant value
                        ack_nr = 0
                        #the last 4 bits:  S A F R
                        # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
                        flags = 4
                        #Receiver window advertised by server for flow control, set to 64
                        win = 0
                        #Set data variable to an empty byte string 
                        data = b''
                        #Creates the ACK package and saves it in ack variable
                        ack = create_packet(seq, ack_nr, flags, win, data)
                        #Send ACK package to the connected client
                        serverSocket.sendto(ack, address)
                        # Close socket after all data has been sent and received
                        print('Server connection closed')
                        break

            #Closes tthe server socket        
            serverSocket.close()
            #Exits program
            sys.exit()


    #Then run client
    else:
        clientSocket = socket(AF_INET, SOCK_DGRAM)              #Prepare a UDP server socket
        #Client initiates three-way handshake with server to establish reliable connection
        #Send SYN packet to server
        #Gives seq the value of the seq varible
        seq = 0
        #Gives ack_nr the value of the seq varible
        ack_nr = 0
        #the last 4 bits:  S A F R
        # 1 0 0 0  SYN flag set, and the decimal equivalent is 8
        flags = 8
        #Receiver window advertised by server for flow control, set to 64
        win = 0
        #Set data variable to an empty byte string
        data = b''
        #Creates the SYN package and saves it in ack variable
        syn = create_packet(seq, ack_nr, flags, win, data)
        #Send SYN package to the server
        clientSocket.sendto(syn, (args.ip_address, args.port))

        #Wait for SYN-ACK packet from server
        #Throw error if SYN-ACK doesn't arrive before timeout
        try:
            #Timeout = 500ms
            clientSocket.settimeout(0.5)                     
            # Wait for data packets from server and saves the packet in the buffer variable and address in the address varaible
            buffer,address = clientSocket.recvfrom(1472)
            #Extracts the 12 byte header from the buffer and saves in in variabal
            header_from_msg = buffer[:12]
            #Saves the content of header into corresponding variables
            seq, ack_nr, flags, win = parse_header(header_from_msg)
        except socket.timeout:
            #Print timeout error message
            print("Error: Timed out waiting for SYN-ACK")
            #Closes client socket
            clientSocket.close()
            #Exits program
            sys.exit()

        # Send ACK packet to server
        #Gives seq the value of the seq varible
        seq = 0
        #Gives ack_nr the value of the seq varible
        ack_nr = 0
        #the last 4 bits:  S A F R
        # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
        flags = 4
        #Receiver window advertised by server for flow control, set to 64
        win = 0
        #Set data variable to an empty byte string
        data = b''
        #Creates the ACK package and saves it in ack variable
        ack = create_packet(seq, ack_nr, flags, win, data)
        #Send ACK package to the server
        clientSocket.sendto(ack, (args.ip_address, args.port))

        #Open the file and read contents to a buffer
        with open(args.file, 'rb') as f:
            data = bytearray(f.read())
        print(f'app data for size ={len(data)}')
        packet_size = 1460                                              #Set packet size (without header)
        num_packets = (len(data) + packet_size - 1) // packet_size      #Calculate number of packets
        print(f'number of packets={num_packets}')
        #Set skip variable, used for the skip_seq test, to True
        skip = True
        #Set skipSeq variable, used for the skip_seq test, to Flase
        skipSeq = False
        #Set global i variable to 0
        i = 0

        #Loop through packets
        while True:

            #If sentence that gives skipSeq and Seq boolens right value when i is the chosen value
            # if GBN is run with the skip_seq test
            if args.test_case == 'skip_seq' and i == 8 and skip == True and args.reliable_method == 'GBN':
                skipSeq = True
                skip = False

            #If sentence that gives skipSeq and Seq boolens right value when i is the chosen value
            # if SR is run with the skip_seq test
            if args.test_case == 'skip_seq' and i == 12 and skip == True and args.reliable_method == 'SR':
                skipSeq = True
                skip = False

            #Calculate start and end points of the data in this packet
            start = i * (packet_size)
            end = min(start + 1460, len(data))
            print(f'start:{start}, end:{end}')
            #Slice the data
            packet_data = data[start:end]
            #Pack the sequence number into the header
            #Set sequence_number
            sequence_number = i+1
            #Set acknowledgment number
            acknowledgment_number = 0
            flags = 0 # we are not going to set any flags when we send a data packet
            #Increse i varaible by 1
            i = i + 1
            #Set window size
            window = 5

            #msg now holds a packet, including our custom header and data
            msg = create_packet(sequence_number, acknowledgment_number, flags, window, packet_data)

            #RELIABLE METHODS
            #Send file contents to server
            start_time = time.time()

            #Run stop_and_wait function from stop_and_wait.py if reliable method is 'stop_and_wait'
            if args.reliable_method == 'stop_and_wait':
                stop_and_wait(msg, clientSocket, sequence_number, args.ip_address, args.port)
                print('Running with stop-and-wait as reliable method')

                if i == num_packets:
                    break

            #Run GBN function from GBN.py if reliable method is 'GBN'
            elif args.reliable_method == 'GBN':
                end = GBN(msg, clientSocket, sequence_number, args.ip_address, args.port, window, num_packets, skipSeq)
                print('Running with GBN as reliable method')

                #Changes skipSeq value to False if it has True value
                if skipSeq == True:
                    skipSeq = False
                
                #If end is True then break
                if end:
                    print('File transfer completed successfully')
                    break

            #Run SR from SR.py if reliable method is 'SR'
            elif args.reliable_method == 'SR':
                end = SR(msg, clientSocket, sequence_number, args.ip_address, args.port, window, num_packets, skipSeq)
                print('Running with SR as reliable method')

                #Changes skipSeq value to False if it has True value
                if skipSeq == True:
                    skipSeq = False

                #If end is True then break
                if end:
                    print('File transfer completed successfully')
                    break
            
            #Sending file content without reliable method
            else: 
                args.reliable_method = None
                print('Running without reliable method')


        # When data transmission is complete, send FIN packet to server
        #Gives seq variable a unrelevant value 
        seq = 0
        #Gives ack_nr varaible a unrelevant value
        ack_nr = 0
        #the last 4 bits:  S A F R
        # 0 0 1 0  FIN flag set, and the decimal equivalent is 2
        flags = 2
        #Receiver window advertised by server for flow control, set to 64
        win = 0
        #Set data variable to an empty byte string 
        data = b''
        #Creates the FIN package and saves it in synack variable
        fin = create_packet(seq, ack_nr, flags, win, data)
        #Send FIN package to the connected client
        clientSocket.sendto(fin, (args.ip_address, args.port))

        #Wait for ACK packet from client and saves the packet in the buffer variable and address in the address varaible
        buffer,address = clientSocket.recvfrom(1472)
        #Extracts the 12 byte header from the buffer and saves in in variabal
        header_from_msg = buffer[:12]
        #Saves the content of header into corresponding variables
        seq, ack_nr, flags, win = parse_header(header_from_msg)
        #If ACK packet received (0100), connection is established
        if flags == 4:
            #Set stop_time
            stop_time = time.time()
            #Calculates and prints total duration
            print(f'Total duration: {round((stop_time - start_time)*1000, 3)} ms')
            # Close socket after all data has been sent and received
            print('Client connection closed')
            #Closes the client socket
            clientSocket.close()        

#Calls main function is file is run directly
if __name__ == '__main__':
    main()                                  
