import xmlrpc.client

def launch_data_server(args):
    with xmlrpc.client.ServerProxy("http://pccris1:8080/") as proxy:
        reply = proxy.execute_launch_data_server()

def launch_file_server():
    with xmlrpc.client.ServerProxy("http://pccris1:8080/") as proxy:
        reply = proxy.execute_launch_file_server()

def launch_controller():
    with xmlrpc.client.ServerProxy("http://pccris1:8080/") as proxy:
        reply = proxy.execute_launch_controller()