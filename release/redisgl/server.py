"""
server.py

Copyright 2018. All Rights Reserved.

Created: April 13, 2017
Authors: Toki Migimatsu
"""
import json
import os
import shutil
import threading
from http.server import HTTPServer
from multiprocessing import Process, Queue

from .HTTPRequestHandler import makeHTTPRequestHandler
from .WebSocketServer import WebSocketServer


def handle_get_request(request_handler, get_vars, **kwargs):
    """
    HTTPRequestHandler callback:

    Serve content inside WEB_DIRECTORY
    """
    WEB_DIRECTORY = os.path.join(os.path.dirname(__file__), "web")

    path_tokens = [token for token in request_handler.path.split("/") if token]

    # Default to index.html
    request_path = None
    if not path_tokens or ".." in path_tokens:
        request_path = os.path.join(WEB_DIRECTORY, "simulator.html")
    elif path_tokens[0] == "get_websocket_port":
        request_handler.wfile.write(str(kwargs["ws_port"]).encode("utf-8"))
        ui_requests = kwargs["ui_requests"]
        ui_requests.put(("WebServer.on_connect",))
        return
    elif len(path_tokens) > 2 and path_tokens[0] == "resources":
        path_resources = [f"{WEB_DIRECTORY}/resources".encode("utf-8")]
        for path_resource in path_resources:
            request_path = os.path.join(path_resource.decode("utf-8"), *path_tokens[1:])
            if os.path.isfile(request_path):
                break
            request_path = None
    else:
        request_path = os.path.join(WEB_DIRECTORY, *path_tokens)
    # print("PATH_TOKENS", path_tokens)
    # print("REQUEST_PATH", request_path)

    # Check if file exists
    if request_path is None or not os.path.isfile(request_path):
        # print(request_handler.path, request_path)
        request_handler.send_error(404, "File not found.")
        return

    # Otherwise send file directly
    with open(request_path, "rb") as f:
        shutil.copyfileobj(f, request_handler.wfile)


def handle_post_request(request_handler, post_vars, **kwargs):
    """
    HTTPRequestHandler callback:

    Set POST variables as Redis keys
    """
    path_tokens = [token for token in request_handler.path.split("/") if token]

    if not path_tokens or ".." in path_tokens:
        return
    if path_tokens[0] == "DEL":
        keys = [key for key, _ in post_vars.items()]
        if not keys:
            return
        if type(keys[0]) is bytes:
            keys = [k.decode("utf-8") for k in keys]

        # result = kwargs["redis_db"].delete(*keys)
        # print("DEL {}: {}".format(" ".join(keys), result))

    elif path_tokens[0] == "SET":
        for key, val_str in post_vars.items():
            if type(key) is bytes:
                key = key.decode("utf-8")

            if type(val_str[0]) is bytes:
                val_json = json.loads(val_str[0].decode("utf-8"))
            else:
                val_json = json.loads(val_str[0])

            try:
                types = (str, unicode)
            except:
                types = (str,)

            if type(val_json) in types:
                val = val_json
            elif type(val_json) is dict:
                val = json.dumps(val_json)
            else:
                val = "; ".join(" ".join(map(str, row)) for row in val_json)
            # print("%s: %s" % (key, val))
            ui_requests = kwargs["ui_requests"]
            ui_requests.put(("WebServer.on_update", key, val))
            # kwargs["redis_db"].set(key, val)

    elif path_tokens[0] == "READY":
        keys = list(post_vars)
        ui_requests = kwargs["ui_requests"]
        ui_requests.put(("WebServer.on_ready", keys[0]))


def run_http_server(http_port, ws_port, ui_requests, verbose: bool):
    kwargs = {
        "http_port": http_port,
        "ws_port": ws_port,
        "ui_requests": ui_requests,
    }
    http_server = HTTPServer(
        ("", http_port),
        makeHTTPRequestHandler(
            handle_get_request, handle_post_request, kwargs, verbose=verbose
        ),
    )
    http_server.serve_forever()


