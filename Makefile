.PHONY: up down test logs

up:
docker compose -f infra/docker-compose.yml up -d

down:
docker compose -f infra/docker-compose.yml down -v

logs:
docker compose -f infra/docker-compose.yml logs -f

test:
python scripts/verify_checksum.py
