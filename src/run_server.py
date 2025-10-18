from tornado import httpserver, ioloop, web
import os

INDEX_PATH = "/workplace/repo/web_resources/index.html"  # becouse tornado is dumm
CERTIFILE_PATH = "certification/cert.pem"
KEYFILE_PATH = "certification/key.pem"
CA_CERTS = "certification/fullchain.pem"


def check_files():
    files_to_check = [INDEX_PATH, CERTIFILE_PATH, KEYFILE_PATH, CA_CERTS]
    for path in files_to_check:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File '{path}' does not exist.")


class RootHandler(web.RequestHandler):
    def get(self):
        self.render(INDEX_PATH)


def main():  # called from /workplace/run.py
    print("Server is starting")
    check_files()
    app = web.Application([(r"/", RootHandler)])
    server = httpserver.HTTPServer(
        app,
        ssl_options={
            "certfile": CERTIFILE_PATH,
            "keyfile": KEYFILE_PATH,
            "ca_certs": CA_CERTS,
        },
    )
    server.listen(443)
    ioloop.IOLoop.instance().start()
