## Worker - Clean Architecture overview

Layers:
- ports: Queue interface
- adapters: RedisQueue implementation
- usecases: ProcessEventUseCase
- app/main.py: thin loop invoking use cases

Env:
- REDIS_URL, QUEUE_REQUESTS



