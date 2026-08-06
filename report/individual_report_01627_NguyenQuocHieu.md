# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Quốc Hiệu       |
| MSSV               | 2A202601627                     |
| Khóa/Lớp         | K3              |
| Tên nhóm         | A2-2     |
| Vai trò chính    | Integration & Comparison                 |
| Repository         | https://github.com/wokhyu/K3_Day10_A22_DataPipeline |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Baseline orchestration | `src/pipelines/phase1.py` (`main`, `_load_or_fetch_raw_records`, `_ensure_index_columns`, `_load_or_build_testset`, `_source_summary`) | `data/raw/crossref_records.json` từ nhóm ingestion | `data/clean/`, `data/embeddings/`, `data/results/baseline_metrics.json`, `data/results/baseline_answers.json`, `data/quality/`, `data/reports/phase1_report.md` | Hoàn thành |
| Corruption & repair orchestration | `src/pipelines/corruption_flow.py` (`main`, `_ensure_index_columns`) | `data/clean/papers_clean.json`, `data/results/baseline_metrics.json`, raw snapshot | `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_log.json`, `data/reports/corruption_report.md` | Hoàn thành |
| Entrypoint & reproducibility | `script/run_phase1.py`, `script/run_corruption_flow.py` | — | 2 lệnh chạy được từ project root, tự set `sys.path` tới `src/` | Hoàn thành |
| Integration bug fix | `src/evaluation/testset.py` (`build_test_set`) | Cleaned DataFrame | Test set 72 sample khớp intent-matching của `qa.py` | Hoàn thành |
| Chạy LangChain agent (`agent.py`) trong pipeline | `src/retrieval/agent.py`, path `demo_answers` trong `config.py` | Baseline index | `data/results/agent_demo_answers.json` | **Chưa hoàn thành** — xem mục 3 |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------ | ------------------------------------ | ---------- |
| Debug lỗi `chromadb.errors.NotFoundError` chặn toàn bộ evaluation | `src/retrieval/index.py` (module retrieval) | Khoanh vùng được nguyên nhân là state cũ trong `data/chroma`, loại trừ bug logic bằng 2 kịch bản repro; **không phải sửa code** của module bạn khác. Chi tiết mục 6 |
| Sửa lệch contract giữa test set và agent | `src/evaluation/testset.py` ↔ `src/retrieval/qa.py` | 24/72 câu hỏi `authors` trước đó không thể trả lời đúng về mặt cấu trúc, nay đã khớp nhánh xử lý |
| Xác minh output của quality/reporting | `src/observability/quality.py`, `reporting.py` | Đối chiếu 6 file JSON trong `data/quality/` với 2 report markdown, số liệu khớp nhau |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------- | ----------------- |
| Ghép 9 bước của baseline pipeline thành 1 lệnh chạy | `src/pipelines/phase1.py` | `baseline_metrics.json`: 72 samples, hit_rate 1.0, token_f1 0.7568 | `python script/run_phase1.py` → exit 0, 7 artifact được ghi |
| Ghép 8 bước corruption → repair → comparison | `src/pipelines/corruption_flow.py` | `corruption_report.md` so sánh 3 trạng thái | `python script/run_corruption_flow.py` → exit 0 |
| Sửa lệch phrasing test set ↔ agent | `src/evaluation/testset.py` | `data/eval/test_set.json` 72 sample (24 summary / 24 authors / 24 date) | `REFRESH_TEST_SET=1` rồi đọc lại file, câu hỏi authors đổi thành `"Who authored the paper titled '...'?"` |
| Gỡ blocker ChromaDB chặn evaluation | log chạy phase 1 | Pipeline chạy trọn vẹn sau khi state được dựng lại | So sánh 2 lần chạy: lần 1 crash, lần 2 exit 0 và sinh đủ artifact |

**Một output cụ thể phần việc của tôi tạo ra:**

`data/reports/corruption_report.md` — report này chỉ tồn tại được khi cả 3 nhánh (baseline / corrupted / repaired) chạy xong trong cùng một lần và cùng dùng một test set. Nó là bằng chứng tích hợp: `generate_corruption_report` nhận `baseline_metrics` đọc từ file của phase 1, còn `corrupted_metrics` và `repaired_metrics` là object trả về ngay trong tiến trình, nên nếu phase 1 chưa chạy thì corruption flow sẽ fail ở `read_json` ngay dòng đầu. Việc report này sinh ra được chứng minh thứ tự phụ thuộc giữa 2 pipeline là đúng.

