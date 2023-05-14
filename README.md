# DATA2410-portfolio2
Instructions:
1) To run in server mode, use the -s flag: python3 application.py -s
* Optional arguments available in server mode:
	* -i to specify a server IP address (default: 127.0.0.1)
	* -p to specify a server port (default: 8088)
	* -r to choose a reliable method (stop_and_wait, GBN or SR)
	* -t to choose a test case (skip_ack or skip_seq)
3) To run simpleperf in client mode, use the -c flag: python3 application.py -s
* Optional arguments available in client mode:
	* -i to specify a server IP address (default: 127.0.0.1)
	* -p to specify a server port (default: 8088)
	* -f to specify which file to send (e.g. -f Loreum_ipsum.txt)
	* -r to choose a reliable method (stop_and_wait, GBN or SR) - must be the same method chosen by the server
	* -t to choose a test case (skip_ack or skip_seq) - must be the same test case chosen by the server
