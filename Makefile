.PHONY: up down logs test ingest status

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

test:
	docker build -t atrium-api:test ./apps/api
	docker run --rm \
		-e WATCH_DOCUMENTS=false \
		-e EMBEDDING_BACKEND=hash \
		-e CHROMA_DIR=/tmp/chroma \
		-e DOCUMENTS_DIR=/tmp/docs \
		-e DATABASE_URL=sqlite:////tmp/atrium-test.db \
		-e QDRANT_URL=memory \
		-e NEO4J_URI= \
		atrium-api:test pytest -q

ingest:
	curl -sS -X POST http://127.0.0.1:8000/api/documents/ingest | python3 -m json.tool

status:
	curl -sS http://127.0.0.1:8000/api/health | python3 -m json.tool
