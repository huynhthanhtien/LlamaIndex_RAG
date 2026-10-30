# Lệnh thường dùng. Chạy `make` để xem danh sách.
# Dùng .RECIPEPREFIX để không phụ thuộc ký tự tab.
.RECIPEPREFIX = >
VENV := venv/bin/python
export TMPDIR := $(CURDIR)/.tmp
export PYTHONDONTWRITEBYTECODE := 1
NGAY := $(shell date +%F)

.PHONY: help test test-log test-llm eval baseline eval-answers report clean

help:
> @echo "make test         - kiểm thử offline (không cần GPU/Ollama)"
> @echo "make test-log     - như make test, lưu output kèm commit vào eval/results/logs/<ngày>_kiem-thu/ để đính báo cáo"
> @echo "make test-llm     - kiểm thử có LLM: gọi Ollama trong .env (RAG_PROFILE=server)"
> @echo "make eval         - đo truy hồi (vector, rerank, lọc phiên bản, hybrid), ghi eval/results/truy-hoi.{json,md}"
> @echo "make baseline     - đo baseline BM25 / không xếp hạng"
> @echo "make eval-answers - chấm câu trả lời bằng evaluator của LlamaIndex (cần Ollama)"
> @echo "make report       - build PDF báo cáo (XeLaTeX + biber)"
> @echo "make clean        - xoá .tmp và thư mục build của LaTeX"

test:
> @mkdir -p .tmp
> $(VENV) -m unittest discover -s tests -t . -v

# Báo cáo ghi đủ ba trạng thái pass / skip / expected failure kèm output và commit (nhận xét tuần 7, ý 7):
# dòng cuối của log là tổng kết của unittest, vd "OK (skipped=10, expected failures=2)".
test-log:
> @mkdir -p .tmp eval/results/logs/$(NGAY)_kiem-thu
> @f=eval/results/logs/$(NGAY)_kiem-thu/make-test-$$(git rev-parse --short HEAD).log; \
>  { echo "# make test — $$(date '+%F %T') — commit $$(git rev-parse --short HEAD)"; \
>    git status --porcelain -- src eval tests data/processed ':!eval/results' | sed 's/^/# chưa commit: /'; \
>    $(VENV) -m unittest discover -s tests -t . -v 2>&1; } > $$f; rc=$$?; \
>  grep -cE ' \.\.\. ok$$' $$f | sed 's/^/pass: /'; grep -cE ' \.\.\. skipped' $$f | sed 's/^/skip: /'; \
>  grep -cE ' \.\.\. expected failure$$' $$f | sed 's/^/expected failure: /'; tail -1 $$f; echo "Đã ghi $$f"; exit $$rc

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
