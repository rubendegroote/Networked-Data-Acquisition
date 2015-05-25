import http.server
import socketserver
import os
import asynchat
import asyncore
import socket
import threading as th
import multiprocessing as mp
import pickle
import time

logging.basicConfig(format='%(asctime)s: %(message)s',
                    level=logging.INFO)


class FileAndLogServer(asyncore.dispatcher):

    def __init__(self, PORT=5008):
        super(FileAndLogServer, self).__init__()
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.bind(('', PORT))
        self.listen(5)
        print('Listening on port {}'.format(PORT))

        self.looping = True
        t = th.Thread(target=self.start).start()

    def start(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.1)

    def stop(self):
        self.looping = False

    def writeable(self):
        return False

    def readable(self):
        return True

    def assignLogbook(self, path):
        self.logPath = path

    def addManager(self, address=None):
        if address == None:
            print('provide IP address and PORT')
            return
        self.manConnector = ManagerConnector((address[0], int(address[1])),
                                             callback=self.processInformation, onCloseCallback=self.manConnectorClosed)

    def processInformation(self, data):
        print(data)

    def processRequests(self, data):
        pass

    def manConnectorClosed(self):
        self.manConnector = None

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            try:
                sender = self.get_sender_ID(sock)
                logging.info(sender)
            except:
                logging.warn('Sender {} did not send proper ID'.format(addr))
                return

            if sender == 'LG_to_L':
                self.viewers.append(Acceptor(sock=sock, callback=None,
                                             onCloseCallback=None, t='LG_to_L'))
            else:
                logging.error('Sender {} named {} not understood'
                              .format(addr, sender))
                return
            logging.info('Accepted {} as {}'.format(addr, sender))

    def get_sender_ID(self, sock):
        now = time.time()
        while time.time() - now < 5:  # Tested; raises RunTimeError after 5 s
            try:
                sender = sock.recv(1024).decode('UTF-8')
                break
            except:
                pass
        else:
            raise
        return sender

    def handle_close(self):
        logging.info('Closing File and Log Server')
        super(FileAndLogServer, self).handle_close()


class ManConnector(Connector):

    def __init__(self, chan, callback, onCloseCallback):
        super(ManConnector, self).__init__(
            chan, callback, onCloseCallback, t='L_to_M')

    def found_terminator(self):
        message = pickle.loads(self.buff)
        self.buff = b""
        self.callback(sender=self, data=message)
        # Line below stays commented: traffic is one-way from manager to logbook (for now) :)
        # self.send_next()


def makeLogServer(PORT=5008):
    return FileAndLogServer(PORT)


def main():
    PORT = input('PORT?')
    d = makeLogServer(int(PORT))

if __name__ == '__main__':
    main()
