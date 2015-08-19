import socket
import sys
import json
import SolsTiScommands as comm

HOST = '192.168.1.216'
PORT = 39933
for res in socket.getaddrinfo(HOST, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM):
    af, socktype, proto, canonname, sa = res
    try:
        s = socket.socket(af, socktype, proto)
    except OSError as msg:
        print(msg)
        s = None
        continue
    try:
        s.connect(sa)
    except OSError as msg:
        s.close()
        s = None
        print(msg)
        continue
    break
if not s is None:
    s.sendall(json.dumps(comm.ping()))
    data = s.recv(1024)
    s.close()
    print(repr(data))
else:
    print('derp')