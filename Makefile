# Lệnh thường dùng. Chạy `make` để xem danh sách.
# Dùng .RECIPEPREFIX để không phụ thuộc ký tự tab.
.RECIPEPREFIX = >
VENV := venv/bin/python
export TMPDIR := $(CURDIR)/.tmp
export PYTHONDONTWRITEBYTECODE := 1

.PHONY: help test test-llm eval baseline eval-answers report clean

help:
> @echo "make test         - kiểm thử offline (không cần GPU/Ollama)"
> @echo "make test-llm     - kiểm thử có LLM: gọi Ollama trong .env (RAG_PROFILE=server)"
> @echo "make eval         - đo truy hồi (vector, rerank, lọc phiên bản, hybrid), ghi eval/results/truy-hoi.{json,md}"
> @echo "make baseline     - đo baseline BM25 / không xếp hạng"
> @echo "make eval-answers - chấm câu trả lời bằng evaluator của LlamaIndex (cần Ollama)"
> @echo "make report       - build PDF báo cáo (XeLaTeX + biber)"
> @echo "make clean        - xoá .tmp và thư mục build của LaTeX"

test:
> @mkdir -p .tmp
> $(VENV) -m unittest discover -s tests -t . -v

test-llm:
> @mkdir -p .tmp
> RAG_TEST_LLM=1 RAG_PROFILE=server $(VENV) -m unittest tests.test_llm -v

eval:
> @mkdir -p .tmp eval/results
> RAG_PROFILE=server $(VENV) eval/evaluate.py --cau-hinh vector,rerank,loc,rerank+loc,hybrid,hybrid+rerank+loc --doi-chieu-thu-vien

baseline:
> @mkdir -p .tmp eval/results
> RAG_PROFILE=server $(VENV) eval/baselines.py

eval-answers:
> @mkdir -p .tmp eval/results
> RAG_PROFILE=server $(VENV) eval/evaluate_answers.py --che-do ca-hai

report:
> cd report && latexmk -pdf -interaction=nonstopmode main.tex

clean:
> rm -rf .tmp
> cd report && latexmk -C
