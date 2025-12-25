import unittest
from src.server.websocket_handler import WebSocketHandler

class TestWebSocketHandler(unittest.TestCase):

    def setUp(self):
        self.handler = WebSocketHandler()

    def test_connection(self):
        # Simulate a WebSocket connection
        self.handler.on_connect()
        self.assertTrue(self.handler.is_connected)

    def test_message_handling(self):
        # Simulate receiving a message
        test_message = "Hello, World!"
        self.handler.on_message(test_message)
        self.assertIn(test_message, self.handler.messages)

    def test_disconnection(self):
        # Simulate a WebSocket disconnection
        self.handler.on_disconnect()
        self.assertFalse(self.handler.is_connected)

if __name__ == '__main__':
    unittest.main()