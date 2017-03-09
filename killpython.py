import os,psutil


def kill_all_python():
    for proc in psutil.process_iter():
        pinfo = proc.as_dict(attrs=['pid', 'name'])
        procname = str(pinfo['name'])
        procpid = str(pinfo['pid'])
        if "python" in procname and procpid != str(os.getpid()):
            print("Stopped Python Process ", proc)
            proc.kill()
        
def main():
    kill_all_python()

if __name__ == '__main__':
    main()