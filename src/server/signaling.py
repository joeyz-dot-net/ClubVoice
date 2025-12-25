class Signaling:
    def __init__(self):
        self.clients = {}

    def add_client(self, client_id, websocket):
        self.clients[client_id] = websocket

    def remove_client(self, client_id):
        if client_id in self.clients:
            del self.clients[client_id]

    async def handle_offer(self, client_id, offer):
        # Handle the offer from the client
        for other_client_id, websocket in self.clients.items():
            if other_client_id != client_id:
                await websocket.send({"type": "offer", "offer": offer, "from": client_id})

    async def handle_answer(self, client_id, answer):
        # Handle the answer from the client
        for other_client_id, websocket in self.clients.items():
            if other_client_id != client_id:
                await websocket.send({"type": "answer", "answer": answer, "from": client_id})

    async def handle_ice_candidate(self, client_id, candidate):
        # Handle ICE candidate from the client
        for other_client_id, websocket in self.clients.items():
            if other_client_id != client_id:
                await websocket.send({"type": "ice-candidate", "candidate": candidate, "from": client_id})