**Phần chưa hoàn thành (khai báo trung thực):**

1. `src/retrieval/agent.py` (`build_agent`, `run_agent_question`) **chưa được gọi ở bất kỳ pipeline hay script nào**. `evaluate_pipeline` dùng `qa.answer_question` — vốn chỉ là retrieval + bóc metadata, không có LLM sinh câu trả lời và không dùng tool. `config.py` có khai báo path `demo_answers` (`data/results/agent_demo_answers.json`) nhưng không module nào ghi vào đó, nên file này không tồn tại. Tôi không ghi nhận agent "chạy tốt" vì chưa có artifact chứng minh.
2. `ragas` đang bị skip ở cả 3 file metrics (`"skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."`). Ngoài ra `ragas` trong `.venv` hiện import lỗi (`ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'`); `metrics.py` có sẵn shim để vá, nhưng tôi **chưa xác minh** shim đó chạy thật vì chưa bật `RUN_RAGAS=1`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Các thành viên khác viết từng module độc lập: ingestion, cleaning, testset, index, quality, reporting. Vai trò của tôi là làm cho chúng chạy được thành một chuỗi có thứ tự đúng, tái lập được, và quan trọng nhất là **so sánh được** — tức baseline, corrupted, repaired phải được đo trên cùng một thước đo thì con số mới có ý nghĩa. Nếu mỗi nhánh tự sinh test set riêng thì ba cột số trong report sẽ không so sánh được với nhau.

### Cách triển khai

**Thứ tự phụ thuộc trong `phase1.py`.** 9 bước được xếp theo dependency chứ không theo thứ tự tùy ý: raw → clean → index → test set → evaluate → quality → freshness → report. Bước index phải đứng trước test set vì `evaluate_pipeline` cần cả hai; bước report đứng cuối vì nó tiêu thụ output của cả evaluate lẫn quality/freshness.

**Cache có kiểm soát.** `_load_or_fetch_raw_records` và `_load_or_build_testset` dùng cùng một quy tắc: chỉ gọi lại source/rebuild khi người dùng bật cờ (`REFRESH_SOURCE`, `REFRESH_TEST_SET`) hoặc khi file chưa tồn tại. Lý do là gọi Crossref mỗi lần chạy sẽ khiến corpus thay đổi theo thời gian, làm baseline hôm nay không so sánh được với corrupted hôm sau. Cache mặc định giữ corpus đứng yên, cờ môi trường cho phép chủ động làm mới khi cần.

**Vá schema không đồng nhất.** `build_clean_dataframe` không trả về `abs_url`/`pdf_url` nhưng `LocalEmbeddingIndex._build_documents` lại đọc hai cột này khi dựng metadata. `_ensure_index_columns` map ngược từ `PaperRecord` theo `paper_id` để bù vào. Đây là chỗ hai module của hai người gặp nhau và là lỗi tích hợp điển hình — sửa ở tầng orchestration thay vì bắt một trong hai module đổi contract.

**Test set đóng băng cho cả 3 nhánh.** `corruption_flow.py` truyền đúng `settings.paths.eval_testset` cho cả lần evaluate corrupted lẫn repaired, không sinh mới. Đây là điều kiện bắt buộc để 3 cột metrics trong `corruption_report.md` có thể đặt cạnh nhau.