class WebServer:
    def __init__(self):
        self._ui_requests = Queue()
        self._db = {}
        self._key_vals = []
        self._del_keys = []
        self._callback_fns = {}

    def connect(self, http_port=8000, ws_port=8001, verbose: bool = True):
        # Create RedisMonitor, HTTPServer, and WebSocketServer
        if verbose:
            print("Starting up server...\n")
        self.is_running = True
        # redis_monitor = RedisMonitor(host=args.redis_host, port=args.redis_port, password=args.redis_pass, db=args.redis_db,
        #                              refresh_rate=args.refresh_rate, key_filter=args.key_filter, realtime=args.realtime)
        # print("Connected to Redis database at %s:%d (db %d)" % (args.redis_host, args.redis_port, args.redis_db))
        # http_server = HTTPServer(("", args.http_port),
        #                          makeHTTPRequestHandler(make_handle_get_request(redis_monitor), handle_post_request, get_post_args))
        self.ws_server = WebSocketServer(port=ws_port)

        # Start HTTPServer
        self.http_server_process = Process(
            target=run_http_server,
            args=(http_port, ws_port, self._ui_requests, verbose),
        )
        self.http_server_process.start()
        if verbose:
            print("Started HTTP server on port %d" % (http_port))

        # Start WebSocketServer
        # ws_server_thread = threading.Thread(target=ws_server.serve_forever, args=(redis_monitor.initialize_client,))
        ws_server_thread = threading.Thread(
            target=self.ws_server.serve_forever, args=(self._initialize_client,)
        )
        ws_server_thread.daemon = True
        ws_server_thread.start()
        if verbose:
            print("Started WebSocket server on port %d\n" % (ws_port))

        # Start RedisMonitor
        print(
            f"Server ready. Listening for incoming connections at http://localhost:{http_port}.\n"
        )
        # redis_monitor.run_forever(ws_server)

    def set(self, key, val, commit=False):
        self._key_vals.append((key, val))
        self._db[key] = val
        if commit:
            self.commit()

    def set_matrix(self, key, val, commit=False):
        self.set(key, " ".join(map(str, val)), commit)

    def delete(self, key):
        self._del_keys.append(key)
        del self._db[key]

    def commit(self):
        self.ws_server.lock.acquire()
        for client in self.ws_server.clients:
            client.send(
                self.ws_server.encode_message(
                    {"update": self._key_vals, "delete": self._del_keys}
                )
            )
        self.ws_server.lock.release()
        self._key_vals.clear()
        self._del_keys.clear()

    def on_connect(self, callback_fn):
        self._callback_fns["WebServer.on_connect"] = callback_fn

    def on_ready(self, callback_fn, args=None):
        if args is not None:
            self._callback_fns["WebServer.on_ready"] = lambda: callback_fn(*args)
        else:
            self._callback_fns["WebServer.on_ready"] = callback_fn

    def on_update(self, key, callback_fn):
        self._callback_fns[key] = callback_fn

    def wait(self):
        while self.is_running:
            request = self._ui_requests.get()
            command = request[0]
            if command not in self._callback_fns:
                continue
            if command == "WebServer.on_update":
                key, val = request[1:]
                self._callback_fns[key](key, val)
                break
            elif command in ("WebServer.on_connect", "WebServer.on_ready"):
                self._callback_fns[command]()
                break

        self.shutdown()

    def _initialize_client(self, ws_server, client):
        self._key_vals.clear()
        self._del_keys.clear()
        key_vals = list(iter(self._db.items()))
        client.send(ws_server.encode_message({"update": key_vals, "delete": []}))

    def shutdown(self):
        self.is_running = False
        self.http_server_process.terminate()

    @staticmethod
    def parse_matrix(val):
        return np.array(map(float, val.split(" ")))
