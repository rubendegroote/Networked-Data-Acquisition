from Artist import makeArtist
import threading as th
import asyncore

def main():
    m = makeArtist('ABU')
    t0 = th.Timer(1, m.StartDAQ).start()
    asyncore.loop(0.001)

if __name__ == '__main__':
    main()