**Repair dựng lại từ raw chứ không "sửa" corrupted.** Bước 6 của corruption flow gọi lại `build_clean_dataframe(load_raw_records(...))` — tức đi lại đúng đường của phase 1 từ snapshot gốc, thay vì cố vá từng ô hỏng trong DataFrame corrupted. Cách này cho kết quả deterministic và chứng minh được raw snapshot là nguồn phục hồi đáng tin.

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | ------- |
| Input | `data/raw/crossref_records.json` (list `PaperRecord`, 11 trường); `.env` cung cấp `LLM_PROVIDER`/`LLM_MODEL` + API key tương ứng |
| Output | `papers_clean.{csv,json}`; `papers_embeddings*.json` (manifest chứa `collection_name`, `persist_path`, `documents`); `baseline/corrupted/repaired_metrics.json` (5 khóa + `ragas`); `*_answers.json`; `corruption_log.json`; 2 report markdown |
| Module phụ thuộc | `ingestion.crossref`, `ingestion.cleaning`, `ingestion.corruption`, `evaluation.testset`, `evaluation.metrics`, `retrieval.index`, `observability.quality`, `observability.reporting` |
| Module sử dụng output | `observability.reporting` (đọc metrics + quality + freshness); `corruption_flow` đọc `baseline_metrics.json` do `phase1` ghi |
| Điều kiện lỗi cần xử lý | Thiếu cột `abs_url`/`pdf_url` sau cleaning (đã xử lý bằng `_ensure_index_columns`); chạy corruption flow trước phase 1 (fail sớm tại `read_json`); LLM judge lỗi/hết quota (`metrics.py` fallback sang heuristic theo token F1); collection ChromaDB ở state cũ (mục 6) |

### Cách xác minh

```bash
# Baseline (regenerate test set sau khi sửa phrasing)
REFRESH_TEST_SET=1 PYTHONIOENCODING=utf-8 PYTHONPATH=src .venv/Scripts/python.exe script/run_phase1.py

# Corruption → repair → comparison
PYTHONIOENCODING=utf-8 PYTHONPATH=src .venv/Scripts/python.exe script/run_corruption_flow.py
```

- **Kết quả mong đợi:** cả 2 lệnh exit 0; sinh đủ artifact ở `data/clean/`, `data/embeddings/`, `data/eval/`, `data/results/`, `data/quality/`, `data/reports/`; metrics của repaired trở về mức baseline.
- **Kết quả thực tế:** đạt. `data/results/` có 7 file, `data/quality/` có 6 file JSON, `data/reports/` có 2 file markdown. `repaired_metrics.json` trùng khít `baseline_metrics.json` tới từng chữ số, và `repaired_answers.json` cùng kích thước 672.893 byte với `baseline_answers.json`.
- **Artifact/log:** `data/reports/phase1_report.md`, `data/reports/corruption_report.md`, `data/results/*.json`, `data/quality/*.json`. Không file nào chứa API key — `.env` nằm trong `.gitignore`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi rà soát trước lúc chạy, tôi phát hiện test set và agent không khớp nhau. `testset.py` sinh câu hỏi `"Who are the authors of the paper titled '...'?"` và `"What topics does the paper titled '...' cover?"`, trong khi `qa.py:_extract_answer` định tuyến câu hỏi sang đúng trường metadata bằng cách match chuỗi cứng: `"who authored"`, `"list the authors"`, `"what categories"`, `"when was"`. Hai phrasing đầu không match cụm nào nên rơi xuống nhánh mặc định `first_sentence(metadata["summary"])` — nghĩa là mọi câu hỏi về tác giả đều bị trả lời bằng câu đầu tiên của abstract, sai về mặt cấu trúc bất kể retrieval tốt đến đâu.
- **Các phương án đã cân nhắc:**
  1. Sửa `qa.py` để nhận thêm các phrasing tự nhiên hơn (`"who are the authors"`, `"what topics"`).
  2. Sửa `testset.py` để câu hỏi sinh ra dùng đúng cụm mà `qa.py` đã hỗ trợ.
- **Phương án đã chọn:** phương án 2 — đổi phrasing trong `testset.py`, kèm comment giải thích ràng buộc để người sau không vô tình viết lại câu hỏi.
- **Lý do:** `Guide.md` Bước 8 ghi rõ `qa.py` và `agent.py` là *code tham khảo* đã cho sẵn, còn Bước 5 giao `testset.py` cho sinh viên tự hoàn thành. Sửa file thuộc phạm vi mình phụ trách giữ được ranh giới ownership, tránh xung đột khi merge với nhánh của thành viên khác, và thay đổi nhỏ hơn (3 dòng phrasing thay vì mở rộng logic match). Điểm đánh đổi tôi chấp nhận: câu hỏi trong test set nghe hơi máy móc hơn so với ngôn ngữ tự nhiên.
- **Bằng chứng quyết định phù hợp:** sau khi sửa, `retrieval_hit_rate` đạt 1.0 và `mean_token_f1` đạt 0.7568 trên 72 sample. **Tôi không có số liệu "trước khi sửa" để so sánh định lượng**, vì lần chạy đầu tiên bị crash bởi lỗi ChromaDB ở mục 6 trước khi kịp ghi metrics. Lập luận ở đây là lập luận cấu trúc — nhánh xử lý `authors` trước đó là *không thể tới được* với phrasing cũ — chứ không phải kết luận rút ra từ so sánh hai lần đo.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**

