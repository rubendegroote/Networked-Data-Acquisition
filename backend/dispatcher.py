import threading as th
import asyncore
import socket
import time
import configparser
import backend.helpers as hp
from backend.connectors import Connector, Acceptor

from config.absolute_paths import CONFIG_PATH

class Dispatcher(asyncore.dispatcher):
    def __init__(self, name):
        super(Dispatcher,self).__init__()
        self.config_parser = configparser.ConfigParser()
        self.config_parser.read(CONFIG_PATH)
        PORT = int(self.config_parser['ports'][name])

        self.port = PORT
        self.name = name
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.bind(('', self.port))
        self.listen(5)

        self.acceptors = []

        self.connectors = {}
        self.connInfo = {}

        self.looping = True
        self.thread =  th.Thread(target=self.start)
        self.thread.start()    

    def start(self):
        while self.looping:
            asyncore.loop(count=1,timeout=1)
            time.sleep(0.005)

    def stop(self):
        for acc in self.acceptors:
            acc.close()
        for conn in self.connectors.values():
            conn.close()
        self.looping = False
        self.thread.join()

    def writeable(self):
        return False

    def readable(self):
        return True

    @hp.try_call
    def forward_instruction(self,params):
        device = self.connectors[params['device']]
        instruction,arguments = params['instruction'],params['arguments']
        device.add_request(('execute_instruction',{'instruction':instruction,
                                                   'arguments':arguments}))

        return {}

    def execute_instruction_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Device {} received instruction correctly.".format(origin)))

    @hp.try_call
    def add_connector(self, params):
        address = params['address']
        if address is None:
            return
        for name, add in self.connectors.items():
            if (str(address[0]),str(address[1])) == (str(add.chan[0]), str(add.chan[1])):
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
        self.connectors[conn.acceptor_name].add_request((
                    'initial_information',{}))
        time.sleep(0.05)
        return {}

    @hp.try_call
    def initial_information(self,params):
        return {}

    def initial_information_reply(self,track,params):
        pass

    @hp.try_call
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

        return hp.add_reply(message, params)

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
            params = getattr(self, function)(track,args)
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


