.PHONY: run stop build logs

run:
	docker-compose up -d

stop:
	docker-compose down

build:
	docker-compose build

logs:
	docker-compose logs -f