```
File "src/retrieval/index.py", line 143, in search
    results = self.collection.query(
chromadb.errors.NotFoundError: Error getting collection:
Collection [6dc7eb0d-770b-4a8b-9cea-0f0c0032e47f] does not exist.
```

  Lỗi ném ra tại câu hỏi **đầu tiên** trong `evaluate_pipeline`, tức ngay sau khi `LocalEmbeddingIndex.build` báo thành công. Toàn bộ `data/results/`, `data/quality/`, `data/reports/` rỗng.

- **Lệnh hoặc bước tái hiện:** `PYTHONPATH=src python script/run_phase1.py` trên một thư mục `data/chroma` đã tích tụ state từ nhiều lần chạy dở trước đó (`ls data/chroma` cho thấy 5 thư mục UUID mồ côi cạnh `chroma.sqlite3`).

- **Nguyên nhân gốc:** UUID trong thông báo lỗi (`6dc7eb0d`) **không còn tồn tại** trong bảng `collections` của `chroma.sqlite3` — kiểm tra trực tiếp bằng sqlite3 cho thấy collection `papers-baseline` lúc đó mang UUID khác (`0e32bb59`) với 2 segment hợp lệ. Nghĩa là `build()` đã tạo collection mới thành công, nhưng handle mà `__init__` lấy về qua `get_collection` lại trỏ tới collection cũ đã bị `delete_collection` xóa ở đầu hàm `build`. Đây là hệ quả của state cũ tồn đọng trong thư mục persist, không phải lỗi logic trong `index.py`.

- **Những gì đã loại trừ:** tôi viết 2 kịch bản repro độc lập để kiểm tra giả thuyết "code `build()` bị sai":
  1. create → reopen bằng `PersistentClient` thứ hai → query. **Pass**, cùng UUID, query đúng.
  2. Collection đã tồn tại sẵn từ tiến trình trước → delete → create → reopen bằng client mới → query. **Pass**.

  Cả hai đều không tái hiện được lỗi, nên tôi kết luận chuỗi `delete → create → get_collection` trong `index.py` bản thân nó không sai, và **quyết định không sửa `index.py`** — tránh thay đổi code của module người khác dựa trên chẩn đoán chưa chắc chắn.

- **Cách xử lý:** chạy lại pipeline trên state đã được `build()` của lần chạy lỗi ghi lại nhất quán. Không thay đổi dòng code nào.

- **Cách xác minh sau khi sửa:** chạy lại `script/run_phase1.py`, lần này **không pipe qua `tail`**. Kết quả: exit 0 thật, `baseline_metrics.json` với 72 samples, `data/quality/` và `data/reports/` được ghi đầy đủ.

- **Điều học được:** hai bài học, và bài học thứ hai làm tôi mất thời gian hơn bài học thứ nhất.

  1. **Vector store có persistent state là một nguồn lỗi ẩn.** Metrics có thể sai hoặc pipeline có thể chết vì thư mục persist bẩn chứ không vì code sai. Với pipeline cần tái lập, nên coi `data/chroma` là cache dùng một lần.
  2. **`cmd | tail` nuốt mất exit code.** Lần chạy đầu tôi dùng `python script/run_phase1.py 2>&1 | tail -30`, shell trả về exit code của `tail` chứ không phải của Python, nên tôi đã báo "exit code 0" trong khi pipeline thực ra đã crash. Chỉ đến khi kiểm tra `data/results/` thấy rỗng mới phát hiện. Từ đó tôi bỏ hẳn `| tail` khi chạy pipeline và luôn đối chiếu exit code với artifact thực tế trên đĩa.

