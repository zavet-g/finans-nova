.PHONY: help run stop restart logs deploy build

GREEN  := \033[0;32m
BLUE   := \033[0;34m
YELLOW := \033[0;33m
RED    := \033[0;31m
RESET  := \033[0m

help:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	@echo "$(GREEN)Finans Nova - Makefile Commands$(RESET)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	@echo "  $(YELLOW)make run$(RESET)      - Запустить контейнеры"
	@echo "  $(YELLOW)make stop$(RESET)     - Остановить контейнеры"
	@echo "  $(YELLOW)make restart$(RESET)  - Перезапустить контейнеры"
	@echo "  $(YELLOW)make logs$(RESET)     - Посмотреть логи (follow mode)"
	@echo "  $(YELLOW)make build$(RESET)    - Собрать образы"
	@echo "  $(YELLOW)make deploy$(RESET)   - Деплой (pull + rebuild + restart)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"

run:
	@echo "$(GREEN)▶$(RESET) Запуск контейнеров..."
	@docker compose up -d
	@echo "$(GREEN)✓$(RESET) Контейнеры запущены"

stop:
	@echo "$(YELLOW)▶$(RESET) Остановка контейнеров..."
	@docker compose down
	@echo "$(YELLOW)✓$(RESET) Контейнеры остановлены"

restart:
	@echo "$(BLUE)▶$(RESET) Перезапуск контейнеров..."
	@docker compose restart
	@echo "$(BLUE)✓$(RESET) Контейнеры перезапущены"

logs:
	@echo "$(BLUE)▶$(RESET) Логи контейнеров (Ctrl+C для выхода)..."
	@docker compose logs -f

build:
	@echo "$(BLUE)▶$(RESET) Сборка образов..."
	@docker compose build
	@echo "$(GREEN)✓$(RESET) Образы собраны"

deploy:
	@echo "$(GREEN)▶$(RESET) Начало деплоя..."
	@echo "$(BLUE)  [1/4]$(RESET) Git pull..."
	@git pull
	@echo "$(BLUE)  [2/4]$(RESET) Остановка контейнеров..."
	@docker compose down
	@echo "$(BLUE)  [3/4]$(RESET) Сборка образов (no-cache)..."
	@docker compose build --no-cache
	@echo "$(BLUE)  [4/4]$(RESET) Запуск контейнеров..."
	@docker compose up -d
	@echo "$(GREEN)✓$(RESET) Деплой завершён"
