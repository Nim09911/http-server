import os
import signal
import sys
from httprequesthandler import HTTPRequestHandler
import logging

# defining logging levles
#DEFINE 1  DEBUG
#DEFINE 2  INFO
#DEFINE 3  WARNING
#DEFINE 4  ERROR
#DEFINE 5  CRITICAL

def storepid():
    
    pid = os.getpid()
    with open('./temp.txt', 'w') as file:
        file.write(str(pid))
        file.close()
    return

def getpid():

    with open('./temp.txt', 'r') as file:
        pid = int(file.read())
        file.close()
    os.remove('./temp.txt')
    return pid

if __name__ == '__main__':
    
    try:
        try:
            loglevel = int(sys.argv[2])
        except:
            loglevel = 1
        if(loglevel < 1 or loglevel > 5):
            print('Error: Command format: python3 http.py [start|restart|stop|] [loglevel int(1~5)]')
            sys.exit()
        loglevel = loglevel*10
    except:
        pass

    try:
        command = str(sys.argv[1])
        if(command == 'start' or command == 'restart'):
            if(command == 'restart' or os.access('./temp.txt', os.F_OK)):
                try:
                    os.kill(getpid(), signal.SIGTERM)     
                except:
                    # on restart -> but actually server hasnt started yet
                    pass
            storepid()
            server = HTTPRequestHandler(loglevel=loglevel)
            print('server starting')
            try:
                server.start()
            except:
                print('Error in starting server')
        elif(str(sys.argv[1]) == 'stop'):
            try:
                os.kill(getpid(), signal.SIGTERM)
                os.remove('./temp.txt')
                print('Server Stopped')
            except:
                if(os.access('./temp.txt', os.F_OK)):
                    print('Unable to stop')
                else:
                    print('Server stopped')
    except:
        print('Error: Command format is python3 http.py [start|restart|stop]\r\n Optional: \r\n \tloglevel: int: 1~5 \r\n')
        sys.exit()