- **Rủi ro còn lại:** nguyên nhân gốc đã khoanh vùng được là state cũ, nhưng **cơ chế chính xác khiến `get_collection` trả về handle cũ thì chưa chứng minh được** vì cả 2 repro đều pass. Nếu lỗi tái diễn, bước tiếp theo có thể kiểm chứng là: cho `build()` truyền thẳng object collection vừa tạo sang `__init__` thay vì gọi `get_collection` lần nữa — loại bỏ hoàn toàn lần tra cứu theo tên.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**
`fetch_source_records` gọi `GET https://api.crossref.org/works` với `query="agentic retrieval augmented generation large language model"` và `filter=from-pub-date:2026-02-07,has-abstract:true`, `rows=24`. Response thô được ghi xuống `crossref_response.json` **trước khi parse** — cố ý như vậy để nếu một item của publisher làm hỏng parser thì vẫn còn nguyên bằng chứng nguồn. `parse_crossref_payload` chuẩn hóa DOI, bóc text từ markup JATS trong abstract, và loại record thiếu DOI/title/abstract, ra `crossref_records.json`. `build_clean_dataframe` chuẩn hóa whitespace, join `authors`/`categories` thành chuỗi, parse `published` và tính `age_days` so với thời điểm chạy, dựng cột `text_for_embedding = title + summary + authors`, bỏ trùng theo `paper_id`, sắp xếp giảm dần theo ngày. Cuối cùng `LocalEmbeddingIndex.build` encode cột `text_for_embedding` bằng MiniLM (chạy local, không tốn API) và nạp vào ChromaDB với `space=cosine`, kèm metadata để `qa.py` bóc ra khi trả lời.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
Đây là hai phép đo tách rời nhau. `ground_truth_doc_ids` đo **retrieval**: `retrieval_hit` là true khi paper đúng nằm trong top-k trả về — chỉ quan tâm "có lấy đúng tài liệu không", không quan tâm câu chữ. `ground_truth` (nội dung) đo **answer**: `token_f1` tính overlap tập token, còn LLM judge chấm điểm 1–5 và cờ `correct`. Tách như vậy giúp chẩn đoán được lỗi nằm ở đâu: hit_rate cao mà F1 thấp nghĩa là retrieval ổn nhưng khâu sinh câu trả lời yếu — đúng với tình trạng hiện tại của bài (1.0 so với 0.7568).

**3. Quality checks khác freshness monitoring ở điểm nào?**
Quality checks soi **tính toàn vẹn nội tại** của bảng dữ liệu tại thời điểm chạy: thiếu `paper_id`, trùng `paper_id`, thiếu title, summary rỗng — sai thì sai ngay, không phụ thuộc hôm nay là ngày nào. Freshness soi **quan hệ giữa dữ liệu và thời gian**: `latest_published`, `oldest_published`, số dòng vượt ngưỡng 180 ngày. Một dataset có thể hoàn toàn sạch mà vẫn cũ. Trong bài này hai tín hiệu bắt được hai loại corruption khác nhau: quality bắt `duplicate_paper_id` và `empty_summary`, freshness bắt `stale_date` — cái mà quality không nhìn thấy.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
Vì nếu test set đổi thì không còn biết chênh lệch metrics đến từ dữ liệu xấu hay từ việc bộ câu hỏi mới khó hơn. Giữ test set cố định biến nó thành hằng số, để biến duy nhất thay đổi giữa 3 lần đo là chất lượng corpus. Đây cũng là lý do `corruption_flow.py` truyền `settings.paths.eval_testset` cho cả hai lần evaluate thay vì gọi `build_test_set`. Có một hệ quả cần lưu ý: sau corruption, 1 record bị xóa nhưng test set vẫn giữ câu hỏi về nó — đó chính là cách bài lab đo tác động của việc mất dữ liệu, chứ không phải lỗi.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**
Dựa trên 3 nhóm bằng chứng cùng lúc: (a) `repaired_quality.json` có `passed: true` với `duplicate_paper_id: 0`, `empty_summary: 0`; (b) `repaired_freshness.json` có `is_fresh: true`, `stale_rows: 0`, `oldest_published` trở lại `2026-02-12`; (c) `repaired_metrics.json` khớp `baseline_metrics.json`. Riêng (c) đủ mạnh vì repair đi lại đúng đường deterministic từ raw snapshot — nếu kết quả chỉ *gần* baseline thì phải nghi ngờ có thứ gì đó không tái lập được.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.0000 | 0.9583 | 1.0000 | Mất đúng 3/72 câu. Con số này khớp với việc 1 record bị xóa khỏi corpus nhưng câu hỏi về nó vẫn còn trong test set — mỗi paper sinh 3 câu hỏi |
| `mean_token_f1` | 0.7568 | 0.6896 | 0.7568 | Giảm 8.9%, mức giảm mạnh nhất trong các metric. Nhạy nhất vì đo trực tiếp trên câu chữ, nên summary bị blank và title bị nhiễu đập thẳng vào đây |
| `judge_accuracy` | 0.6944 | 0.6389 | 0.6944 | Giảm 4 câu. LLM judge khoan dung hơn token F1 vì chấm theo ngữ nghĩa, câu trả lời lệch chữ vẫn có thể được coi là đúng |
| `mean_judge_score` | 3.958 | 3.694 | 3.958 | Cùng xu hướng, biên độ nhỏ hơn. Thang 1–5 nén bớt chênh lệch so với F1 liên tục |
| Quality checks | `passed: true` | `passed: false` | `passed: true` | Corrupted: `duplicate_paper_id: 2`, `empty_summary: 2`, `stale_rows: 2`, tổng 25 dòng (24 − 1 xóa + 2 nhân bản) |
| Freshness status | `is_fresh: true` | `is_fresh: false` | `is_fresh: true` | `oldest_published` bị đẩy từ `2026-02-12` về `2021-03-16`; `latest_published` lùi từ `2026-08-01` về `2026-07-13` do record mới nhất bị xóa |

