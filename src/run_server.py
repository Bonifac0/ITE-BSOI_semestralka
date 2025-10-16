from tornado import httpserver, ioloop, web


class RootHandler(web.RequestHandler):
    def get(self):
        self.render("/workplace/repo/web_resources/index.html")


app = web.Application([(r"/", RootHandler)])

if __name__ == "__main__":
    server = httpserver.HTTPServer(
        app,
        ssl_options={
            "certfile": "cert.pem",
            "keyfile": "key.pem",
            "ca_certs": "fullchain.pem",
        },
    )
    server.listen(443)
    ioloop.IOLoop.instance().start()
