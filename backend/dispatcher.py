
import asyncore
import asynchat


class Dispatcher(asyncore.dispatcher):
    def _init__(self):
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.bind(('', self.port))
        self.listen(5)

        self.acceptors = []

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

    def callback(self,message):
        function = message['message']['op']
        args = message['message']['parameters']

        params = self.__dict__[function](args)

        return add_reply(message,params)

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
                               callback=self.callback,
                               onCloseCallback=self.closecallback,
                               t='MGui_to_M'))

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