### Kết luận từ số liệu

1. **Data corruption** (6 kịch bản trong `corruption_log.json`: drop 1, blank_summary 2, inject_noise 2, truncate_title 2, stale_date 2, duplicate_rows 2) → **quality/freshness signal đổi trạng thái**: `passed` true → false và `is_fresh` true → false, với 3 vi phạm đếm được cụ thể → **agent metric giảm trên cả 4 chỉ số**, rõ nhất ở `mean_token_f1` 0.7568 → 0.6896.

2. **Repair action** (dựng lại từ `crossref_records.json` bằng `build_clean_dataframe`, không vá từng ô) → **quality/freshness phục hồi hoàn toàn**: `passed: true`, `is_fresh: true`, `total_rows` về đúng 24 → **agent metric phục hồi hoàn toàn**, trùng baseline tới từng chữ số thập phân trên cả 4 metric.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**

Xóa record (`drop`) là loại gây tổn thất *không thể cứu bằng retrieval tốt hơn*: 3 câu hỏi mất hit vĩnh viễn vì tài liệu đúng không còn tồn tại trong index — đây chính là 0.9583 = 69/72. Các corruption còn lại chỉ làm giảm chất lượng chứ không xóa khả năng trả lời.

Nhưng xét về **biên độ tác động lên câu trả lời**, `blank_summary` mới là loại nặng nhất. Lý do nằm ở `qa.py:_extract_answer`: nhánh mặc định trả về `first_sentence(metadata["summary"])`, nên summary rỗng đồng nghĩa câu trả lời rỗng và token F1 = 0 tuyệt đối. Nó còn đánh kép: `summary` cũng nằm trong `text_for_embedding`, nên record đó vừa mất khả năng trả lời vừa mất chất lượng vector.

`stale_date` thì ngược lại — làm `is_fresh` chuyển sang false rất rõ nhưng gần như không ảnh hưởng F1, vì `published` chỉ được dùng cho nhóm câu hỏi `date` (24/72) và ngày bị lùi vẫn là một chuỗi hợp lệ để so khớp.

**Kết quả nào khác với kỳ vọng ban đầu?**

Tôi kỳ vọng corruption sẽ kéo metrics xuống mạnh hơn nhiều. Thực tế `retrieval_hit_rate` chỉ rơi từ 1.0 xuống 0.9583. Giả thuyết đầu tiên của tôi là corruption không được áp dụng thật. Tôi kiểm tra bằng cách đọc `corruption_log.json` và `corrupted_quality.json`: cả 6 kịch bản đều có ghi nhận, và quality bắt được đúng 2 duplicate + 2 empty summary + 2 stale — tức corruption có chạy thật.

