
import asyncore
import asynchat


class Dispatcher(asyncore.dispatcher):
    def _init__(self):
        super(Dispatcher,self).__init__()
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.bind(('', self.port))
        self.listen(5)

        self.acceptors = []

        self.connectors = {}
        self.connInfo = {}

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

    def add_connector(self,address = None):
        if address is None:
            return
        for name, add in self.connectors.items():
            if address == (add.chan[0], str(add.chan[1])):
                if self.connInfo[name][0]:
                    return
        conn = Connector(chan=(address[0], int(address[1])),
                              callback=self.connector_callback,
                              onCloseCallback=self.connector_closed,
                              t='DS_to_A',
                              defaultRequest='data')
        self.connectors[conn.artistName] = conn
        self.connInfo[conn.artistName] = (
            True, conn.chan[0], conn.chan[1])
        for c in self.acceptors: # should be changed to use add_notification
            c.commQ.put(self.connInfo)

    def remove_connector(self,address):
        toRemove = []
        for name, prop in self.connInfo.items():
            if address == (prop[1], str(prop[2])):
                self.connectors[name].close()
                toRemove.append(name)

        for name in toRemove:
            del self.connectors[name]
            del self.connInfo[name]

    def acceptor_callback(self,message):
        function = message['message']['op']
        args = message['message']['parameters']

        params = getattr(self,function)(args)

        return add_reply(message,params)

    def acceptor_closed(self,acceptor):
        self.acceptors.remove(acceptor)

    def connector_calback(self,message):
        ## deal with message
        pass # no return value needed!

    def connector_closed(self,connector):
        self.connInfo[connector.artistName] = (
            False, connector.chan[0], connector.chan[1])
        for c in self.acceptors:
            c.commQ.put(self.connInfo)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            try:
                sender = self.get_sender_ID(sock)
                logging.info(sender)
            except:
                return
            self.acceptors.append(Acceptor(sock=sock,
                               callback=self.acceptor_callback,
                               onCloseCallback=self.acceptor_closed))

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
        super(Dispatcher, self).handle_close()

d = Dispatcher()
print(dir(d))
print(getattr(d,'get_sender_ID'))