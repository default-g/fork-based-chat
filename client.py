import socket
import json
import sys
import os, signal
from colorama import Fore


class Client:
    def __init__(self, server_host, server_port):
        self.__server_address = (server_host, server_port)
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __sigchld_handler(signum, frame):
        pid, _ = os.waitpid(-1, os.WNOHANG)

    def __receiver_thread(self):
        with self.__socket as socket:
            while True:
                data = socket.recv(1024)
                if not data:
                    break
                data = json.loads(data.decode("utf-8"))
                print(
                    data["color"]
                    + data["nickname"]
                    + ": "
                    + Fore.RESET
                    + data["message"]
                    + Fore.RESET
                )

    def run(self):
        signal.signal(signal.SIGCHLD, Client.__sigchld_handler)

        with self.__socket as socket:
            socket.connect(self.__server_address)
            if os.fork() == 0:
                try:
                    while True:
                        message = input()
                        print("\033[1A" + "\033[K", end="")
                        json_object = {
                            "message": message,
                        }
                        socket.sendall(bytes(json.dumps(json_object), encoding="utf-8"))
                except:
                    print("Disconnected")
            else:
                self.__receiver_thread()


if __name__ == "__main__":
    server_host, server_port = sys.argv[1].split(":")
    client = Client(server_host, int(server_port))
    client.run()
