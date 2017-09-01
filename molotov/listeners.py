import io


_UNREADABLE = "***WARNING: Molotov can't display this body***"
_BINARY = "**** Binary content ****"
_FILE = "**** File content ****"
_COMPRESSED = ('gzip', 'compress', 'deflate', 'identity', 'br')


class BaseListener(object):
    async def __call__(self, event, **options):
        attr = getattr(self, 'on_' + event, None)
        if attr is not None:
            await attr(**options)


class StdoutListener(BaseListener):
    def __init__(self, **options):
        self.verbose = options.get('verbose', 0)
        self.console = options['console']

    def _body2str(self, body):
        try:
            from aiohttp.payload import Payload
        except ImportError:
            Payload = None

        if Payload is not None and isinstance(body, Payload):
            body = body._value

        if isinstance(body, io.IOBase):
            return _FILE

        if not isinstance(body, str):
            try:
                body = str(body, 'utf8')
            except UnicodeDecodeError:
                return _UNREADABLE

        return body

    async def on_sending_request(self, session, request):
        if self.verbose < 2:
            return
        raw = '>' * 45
        raw += '\n' + request.method + ' ' + str(request.url)
        if len(request.headers) > 0:
            headers = '\n'.join('%s: %s' % (k, v) for k, v in
                                request.headers.items())
            raw += '\n' + headers
        if request.headers.get('Content-Encoding') in _COMPRESSED:
            raw += '\n\n' + _BINARY + '\n'
        elif request.body:
            raw += '\n\n' + self._body2str(request.body) + '\n'

        self.console.print(raw)

    async def on_response_received(self, session, response, request):
        if self.verbose < 2:
            return
        raw = '\n' + '=' * 45 + '\n'
        raw += 'HTTP/1.1 %d %s\n' % (response.status, response.reason)
        items = response.headers.items()
        headers = '\n'.join('{}: {}'.format(k, v) for k, v in items)
        raw += headers
        if response.headers.get('Content-Encoding') in _COMPRESSED:
            raw += '\n\n' + _BINARY
        elif response.content:
            content = await response.content.read()
            if len(content) > 0:
                # put back the data in the content
                response.content.unread_data(content)
                try:
                    raw += '\n\n' + content.decode()
                except UnicodeDecodeError:
                    raw += '\n\n' + _UNREADABLE
            else:
                raw += '\n\n'

        raw += '\n' + '<' * 45 + '\n'
        self.console.print(raw)


class CustomListener(object):
    def __init__(self, fixture):
        self.fixture = fixture

    async def __call__(self, event, **options):
        await self.fixture(event, **options)
