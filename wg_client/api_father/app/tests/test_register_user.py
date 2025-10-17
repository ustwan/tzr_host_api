import asyncio

from usecases.register_user import RegisterUserUseCase


class InMemoryRepo:
    def __init__(self):
        self.users = set()
        self.tg = {}

    async def count_telegram_players(self, telegram_id: int) -> int:
        return self.tg.get(telegram_id, 0)

    async def is_login_taken(self, login: str) -> bool:
        return login in self.users

    async def insert_user_and_tgplayer(self, login: str, gender: int, telegram_id: int, username):
        self.users.add(login)
        self.tg[telegram_id] = self.tg.get(telegram_id, 0) + 1


class DummyGS:
    async def register_user(self, *, host: str, port: int, login: str, password: str, gender: int) -> None:
        return None


class DummyQueue:
    def __init__(self):
        self.items = []

    async def enqueue(self, name: str, item: dict) -> None:
        self.items.append((name, item))


def test_register_success():
    uc = RegisterUserUseCase(InMemoryRepo(), DummyGS(), DummyQueue(), "queue:requests")
    asyncio.get_event_loop().run_until_complete(uc.execute(
        login="alice", password="P@ssw0rd", gender=1, telegram_id=1, username=None,
        game_server_host="127.0.0.1", game_server_port=5190,
    ))

def test_register_limit_exceeded():
    repo = InMemoryRepo()
    repo.tg[10] = 5
    uc = RegisterUserUseCase(repo, DummyGS())
    try:
        asyncio.get_event_loop().run_until_complete(uc.execute(
            login="bob", password="P@ssw0rd", gender=1, telegram_id=10, username=None,
            game_server_host="127.0.0.1", game_server_port=5190,
        ))
        assert False, "expected ValueError"
    except ValueError as e:
        assert str(e) == "limit_exceeded"


