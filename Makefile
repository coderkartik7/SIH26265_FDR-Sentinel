.PHONY: dataset train eval test run frontend backend clean help

help:
	@echo "AICTE FDR-Sentinel - Smart India Hackathon 2026 (SIH26265)"
	@echo "Usage:"
	@echo "  make dataset    Generate seed=42 synthetic dataset (150 documents)"
	@echo "  make train      Train GBDT risk model and compute SHAP explanations"
	@echo "  make eval       Run end-to-end pipeline evaluation and generate charts"
	@echo "  make test       Run full pytest test suite (27 passing tests)"
	@echo "  make run        Start the entire system locally via Docker Compose"
	@echo "  make frontend   Build and test production frontend bundle"

dataset:
	python datagen/generate_dataset.py

train:
	python backend/app/ml/train.py

eval:
	python eval/run_eval.py
	python eval/make_charts.py

test:
	pytest -v

run:
	docker compose up --build

frontend:
	cd frontend && npm install && npm run build

clean:
	rm -rf __pycache__ backend/app/**/__pycache__ .pytest_cache frontend/dist