Nguyên nhân thật nằm ở **tỷ lệ**: `corrupt_clean_dataframe` dùng 5%–10% mỗi loại trên corpus chỉ 24 dòng, nên `max(1, int(24*0.1))` chỉ ra 2 dòng. Tổng cộng chưa tới 10 dòng bị đụng tới, và các dòng còn lại vẫn sạch nguyên. Thêm nữa, `top_k = 4` khá rộng so với corpus 24 tài liệu — tức 1/6 corpus được trả về mỗi lần query, nên retrieval rất khó trượt.

Một điểm nữa ban đầu làm tôi nghi ngờ: `repaired_metrics.json` trùng baseline **tuyệt đối**, không lệch một chữ số nào. Tôi đã nghi pipeline copy nhầm file. Kiểm tra lại thì thấy hợp lý: repair đọc cùng snapshot raw, chạy cùng `build_clean_dataframe` deterministic, embed bằng cùng model local MiniLM, và judge chạy ở `temperature=0.0`. Đúng đầu vào giống nhau thì đầu ra phải giống nhau. Tôi đối chiếu thêm kích thước file — `repaired_answers.json` và `baseline_answers.json` đều 672.893 byte — càng củng cố rằng đây là tính deterministic chứ không phải copy nhầm.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** lỗi tích hợp không nằm bên trong module nào cả mà nằm ở chỗ hai module gặp nhau. Hai ca tôi gặp đều đúng kiểu đó — `build_clean_dataframe` không trả `abs_url`/`pdf_url` mà `_build_documents` lại cần, và test set sinh phrasing mà `qa.py` không nhận. Cả hai module đều "đúng" khi đọc riêng lẻ; chỉ khi ghép lại mới lộ ra. Contract giữa các module cần được viết ra rõ ràng chứ không thể suy đoán.

2. **Về data quality/observability:** phải có nhiều tín hiệu khác loại thì mới bắt đủ lỗi. Trong bài này quality checks hoàn toàn mù trước `stale_date`, còn freshness hoàn toàn mù trước `duplicate_paper_id`. Nếu chỉ triển khai một trong hai, một nửa số corruption sẽ lọt qua mà dashboard vẫn xanh.

3. **Về ảnh hưởng của data đến RAG agent:** dữ liệu xấu không làm agent "hỏng" mà làm nó **âm thầm trả lời kém đi**. Không có exception nào được ném ra, pipeline vẫn exit 0, chỉ có metrics tụt vài phần trăm. Đây chính là lý do phải đo bằng test set cố định — nếu không có phép đo, sự xuống cấp này hoàn toàn vô hình.

### Nếu có thêm thời gian

Ưu tiên cao nhất là **thực sự chạy `agent.py` và ghi `agent_demo_answers.json`**, vì đây là khoảng trống thật của bài: agent LangChain với 2 tool (`semantic_search_papers`, `lookup_paper`) đã được viết đầy đủ nhưng chưa từng được gọi, nên chưa có bằng chứng nào cho thấy nó chạy được. Cách đo: chạy 3–4 câu hỏi qua agent — trong đó cố tình có một câu hỏi về chủ đề *không* nằm trong corpus — rồi kiểm tra agent có gọi tool trước khi trả lời hay không, và có nói thẳng "không có trong corpus" thay vì bịa ra câu trả lời hay không.

Thứ hai, tôi muốn tăng cường độ corruption (ví dụ 30% thay vì 10%) và giảm `top_k` từ 4 xuống 2, rồi đo lại. Với corpus 24 tài liệu, `top_k=4` nghĩa là mỗi query lấy về 1/6 corpus nên retrieval gần như không thể trượt — điều này giải thích vì sao `retrieval_hit_rate` chỉ rơi 4%. Đo lại ở cấu hình chặt hơn sẽ cho thấy tác động của dữ liệu xấu rõ nét hơn nhiều, và quan trọng hơn là kiểm chứng được giả thuyết "biên độ giảm nhỏ là do tỷ lệ corruption và top_k rộng, không phải do corruption không hiệu lực".

Thứ ba, bật `RUN_RAGAS=1` để bổ sung `faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`. Riêng `faithfulness` sẽ trả lời được một câu hỏi mà 4 metric hiện tại không chạm tới: khi summary bị blank, agent trả lời rỗng hay bắt đầu bịa?

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Quốc Hiệu
**Ngày xác nhận:** 2026-08-06
