#Import libraries required for the program to work
import argparse
import sys
from socket import *
from header import create_packet



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


        #While data received from client, save to buffer
        while True:
            buffer = serverSocket.recvfrom(1472)
            print(buffer)
        
    #Then run client
    else:
        clientSocket = socket(AF_INET, SOCK_DGRAM)
        print(f'A simpleperf client connecting to server {args.ip_address}, port {args.port}')    #Print message when client request sent

        #Open the file and read contents to a buffer
        with open(args.file, 'rb') as f:
            data = bytearray(f.read())
        print(f'app data for size ={len(data)}')
        packet_size = 1460
        num_packets = (len(data) + packet_size) // packet_size
        print(f'number of packets={num_packets}')
        
        #Loop through packets
        for i in range(num_packets):
            #Calculate start and end points of the data in this packet
            start = i * (packet_size - 12)
            end = min(start + 1460, len(data))
            print(f'start:{start}, end:{end}')
            #Slice the data 
            packet_data = data[start:end]
            #Pack the sequence number into the header
            sequence_number = i
            acknowledgment_number = 0
            window = 0 # window value should always be sent from the receiver-side
            flags = 0 # we are not going to set any flags when we send a data packet

            #msg now holds a packet, including our custom header and data
            msg = create_packet(sequence_number, acknowledgment_number, flags, window, packet_data)
        
            #Send file contents to server
            clientSocket.sendto(msg, (args.ip_address, args.port))
        
        clientSocket.close()                        #Close socket


if __name__ == '__main__':
    main()                                                      #Execution of module begins with main()