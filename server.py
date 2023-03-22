import socket
import os
from colorama import Fore
import json
from datetime import datetime
import random
import pickle
import threading
import os, signal
import sys
import time


class Server:
    def __init__(self, host, port=0):
        self.__address = (host, port)
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__socket.bind(self.__address)
        self.__colors = [Fore.BLUE, Fore.CYAN, Fore.MAGENTA, Fore.RED]
        self.__server_connections = {}
        open("messages", "w").close()

    def __notify_all_clients(self):
        while True:
            while not self.__load_messages():
                time.sleep(0.1)
            messages = self.__load_messages()
            connections = self.__server_connections
            for message in messages:
                if "from" in message and not connections[message["from"]]["nickname"]:
                    self.__handle_nickname_assignment(
                        message["from"], message["message"]
                    )
                    continue
                try:    
                    message = {
                            "nickname": connections[message["from"]]["nickname"],
                            "message": message["message"],
                            "color": connections[message["from"]]["color"],
                        }
                    print(
                        Fore.YELLOW
                        + Server.__get_timestamp()
                        + f" Message from {message['nickname']}: {message['message']} "
                        + Fore.RESET
                )
                except:
                    message = {
                        "nickname": 'SERVER',
                        "message": message["message"],
                        "color": Fore.GREEN,
                    }       
                
                for connection in list(connections):
                    try:
                        self.__server_connections[connection]["connection"].sendall(
                            Server.__encode_json(message)
                        )
                    except:
                        self.__server_connections[connection]["connection"].close()
                        self.__server_connections.pop(connection, None)

            self.__clear_messages()

    def __handle_nickname_assignment(self, connectionfd, nickname: str):
        if not self.__is_nickname_in_use(nickname):
            self.__server_connections[connectionfd]["nickname"] = nickname
            address = self.__server_connections[connectionfd]["address"]
            self.__server_connections[connectionfd]["connection"].sendall(
                Server.__encode_json(
                    {
                        "color": Fore.GREEN,
                        "message": f"Welcome to the chat, {nickname}",
                        "nickname": "SERVER",
                    }
                )
            )
            print(
                Fore.YELLOW
                + Server.__get_timestamp()
                + f" Client with address {address[0]}:{address[1]} assigned with nickname '{nickname}'"
                + Fore.RESET
            )

        else:
            self.__server_connections[connectionfd]["connection"].sendall(
                Server.__encode_json(
                    {
                        "color": Fore.GREEN,
                        "message": Fore.RED
                        + "Nickname is already in use. Try another one",
                        "nickname": "SERVER",
                    }
                )
            )

    def __server_commands_handler(self):
        while True:
            command = input()
            command = command.split(" ")
            if command[0] == "help":
                print('List of commands: ')
                print('list - List all connected users')
                print('kick <nickname> - Kick user from chat')
                print('notify <message> - Notify all users from server')
            elif command[0] == "list":
                i = 1
                print(Fore.RESET + f"Current online: {len(self.__server_connections)}")
                for connection in self.__server_connections:
                    nickname = self.__server_connections[connection]["nickname"]
                    address = self.__server_connections[connection]["address"]
                    print(f"{i}. {address[0]}:{address[1]} {nickname}")
                    i += 1   
            elif command[0] == "kick":
                if not command[1]:
                    print('Nickname not defined')
                    continue
                for connection in self.__server_connections:
                    if self.__server_connections[connection]["nickname"] == command[1]:
                        message = {
                            "message": Fore.RED + "You've been kicked" + Fore.RESET,
                            "nickname": "SERVER",
                            "color": Fore.GREEN,
                        }
                        self.__server_connections[connection]["connection"].sendall(
                            Server.__encode_json(message)
                        )
                        self.__server_connections[connection]["connection"].close()
                        os.kill(
                            self.__server_connections[connection]["pid"], signal.SIGKILL
                        )
                        self.__server_connections.pop(connection, None)
                        break
            elif command[0] == "notify":
                message = ''
                command.pop(0)
                if not command[1]:
                    print('Message not defined')
                    continue
                for word in command:
                    message += word + ' '
                message = {
                    'message': message
                }        
                self.__put_messages(message)        
            else:
                print(Fore.RESET + "Command not found, use help to list all commands")

    def __put_messages(self, message):
        if os.stat("messages").st_size == 0:
            messages = []
        messages.append(message)
        with open("messages", "wb") as f:
            pickle.dump(messages, f)

    def __load_messages(self):
        if os.stat("messages").st_size == 0:
            return []
        with open("messages", "rb") as f:
            return pickle.load(f)
        
    def __clear_messages(self):
        open("messages", "wb").close()

    def __encode_json(dictionary: dict):
        return bytes(json.dumps(dictionary), encoding="utf-8")

    def __is_nickname_in_use(self, nickname):
        connections = self.__server_connections
        return nickname in [item["nickname"] for item in connections.values()]

    def __get_timestamp():
        date_time_object = datetime.now()
        return date_time_object.strftime("%H:%M:%S - %b %d %Y")

    def __client_thread(self, connection, connection_data):
        with connection:
            greeting_message = {
                "nickname": "SERVER",
                "message": "Input nickname to use chat",
                "color": Fore.GREEN,
            }
            connection.sendall(Server.__encode_json(greeting_message))
            address_string = (
                f"{connection_data['address'][0]}:{connection_data['address'][1]}"
            )
            print(
                Fore.YELLOW
                + Server.__get_timestamp()
                + f" Connected client: {address_string}"
                + Fore.RESET
            )
            while True:
                data = connection.recv(1024)
                if not data:
                    break
                data = json.loads(data.decode("utf-8"))
                if data["message"]:
                    data["from"] = connection_data["server_connection_fileno"]
                    self.__put_messages(data)
            print(
                Fore.YELLOW
                + Server.__get_timestamp()
                + f" Disconnected client: {address_string}"
                + Fore.RESET
            )

    def __sigchld_handler(signum, frame):
        pid, _ = os.waitpid(-1, os.WNOHANG)

    def run(self):
        socket_address = self.__socket.getsockname()
        print(Fore.GREEN + f"Server running at {socket_address[0]}:{socket_address[1]}")

        threading.Thread(target=self.__notify_all_clients, daemon=True).start()
        threading.Thread(target=self.__server_commands_handler, daemon=True).start()

        signal.signal(signal.SIGCHLD, Server.__sigchld_handler)

        with self.__socket as server_socket:
            server_socket.listen()
            while True:
                connection, address = server_socket.accept()
                connectionfd = connection.fileno()
                connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                connection_data = {
                    "server_connection_fileno": connectionfd,
                    "connection": connection,
                    "address": address,
                    "nickname": "",
                    "color": random.choice(self.__colors),
                }
                pid = os.fork()
                if pid == 0:
                    server_socket.close()
                    self.__client_thread(
                        connection, connection_data
                    )
                    sys.exit(0)
                else:
                    self.__server_connections[connectionfd] = connection_data
                    self.__server_connections[connectionfd]["pid"] = pid


if __name__ == "__main__":
    server = Server("localhost", 5050)
    server.run()
