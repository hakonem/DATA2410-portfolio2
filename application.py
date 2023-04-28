#Import libraries required for the program to work
import argparse
import sys
from socket import *
from header import *


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
        serverSocket = socket(AF_INET, SOCK_DGRAM)             #Prepare a UDP (SOCK_DGRAM) server socket using IPv4 (AF_INET)
        try:
            serverSocket.bind((args.ip_address, args.port))                       
        #EXCEPTION HANDLING
        except:
            print('Bind failed. Error: ')                       #Print error message and terminate program if socket binding fails 
            sys.exit()
        print(f'Ready to receive...')                           #Print message when socket ready to receive


        #Wait for SYN packet from client
        while True:
            buffer,address = serverSocket.recvfrom(1472)
            print(buffer)
            header_from_msg = buffer[:12]
            seq, ack, flags, win = parse_header(header_from_msg)
            print(f'seq={seq}, ack={ack}, flags={flags}, recevier-window={win}')
            syn, ack, fin = parse_flags(flags)
            print(f'syn_flag = {syn}, fin_flag={fin}, and ack_flag={ack}')

            
            if syn:
                #Send SYN-ACK packet to client
                seq = 0
                ack = seq + 1
                #the last 4 bits:  S A F R
                # 1 1 0 0  SYN flag set, and the decimal equivalent is 12
                flags = 12
                win = 64        #Receiver window advertised by server for flow control, set to 64
                data = b''
                synack = create_packet(seq, ack, flags, win, data)
                serverSocket.sendto(synack, address)

                # Wait for ACK packet from client
                buffer,address = serverSocket.recvfrom(1472)
                header_from_msg = buffer[:12]
                seq, ack, flags, win = parse_header(header_from_msg)
                syn, ack, fin = parse_flags(flags)
                if ack == seq + 1:
                    print("Connection established.")
                    break
            
            # Wait for data packets from client
            while True:
                buffer,address = serverSocket.recvfrom(1472)
                header_from_msg = buffer[:12]
                seq, ack, flags, win = parse_header(header_from_msg)
                syn, ack, fin = parse_flags(flags)
                if len(buffer) > 12:
                    print(buffer)
            
        
    #Then run client
    else:
        clientSocket = socket(AF_INET, SOCK_DGRAM)              #Prepare a UDP (SOCK_DGRAM) server socket using IPv4 (AF_INET)
        clientSocket.settimeout(0.5)                     #Timeout = 500ms
        #Client initiates three-way handshake with server to establish reliable connection
        #Send SYN packet to server
        seq = 0
        ack = 0
        #the last 4 bits:  S A F R
        # 1 0 0 0  SYN flag set, and the decimal equivalent is 8
        flags = 8                                               
        win = 0
        data = b''
        syn = create_packet(seq, ack, flags, win, data)
        clientSocket.sendto(syn, (args.ip_address, args.port))

        #Wait for SYN-ACK packet from server
        #Throw error if SYN-ACK doesn't arrive before timeout
        try:
            buffer,address = clientSocket.recvfrom(1472)
            header_from_msg = buffer[:12]
            seq, ack, flags, win = parse_header(header_from_msg)
            syn, ack, fin = parse_flags(flags)
            syn and ack
            socket.timeout
        except TimeoutError:
            print("Error: Timed out waiting for SYN-ACK")
            clientSocket.close()
            sys.exit(1)

        # Send ACK packet to server
        seq = 0
        ack = 0
        #the last 4 bits:  S A F R
        # 0 1 0 0  ACK flag set, and the decimal equivalent is 4
        flags = 4                                               
        win = 0
        data = b''
        ack = create_packet(seq, ack, flags, win, data)
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
            print(packet_data)
            #Pack the sequence number into the header
            sequence_number = i+1
            acknowledgment_number = 0
            window = 0 # window value should always be sent from the receiver-side
            flags = 0 # we are not going to set any flags when we send a data packet

            #msg now holds a packet, including our custom header and data
            msg = create_packet(sequence_number, acknowledgment_number, flags, window, packet_data)
        
            #Send file contents to server
            clientSocket.sendto(msg, (args.ip_address, args.port))
        
        clientSocket.close()                #Close socket


if __name__ == '__main__':
    main()                                  #Execution of module begins with main()