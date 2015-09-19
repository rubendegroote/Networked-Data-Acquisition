import threading as th
import asyncore
import socket
import time

from backend.Helpers import *
from backend.connectors import Connector, Acceptor


class Dispatcher(asyncore.dispatcher):
    def __init__(self, PORT, name, defaultRequest = ('status',{})):
        super(Dispatcher,self).__init__()
        self.port = PORT
        self.name = name
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.bind(('', self.port))
        self.listen(5)

        self.acceptors = []

        self.connectors = {}
        self.connInfo = {}

        self.defaultRequest = defaultRequest

        self.looping = True
        t = th.Thread(target=self.start).start()

        self.sleeptime = 0.03

    def start(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(self.sleeptime)

    def stop(self):
        self.looping = False

    def writeable(self):
        return False

    def readable(self):
        return True

    @try_call
    def add_connector(self, params):
        address = params['address']
        if address is None:
            return
        for name, add in self.connectors.items():
            if address == (add.chan[0], str(add.chan[1])):
                if self.connInfo[name][0]:
                    return
        conn = Connector(chan=(address[0], int(address[1])),
                              callback=self.connector_cb,
                              onCloseCallback=self.connector_closed_cb,
                              default_callback=self.default_cb,
                              name=self.name)
        self.connectors[conn.acceptor_name] = conn
        self.connInfo[conn.acceptor_name] = (
            True, conn.chan[0], conn.chan[1])
        return {}

    @try_call
    def remove_connector(self,params):
        address = params['address']
        toRemove = []
        for name, prop in self.connInfo.items():
            if address == [prop[1], str(prop[2])]:
                self.connectors[name].close()
                toRemove.append(name)
        for name in toRemove:
            self.connectors[name].close()
            del self.connectors[name]
            del self.connInfo[name]

        return {}

    def acceptor_cb(self, message):
        function = message['message']['op']
        args = message['message']['parameters']

        params = getattr(self, function)(args)

        return add_reply(message, params)

    def acceptor_closed_cb(self, acceptor):
        self.acceptors.remove(acceptor)

    def connector_cb(self, message):
        if message['reply']['parameters']['status'][0] == 0:
            function = message['reply']['op']
            args = message['reply']['parameters']
            track = message['track']
            for mess in message['status_updates']:
                adjusted_mess = mess
                adjusted_mess[1] = "{} says \'{}\'".format(track[-1][0],mess[1])
                self.notify_connectors(adjusted_mess)
            params = getattr(self, function)(track, args)
        else:
            exception = message['reply']['parameters']['exception']
            self.notify_connectors(([1],"Received status fail in reply\n:{}".format(exception)))

    def connector_closed_cb(self,connector):
        self.connInfo[connector.acceptor_name] = (
            False, connector.chan[0], connector.chan[1])
        self.notify_connectors(([1],"{} disconnected from {}".format(self.name,connector.acceptor_name)))

    def default_cb(self):
        return 'status',{}

    def notify_connectors(self,status_update):
        for acc in self.acceptors:
            acc.message_queue.append(status_update)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            try:
                sender = self.get_sender_ID(sock)
                logging.info(sender)
            except Exception as e:
                self.notify_connectors(([1],"Received status fail in handle_accept\n:{}".format(str(e))))
                return
            self.acceptors.append(Acceptor(sock=sock,name=self.name,
                               callback=self.acceptor_cb,
                               onCloseCallback=self.acceptor_closed_cb))

    def get_sender_ID(self, sock):
        now = time.time()
        while time.time() - now < 5:  # Tested; raises RunTimeError after 5 s
            try:
                sender = sock.recv(1024).decode('UTF-8')
                break
            except Exception as e:
                pass
        else:
            raise
        return sender

    def handle_close(self):
        self.stop()
        super(Dispatcher, self).handle_close()

