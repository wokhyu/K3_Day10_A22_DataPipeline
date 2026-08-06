# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K3              |
| Tên nhóm         | A2-2              |
| Repository         | https://github.com/wokhyu/K3_Day10_A22_DataPipeline |
| Ngày hoàn thành | 2026-08-06               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Khắc Huy | [MSSV — cần điền] | Ingestion | `src/ingestion/crossref.py`; `data/raw/crossref_response.json`, `data/raw/crossref_records.json` |
| 2 | Lê Kim Nam | [MSSV — cần điền] | Cleaning & data modeling | `src/ingestion/cleaning.py`; `data/clean/papers_clean.{csv,json}` |
| 3 | Nguyễn Duy Lâm | [MSSV — cần điền] | Retrieval & evaluation | `src/retrieval/`, `src/evaluation/`; `data/embeddings/`, `data/eval/test_set.json` |
| 4 | Nguyễn Minh Hoàng | [MSSV — cần điền] | Observability & corruption | `src/observability/`, `src/ingestion/corruption.py`; `data/quality/`, `data/results/corruption_log.json` |
| 5 | Nguyễn Quốc Hiệu | 2A202601627 | Integration & Comparison | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/run_*.py`; `data/reports/` |

> Tên thành viên 1–4 suy ra từ contributor và branch trong git; MSSV và ranh giới vai trò cần từng thành viên tự xác nhận trước khi nộp.

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm hoàn thành trọn vẹn cả hai pha của bài lab. Pha baseline lấy 24 paper từ Crossref REST API, làm sạch thành 24 dòng với schema 10 cột, embed bằng `all-MiniLM-L6-v2` chạy local và nạp vào ChromaDB với cosine distance, sinh test set 72 câu hỏi rồi đánh giá bằng 4 metric cộng LLM-as-judge. Artifact baseline gồm `data/raw/` (2 file), `data/clean/`, `data/embeddings/`, `data/eval/test_set.json`, `data/results/baseline_metrics.json` cùng `baseline_answers.json`, `data/quality/` và `data/reports/phase1_report.md`.

Pha corruption áp 6 kịch bản lên dataset sạch. Về mặt *khả năng trả lời*, xóa record là loại gây tổn thất không thể cứu được: 3/72 câu mất hit vĩnh viễn vì tài liệu không còn trong index, kéo `retrieval_hit_rate` từ 1.0 xuống 0.9583. Về mặt *chất lượng câu trả lời*, blank summary nặng nhất vì `qa.py` lấy câu đầu của summary làm câu trả lời mặc định, đồng thời summary cũng nằm trong `text_for_embedding` nên record đó vừa mất khả năng trả lời vừa mất chất lượng vector — `mean_token_f1` giảm 8.9%.

Repair dựng lại từ raw snapshot phục hồi **toàn bộ** 4 metric về đúng giá trị baseline tới từng chữ số thập phân, đồng thời `passed` và `is_fresh` đều trở lại `true`.

Giới hạn lớn nhất còn lại: agent LangChain trong `src/retrieval/agent.py` chưa được gọi trong pipeline nào, nên chưa có artifact chứng minh; và `ragas` đang bị skip ở cả ba trạng thái.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (/works, rows=24)
    -> data/raw/crossref_response.json  (snapshot thô, ghi TRƯỚC khi parse)
    -> data/raw/crossref_records.json   (24 PaperRecord đã chuẩn hóa)
    -> data/clean/papers_clean.{csv,json}  (24 dòng, 10 cột, có text_for_embedding + age_days)
    -> MiniLM embedding + ChromaDB collection "papers-baseline" (cosine)
    -> data/eval/test_set.json (72 câu, ĐÓNG BĂNG cho cả 3 trạng thái)
    -> data/results/baseline_metrics.json + baseline_answers.json
    -> data/quality/phase1_quality.json + freshness_report.json
    -> data/reports/phase1_report.md
         |
         v  (corruption_flow.py đọc lại clean + baseline_metrics)
    -> 6 kịch bản corruption -> data/clean/papers_clean_corrupted.*
    -> re-index "papers-corrupted" -> corrupted_metrics.json (CÙNG test set)
    -> repair: đọc lại crossref_records.json -> build_clean_dataframe -> papers_clean_repaired.*
    -> re-index "papers-repaired" -> repaired_metrics.json (CÙNG test set)
    -> data/reports/corruption_report.md
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| ----- | ----- | ----------- | --------------- | ----- |
| Ingestion | Crossref `/works` | Retry 4 lần với backoff + tôn trọng `Retry-After`; chuẩn hóa DOI; bóc text từ markup JATS trong abstract; loại record thiếu DOI/title/abstract | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Thành viên 1 |
| Cleaning | 24 `PaperRecord` | Chuẩn hóa whitespace; join `authors`/`categories`; parse `published`; tính `age_days`; dựng `text_for_embedding`; dedupe theo `paper_id`; sort giảm dần theo ngày | `data/clean/papers_clean.{csv,json}` | Thành viên 2 |
| Embedding/index | Cột `text_for_embedding` | `all-MiniLM-L6-v2` chạy local, `normalize_embeddings=True`; ChromaDB `PersistentClient` với `space=cosine`; 3 collection tách biệt | `data/embeddings/papers_embeddings*.json` (manifest) + `data/chroma/` | Thành viên 3 |
| Evaluation | Cleaned df + index | Sinh test set theo `paper_id` (seed 42); `token_f1` trên tập token; LLM-as-judge có structured output + fallback heuristic | `data/eval/test_set.json`, `data/results/*_metrics.json`, `*_answers.json` | Thành viên 3 |
| Observability | Cleaned/corrupted df | 5 quality check + freshness so với ngưỡng 180 ngày | `data/quality/*.json` (6 file) | Thành viên 4 |
| Corruption/repair | Cleaned df, raw snapshot | 6 kịch bản corruption với seed 42; repair bằng cách chạy lại `build_clean_dataframe` từ raw | `data/clean/papers_clean_corrupted.*`, `*_repaired.*`, `data/results/corruption_log.json` | Thành viên 4 + 5 |
| Orchestration | Toàn bộ | Xếp thứ tự theo dependency; cache có kiểm soát qua `REFRESH_*`; vá lệch schema giữa cleaning và index; đóng băng test set cho cả 3 nhánh | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Thành viên 5 |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| ------------- | ---------------- |
| `LLM_PROVIDER` | `gemini` |
| `LLM_MODEL` | `gemini-2.5-flash` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (chạy local, không tốn API) |
| Số lượng Crossref records | `max_results = 24` |
| Retrieval `top_k` | `4` |
| Freshness threshold | `180` ngày |
| Random seed | `42` — dùng ở `build_test_set` (`df.sample(random_state=42)`) và `corrupt_clean_dataframe` (`random.seed(42)`) |

Query: `agentic retrieval augmented generation large language model`
Filter: `from-pub-date:2026-02-07,has-abstract:true` (ngày cắt được tính động = hôm nay − 180 ngày)
LLM judge chạy ở `temperature=0.0`.

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

Hai lệnh phải chạy **theo đúng thứ tự này**: `corruption_flow.py` đọc `data/results/baseline_metrics.json` ngay dòng đầu, nên chạy trước sẽ fail tại `read_json`.

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----- | ---------- | ------------------------- | ---------- |
| Baseline pipeline | Thành công | 2026-08-06 14:53 | `data/results/baseline_metrics.json` (72 samples), `data/reports/phase1_report.md`, 2 file trong `data/quality/` |
| Corruption flow | Thành công | 2026-08-06 15:09 | `data/results/{corrupted,repaired}_metrics.json`, `corruption_log.json`, `data/reports/corruption_report.md`, 4 file trong `data/quality/` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| ---------- | ------- |
| Source | Crossref REST API — `https://api.crossref.org/works` |
| Query/filter | `query=agentic retrieval augmented generation large language model`, `filter=from-pub-date:2026-02-07,has-abstract:true`, `rows=24` |
| Thời điểm lấy dữ liệu | Snapshot trong `data/raw/`; `latest_published` = `2026-08-01`, `oldest_published` = `2026-02-12` |
| Số record nhận được | 24 raw records → 24 clean rows (không record nào bị loại ở bước cleaning) |
| Cơ chế retry/backoff | Tối đa 4 lần với status 429/500/502/503/504; ưu tiên header `Retry-After` (hỗ trợ cả dạng giây lẫn HTTP-date), fallback exponential `2^attempt` giới hạn 8s; timeout (5s connect, 30s read) |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| ------ | ------------ | --------- | ------- | ------------------- |
| `paper_id` | str | Có | DOI đã chuẩn hóa, dùng làm document ID | Loại record nếu không khớp regex `^10\.\d{4,9}/\S+$`; bỏ tiền tố `https://doi.org/`, `doi:` |
| `title` | str | Có | Tiêu đề paper | Loại record nếu rỗng hoặc sau khi clean còn < 5 ký tự |
| `summary` | str | Có | Abstract đã bóc khỏi markup JATS | Loại record nếu rỗng; markup hỏng thì fallback sang regex xóa tag |
| `authors` → `authors_joined` | list[str] → str | Không | Tác giả, join bằng `", "` | Rỗng nếu thiếu — không bịa dữ liệu |
| `categories` → `categories_joined` | list[str] → str | Không | Chủ đề từ trường `subject` của Crossref | **Thực tế rỗng toàn bộ 24 record**, xem ghi chú dưới |
| `published` | str (ISO) | Không | Ngày xuất bản; thử lần lượt `published` → `published-online` → `published-print` → `issued` → `created` | `age_days = None` nếu không parse được |
| `age_days` | int/None | Không | Số ngày so với thời điểm chạy | `None`, và quality check dùng `fillna(0)` nên không bị tính là stale |
| `text_for_embedding` | str | Có | Chuỗi đưa vào MiniLM | Sinh từ title + summary + authors |
| `abs_url`, `pdf_url` | str | Không | Link landing/PDF | Bù ở tầng pipeline (`_ensure_index_columns`), rỗng nếu không có |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| ------- | ----------------- | ---------------------: | ------------- |
| Loại record thiếu `paper_id`/`title`/`summary` | Completeness | 0 (raw đã lọc sẵn ở `parse_crossref_payload`) | 24 raw → 24 clean, so `crossref_records.json` với `papers_clean.json` |
| Loại record có title < 5 ký tự | Validity | 0 | Như trên |
| Chuẩn hóa whitespace (`" ".join(value.split())`) | Consistency | 24 (áp cho mọi record) | So `summary` trong raw và clean |
| Dedupe theo `paper_id`, giữ bản đầu | Uniqueness | 0 ở baseline; bắt được 2 ở corrupted | `phase1_quality.json` `duplicate_paper_id: 0` so với `corrupted_quality.json`: `2` |
| Sort giảm dần theo `published` | — | 24 | `freshness_report.json` `latest_published` = `2026-08-01` |

**Ghi chú quan trọng về `categories`:** Crossref không trả trường `subject` cho bất kỳ record nào trong bộ 24 paper này, nên `categories_joined` rỗng toàn bộ. Hệ quả trực tiếp: `build_test_set` bỏ qua nhóm câu hỏi `categories` (code chủ động skip khi ground truth rỗng thay vì ghi `NaN` vào test set), nên test set có 72 câu chứ không phải 96 — chỉ còn 3 nhóm × 24 paper.

**`text_for_embedding`, document ID và `age_days`:**

`text_for_embedding = title + "\n" + summary + "\n" + authors_joined`. Gộp cả ba thay vì chỉ dùng abstract để câu hỏi dạng "paper tên X" vẫn match được qua title, và câu hỏi về tác giả có tín hiệu trong vector. Đây cũng chính là lý do blank summary gây tác động kép — vừa hỏng câu trả lời vừa hỏng vector.

Document ID trong ChromaDB là `f"{paper_id}::{index}"` chứ không phải `paper_id` trần, vì sau corruption dataset có `paper_id` trùng lặp và Chroma yêu cầu ID duy nhất. `paper_id` gốc được giữ trong metadata để đối chiếu với `ground_truth_doc_ids`.

`age_days = (run_date − published).days`, tính lúc chạy chứ không lưu cứng, nên freshness luôn phản ánh thời điểm chạy thật.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| ---------- | ---------------- |
| Số câu hỏi | 72 |
| Các `question_type` | `summary` (24), `authors` (24), `date` (24). `categories` bị bỏ vì Crossref không trả `subject` |
| Ground-truth document ID | `ground_truth_doc_ids = [paper_id]` của chính paper sinh ra câu hỏi; `retrieval_hit` = true khi ID này nằm trong top-k |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB `PersistentClient` tại `data/chroma/`; 3 collection: `papers-baseline`, `papers-corrupted`, `papers-repaired`, đều `space=cosine` |
| Retrieval `top_k` | 4 |
| LLM provider/model | `gemini` / `gemini-2.5-flash`, `temperature=0.0`, structured output theo schema `JudgeVerdict` |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` — 72 sample, sinh 1 lần với `random_state=42` |

**Vì sao giữ nguyên test set cho cả ba trạng thái:**

Nếu test set đổi giữa các lần đo thì không còn phân biệt được chênh lệch metric đến từ chất lượng dữ liệu hay từ việc bộ câu hỏi mới khó hơn. Giữ cố định biến test set thành hằng số, để biến duy nhất thay đổi giữa 3 lần đo là chất lượng corpus. Trong code, `corruption_flow.py` truyền đúng `settings.paths.eval_testset` cho cả hai lần `evaluate_pipeline` và không gọi `build_test_set`; `phase1.py` chỉ sinh mới khi file chưa tồn tại hoặc khi bật `REFRESH_TEST_SET`.

Có một hệ quả cần nói rõ để không bị hiểu nhầm là bug: sau corruption, 1 record bị xóa nhưng test set **vẫn giữ** 3 câu hỏi về nó. Đó chính là cơ chế đo tác động của việc mất dữ liệu, và là nguồn gốc của con số `retrieval_hit_rate = 69/72 = 0.9583`.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| -------- | ------------------ | ---------- | ------- |
| Raw response/records | `data/raw/` | Có | `crossref_response.json` (payload thô) + `crossref_records.json` (24 record đã parse) |
| Cleaned dataset | `data/clean/` | Có | `papers_clean.{csv,json}` — 24 dòng, 10 cột. Kèm cả bản corrupted và repaired |
| Embedding manifest/index | `data/embeddings/` | Có | 3 manifest JSON chứa `collection_name`, `persist_path`, `documents`; index nhị phân ở `data/chroma/` |
| Evaluation set | `data/eval/` | Có | `test_set.json` — 72 sample |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Kèm `baseline_answers.json` (672.893 byte, chi tiết từng câu) |
| Quality/freshness | `data/quality/` | Có | 6 file JSON cho 3 trạng thái |
| Baseline report | `data/reports/phase1_report.md` | Có | Kèm `corruption_report.md` |
| Agent demo answers | `data/results/agent_demo_answers.json` | **Thiếu** | Path có khai báo ở `config.py:98` nhưng không module nào ghi vào — xem mục 12 |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| ------ | -------: | --------- |
| `retrieval_hit_rate` | 1.0000 | Mọi câu hỏi đều lấy đúng paper vào top-4. Cần đọc kèm ngữ cảnh: corpus chỉ 24 tài liệu và `top_k=4` nghĩa là mỗi query trả về 1/6 corpus, nên đây là bài toán retrieval dễ |
| `mean_token_f1` | 0.7568 | Câu trả lời trùng phần lớn token với ground truth nhưng không khớp hoàn toàn. Chủ yếu do nhóm `summary`: `qa.py` chỉ trả về câu đầu tiên của abstract trong khi ground truth là toàn bộ abstract |
| `judge_accuracy` | 0.6944 | 50/72 câu được LLM judge chấm là đúng về mặt nội dung |
| `mean_judge_score` | 3.9583 | Trên thang 1–5. Cao hơn `judge_accuracy` vì nhiều câu được chấm 3 điểm — đúng một phần nhưng không đủ để gắn cờ `correct` |
| Ragas | N/A | Bị skip: `metrics.py` yêu cầu `RUN_RAGAS=1` mới chạy. Ngoài ra `ragas` trong môi trường hiện tại import lỗi `ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'`; code có sẵn shim để vá nhưng nhóm **chưa xác minh** shim hoạt động |

Khoảng cách giữa `retrieval_hit_rate` 1.0 và `mean_token_f1` 0.7568 là kết quả đáng chú ý nhất của baseline: retrieval hoàn hảo nhưng câu trả lời chỉ đạt ~76%. Điều này định vị điểm yếu nằm ở khâu sinh câu trả lời chứ không phải khâu tìm tài liệu.

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ----- | ----------------- | -------------- | ---------------- | ---------- |
| `missing_paper_id` | Completeness | = 0 | Pass — 0 | `data/quality/phase1_quality.json` |
| `duplicate_paper_id` | Uniqueness | = 0 | Pass — 0 | `phase1_quality.json` |
| `missing_title` | Completeness | = 0 | Pass — 0 | `phase1_quality.json` |
| `empty_summary` | Completeness | = 0 | Pass — 0 | `phase1_quality.json` |
| `stale_rows` | Timeliness | = 0 (`age_days` ≤ 180) | Pass — 0 | `phase1_quality.json` |
| `passed` (tổng hợp) | — | true | **Pass** | `phase1_quality.json` |

Cả 5 check đều là hand-rolled bằng pandas trong `src/observability/quality.py`. `great-expectations` có trong `pyproject.toml` và thư mục `data/quality/gx/` đã được tạo sẵn, nhưng nhóm chưa dùng tới.

### Freshness

| Thuộc tính | Giá trị |
| ---------- | ------- |
| Freshness được đo tại | Cleaned dataset (`data/clean/papers_clean.json`), sau bước cleaning và trước bước index |
| Timestamp mới nhất | `2026-08-01T00:00:00+00:00` |
| Timestamp cũ nhất | `2026-02-12T00:00:00+00:00` |
| Ngưỡng freshness | 180 ngày (`freshness_threshold_days`) |
| Trạng thái baseline | **Fresh** (`is_fresh: true`) |
| Lý do | `stale_rows = 0` trên 24 dòng. Hợp lý vì filter Crossref `from-pub-date` được tính động bằng chính ngưỡng 180 ngày, nên mọi record lấy về đều nằm trong cửa sổ. Đây là ràng buộc kép: filter ở ingestion và check ở observability dùng chung một hằng số |

Hai tín hiệu này bắt hai loại lỗi khác nhau và **không thay thế được cho nhau**: quality checks soi tính toàn vẹn nội tại (trùng, thiếu, rỗng) không phụ thuộc thời gian; freshness soi quan hệ giữa dữ liệu và thời gian. Bằng chứng cụ thể trong bài: quality hoàn toàn mù trước `stale_date`, còn freshness hoàn toàn mù trước `duplicate_paper_id`.

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ---------- | -------- | ----------------: | ---------------------- | ---------------- | ----------- |
| Drop latest records | `iloc[1:]` trên df đã sort giảm dần theo ngày → xóa record mới nhất | 1 | `total_rows` giảm; `latest_published` lùi lại | `latest_published` lùi từ `2026-08-01` về `2026-07-13`; **3 câu hỏi mất hit vĩnh viễn** → `retrieval_hit_rate` 1.0 → 0.9583 | Dựng lại từ raw snapshot |
| Blank summary | Gán `""` cho 10% số dòng | 2 | `empty_summary > 0` | `corrupted_quality.json`: `empty_summary: 2`. Tác động kép — vừa làm câu trả lời rỗng vừa làm hỏng vector | Như trên |
| Inject noise vào title | Thay 1 ký tự ngẫu nhiên bằng ký tự trong `!@#$%` | 2 | Không check nào bắt trực tiếp | Không đổi tín hiệu quality; ảnh hưởng gián tiếp qua embedding và exact-title lookup | Như trên |
| Truncate title | Cắt còn 10 ký tự + `"..."` | 2 | Không check nào bắt trực tiếp | Như trên. Làm hỏng nhánh `index.lookup()` theo exact title trong `qa.py` | Như trên |
| Stale publication date | Trừ 1825 ngày (5 năm) khỏi `published` và cộng vào `age_days` | 2 | `stale_rows > 0`, `is_fresh: false` | `corrupted_freshness.json`: `stale_rows: 2`, `is_fresh: false`, `oldest_published` lùi về `2021-03-16` | Như trên |
| Duplicate rows | `sample(n=2, random_state=42)` rồi concat | 2 | `duplicate_paper_id > 0` | `corrupted_quality.json`: `duplicate_paper_id: 2`, `total_rows` = 25 | Như trên |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: **Có**
- Nhận xét: log ghi đủ 6 loại corruption kèm `type`, `count` và `description`. Hạn chế: log **không ghi `paper_id` cụ thể** của các record bị tác động và không ghi tham số (tỷ lệ 5%/10%, seed 42), nên muốn truy vết chính xác record nào bị đụng vẫn phải diff `papers_clean.json` với `papers_clean_corrupted.json`. Đây là điểm nên cải thiện.

**Vì sao repair là phục hồi thật chứ không phải che kết quả lỗi:**

Repair **không** vá từng ô hỏng trong DataFrame corrupted. Thay vào đó `corruption_flow.py` đọc lại `data/raw/crossref_records.json` rồi chạy đúng `build_clean_dataframe` mà baseline đã dùng — tức đi lại toàn bộ đường từ nguồn. Cách này có ba hệ quả có thể kiểm chứng: (1) nếu raw snapshot bị hỏng thì repair cũng hỏng theo, nên kết quả tốt là bằng chứng snapshot đáng tin; (2) kết quả deterministic, không phụ thuộc thứ tự hay mức độ corruption; (3) nếu repair chỉ "che" lỗi thì các quality check hand-rolled vẫn sẽ bắt được — nhưng `repaired_quality.json` cho `passed: true` với cả 5 chỉ số về 0.

Điểm mấu chốt: `total_rows` của repaired trở lại đúng **24** chứ không phải 25. Nếu repair chỉ xử lý duplicate mà không dựng lại từ nguồn thì record bị xóa sẽ không thể quay lại, và `retrieval_hit_rate` sẽ mắc kẹt ở 0.9583.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| ------------- | -------: | --------: | -------: | ---------------------: | -----------: | -------- |
| `retrieval_hit_rate` | 1.0000 | 0.9583 | 1.0000 | −0.0417 (−4.2%) | 100% | Mất đúng 3/72 câu = 3 câu hỏi của 1 record bị xóa |
| `mean_token_f1` | 0.7568 | 0.6896 | 0.7568 | −0.0673 (−8.9%) | 100% | Giảm mạnh nhất. Nhạy nhất vì đo trực tiếp trên câu chữ |
| `judge_accuracy` | 0.6944 | 0.6389 | 0.6944 | −0.0556 (−8.0%) | 100% | Giảm 4 câu (50 → 46 câu đúng) |
| `mean_judge_score` | 3.9583 | 3.6944 | 3.9583 | −0.2639 (−6.7%) | 100% | Biên độ nhỏ hơn vì thang 1–5 nén bớt chênh lệch so với F1 liên tục |
| Quality checks pass/fail | `true` | `false` | `true` | Đảo trạng thái | 100% | Corrupted: `duplicate_paper_id: 2`, `empty_summary: 2`, `stale_rows: 2`, 25 dòng |
| Freshness status | `true` | `false` | `true` | Đảo trạng thái | 100% | `oldest_published` `2026-02-12` → `2021-03-16` → `2026-02-12` |

**Hai kết luận nhân quả có artifact hỗ trợ:**

1. **Corruption** (6 kịch bản trong `corruption_log.json`, tổng cộng ~9/24 record bị đụng) → **quality và freshness đều đảo trạng thái**: `phase1_quality.json` `passed: true` → `corrupted_quality.json` `passed: false` với 3 vi phạm đếm được (`duplicate_paper_id: 2`, `empty_summary: 2`, `stale_rows: 2`), và `is_fresh: true` → `false` → **cả 4 agent metric đều giảm**, rõ nhất là `mean_token_f1` 0.7568 → 0.6896.

2. **Repair từ raw snapshot** (`load_raw_records` → `build_clean_dataframe`, không vá thủ công) → **quality và freshness phục hồi hoàn toàn**: `repaired_quality.json` `passed: true` với cả 5 chỉ số về 0, `repaired_freshness.json` `is_fresh: true`, `total_rows` về đúng 24 → **cả 4 agent metric phục hồi 100%**, trùng baseline tới từng chữ số thập phân.

**Kết quả khác kỳ vọng và cách nhóm đã kiểm tra:**

*Thứ nhất, biên độ giảm nhỏ hơn dự đoán.* Nhóm kỳ vọng metrics rơi mạnh hơn nhiều, nhưng `retrieval_hit_rate` chỉ giảm 4.2%. Giả thuyết đầu tiên là corruption không thực sự được áp dụng. Nhóm kiểm tra bằng cách đọc `corruption_log.json` và `corrupted_quality.json`: cả 6 kịch bản đều có ghi nhận, và quality bắt đúng 2 duplicate + 2 empty summary + 2 stale — tức corruption có chạy thật. Nguyên nhân thật nằm ở **tỷ lệ**: `max(1, int(24 * 0.1))` chỉ ra 2 dòng mỗi loại trên corpus 24 dòng, tổng cộng chưa tới 10 dòng bị đụng. Cộng thêm `top_k=4` trên corpus 24 tài liệu nghĩa là mỗi query lấy về 1/6 corpus, nên retrieval rất khó trượt.

*Thứ hai, repaired trùng baseline tuyệt đối.* Không lệch một chữ số nào trên cả 4 metric, ban đầu làm nhóm nghi pipeline copy nhầm file. Kiểm tra lại thì thấy hợp lý: repair đọc cùng snapshot raw, chạy cùng `build_clean_dataframe` deterministic, embed bằng cùng model MiniLM chạy local, và judge chạy ở `temperature=0.0`. Đầu vào giống hệt thì đầu ra phải giống hệt. Nhóm đối chiếu thêm kích thước file — `repaired_answers.json` và `baseline_answers.json` đều 672.893 byte — củng cố rằng đây là tính deterministic chứ không phải copy nhầm.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Baseline pipeline crash ngay tại câu hỏi **đầu tiên** của `evaluate_pipeline`, tức ngay sau khi `LocalEmbeddingIndex.build` đã báo thành công:

```
File "src/retrieval/index.py", line 143, in search
    results = self.collection.query(
chromadb.errors.NotFoundError: Error getting collection:
Collection [6dc7eb0d-770b-4a8b-9cea-0f0c0032e47f] does not exist.
```

  Toàn bộ `data/results/`, `data/quality/`, `data/reports/` rỗng.

- **Nguyên nhân:** UUID trong thông báo lỗi **không còn tồn tại** trong bảng `collections` của `chroma.sqlite3` — truy vấn sqlite trực tiếp cho thấy collection `papers-baseline` lúc đó mang UUID khác với 2 segment hợp lệ. Nghĩa là `build()` đã tạo collection mới thành công, nhưng handle mà `__init__` lấy về qua `get_collection` lại trỏ tới collection cũ đã bị `delete_collection` xóa ở đầu hàm `build`. Bối cảnh: `data/chroma/` khi đó đã tích tụ 5 thư mục UUID mồ côi từ các lần chạy dở trước đó.

- **Cách xử lý:** Nhóm viết 2 kịch bản repro độc lập để kiểm tra giả thuyết "code `build()` sai": (a) create → reopen bằng client thứ hai → query; (b) collection đã tồn tại sẵn → delete → create → reopen → query. **Cả hai đều pass**, không tái hiện được lỗi. Kết luận: chuỗi `delete → create → get_collection` bản thân nó không sai, lỗi đến từ state cũ tồn đọng. Nhóm **quyết định không sửa `index.py`** để tránh thay đổi code dựa trên chẩn đoán chưa chắc chắn, và chạy lại pipeline trên state đã được dựng lại nhất quán.

- **Cách xác minh:** chạy lại `script/run_phase1.py`, lần này **không pipe qua `tail`**. Đây là chi tiết quan trọng: lần chạy đầu dùng `python script/run_phase1.py 2>&1 | tail -30` khiến shell trả về exit code của `tail` chứ không phải của Python, nên pipeline đã crash mà vẫn báo exit 0 — chỉ đến khi kiểm tra `data/results/` thấy rỗng mới phát hiện. Sau khi bỏ `| tail`: exit 0 thật, `baseline_metrics.json` với 72 samples, `data/quality/` và `data/reports/` đầy đủ.

- **Rủi ro còn lại:** nguyên nhân đã khoanh vùng được là state cũ, nhưng **cơ chế chính xác khiến `get_collection` trả về handle cũ chưa chứng minh được** vì cả 2 repro đều pass. Nếu tái diễn, bước tiếp theo có thể kiểm chứng là cho `build()` truyền thẳng object collection vừa tạo sang `__init__` thay vì gọi `get_collection` lần nữa.

**Một vấn đề tích hợp thứ hai** đáng ghi nhận: `testset.py` sinh câu hỏi `"Who are the authors of the paper titled '...'?"` trong khi `qa.py:_extract_answer` định tuyến bằng match chuỗi cứng `"who authored"` / `"list the authors"`. Phrasing cũ không match cụm nào nên rơi xuống nhánh mặc định trả về câu đầu của abstract — nghĩa là toàn bộ 24 câu hỏi về tác giả sai về mặt cấu trúc bất kể retrieval tốt đến đâu. Nhóm sửa phrasing trong `testset.py` (module thuộc phần sinh viên tự làm theo Guide Bước 5) thay vì sửa `qa.py` (code tham khảo cho sẵn theo Bước 8), kèm comment giải thích ràng buộc. Lưu ý trung thực: **không có số liệu "trước khi sửa" để so sánh định lượng**, vì lần chạy đầu bị crash bởi lỗi ChromaDB ở trên trước khi kịp ghi metrics. Lập luận ở đây là lập luận cấu trúc — nhánh xử lý `authors` trước đó là không thể tới được — chứ không phải kết luận từ hai lần đo.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| ----------------- | --------- | --------------------------------- |
| **Agent LangChain chưa được gọi trong pipeline.** `build_agent` và `run_agent_question` trong `src/retrieval/agent.py` chỉ được re-export ở `src/retrieval/__init__.py`, không nơi nào gọi. `evaluate_pipeline` dùng `qa.answer_question` — thuần retrieval + bóc metadata, không có LLM sinh câu trả lời, không dùng tool | Không có artifact chứng minh agent chạy được; `config.py:98` khai báo `demo_answers` nhưng file `data/results/agent_demo_answers.json` không tồn tại | Thêm một bước gọi agent vào `phase1.py` sau khi build index, chạy 3–4 câu trong đó có 1 câu ngoài corpus. Đo bằng: agent có gọi tool trước khi trả lời không, và có nói thẳng "không có trong corpus" thay vì bịa không |
| **`ragas` bị skip** ở cả 3 trạng thái | Thiếu `faithfulness`, `answer_relevancy`, `context_precision`, `context_recall` — Guide Bước 10 có liệt kê `ragas` là chỉ số cần quan tâm | Bật `RUN_RAGAS=1`. Riêng `faithfulness` trả lời được câu hỏi mà 4 metric hiện tại không chạm tới: khi summary bị blank, agent trả lời rỗng hay bắt đầu bịa? Cần xác minh trước cái shim `langchain_community.chat_models.vertexai` trong `metrics.py` |
| **Corpus quá nhỏ (24) và `top_k=4` quá rộng** | Mỗi query lấy về 1/6 corpus nên retrieval gần như không thể trượt — đây là lý do `retrieval_hit_rate` chỉ giảm 4.2% dù corruption có hiệu lực thật | Tăng `max_results` lên 100+, giảm `top_k` xuống 2, tăng tỷ lệ corruption lên 30%. Đo bằng biên độ giảm của `retrieval_hit_rate` — nếu giả thuyết đúng, biên độ phải lớn hơn rõ rệt |
| **`corruption_log.json` không ghi `paper_id` bị tác động** | Không truy vết được record nào bị đụng nếu không diff thủ công 2 file clean | Bổ sung danh sách `paper_id` và tham số (tỷ lệ, seed) vào mỗi entry log. Xác minh bằng cách đối chiếu log với diff `papers_clean.json` ↔ `papers_clean_corrupted.json` |
| **`great-expectations` là dependency thừa** | Có trong `pyproject.toml`, `data/quality/gx/` được tạo sẵn nhưng rỗng; quality checks hand-rolled bằng pandas | Hoặc chuyển 5 check sang GX expectation suite để có validation result chuẩn, hoặc gỡ khỏi dependency |
| **Vector store persist dễ lệch state** | Đã gây crash toàn bộ evaluation một lần (mục 11); `data/chroma/` tích tụ thư mục UUID mồ côi | Coi `data/chroma/` là cache dùng một lần — xóa sạch trước mỗi lần build. Xác minh bằng cách chạy pipeline 3 lần liên tiếp trên thư mục sạch và trên thư mục bẩn, so tỷ lệ thành công |
| **`_ensure_index_columns` bị lặp** ở `phase1.py:25` và `corruption_flow.py:15` | Sửa một chỗ quên chỗ kia sẽ gây lệch giữa baseline và repaired | Đưa về `core/utils.py` hoặc `ingestion/cleaning.py`. Xác minh bằng việc `repaired_metrics.json` vẫn trùng `baseline_metrics.json` sau khi refactor |

## 13. Checklist trước khi nộp

- [ ] Thông tin nhóm và repository chính xác.
- [ ] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json`, 72 sample).
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
