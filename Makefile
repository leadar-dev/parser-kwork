.PHONY: run
run:
	uv run python3 -m src.main

# Форматирование и линтинг (через brew: ruff, ty)
# lint       - проверяет стиль (только читает) - ruff check
# lint/fix   - проверяет и автоисправляет (изменяет файлы) - ruff check --fix
# typecheck  - проверка типов и опечаток - ty check

.PHONY: lint
lint:
	@echo "→ Checking code style..."
	@uv run ruff format --check .
	@uv run ruff check .

.PHONY: format
format:
	@echo "→ Auto-fixing issues..."
	@uv run ruff format .
	@uv run ruff check . --fix
	@echo "✓ Fixed"

.PHONY: typecheck
typecheck:
	@echo "→ Type checking..."
	@uv run ty check

.PHONY: check
check: lint typecheck
	@echo "✓ All checks passed"

.PHONY: sync
sync:
	uv sync

.PHONY: dev
dev: sync
	uv sync --dev
