from backend.FileServer import start_fileserver
import threading as th
import asyncore


def main():
    start_fileserver()

if __name__ == '__main__':
    main()
