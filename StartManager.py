from backend.Manager import start_manager
import threading as th
import asyncore


def main():
    start_manager()

if __name__ == '__main__':
    main()
