import http.server
import socketserver
import os

def makeFileServer(PORT=8000):
    orig_root = os.getcwd()
    os.chdir('C:\\Data')
    httpd = socketserver.TCPServer(('', PORT), http.server.SimpleHTTPRequestHandler)
    httpd.serve_forever()
    os.chdir(orig_root)

def main():
    PORT = input('PORT?')
    makeFileServer(PORT=int(PORT))

if __name__=='__main__':
    main()
