## API_FATHER - Clean Architecture overview

Layers:
- interfaces/http: FastAPI routes
- usecases: application services (RegisterUserUseCase)
- ports: abstract dependencies (UserRepository, GameServerClient, Queue)
- adapters: concrete implementations (MySQL, Socket, Redis)
- infrastructure: container/wiring

Run:
- Env via HOST_API_SERVICE/.env
- Compose via tools/ctl.sh

Tests:
- Unit tests for use cases
- Smoke tests with FastAPI TestClient



