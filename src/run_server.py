from tornado import httpserver, ioloop, web
import os

INDEX_PATH = "repo/web_resources/index.html"
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


app = web.Application([(r"/", RootHandler)])

if __name__ == "__main__":
    print("Server is starting")
    check_files()
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
