from backend.DataServer import start_dataserver
import threading as th
import asyncore


def main():
    start_dataserver()

if __name__ == '__main__':
    main()
