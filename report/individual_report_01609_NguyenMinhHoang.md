# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Minh Hoàng |
| MSSV | 2A202601609 |
| Khóa/Lớp | K3 |
| Tên nhóm | A2-2 |
| Vai trò chính | Thành viên 3 — Observability owner |
| Repository | `DAY10_2A202601627_NguyenQuocHieu` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data quality checks | `src/observability/quality.py` — `run_data_quality_checks` | DataFrame cleaned/corrupted/repaired, `Settings`, report name | JSON quality report trong `data/quality/` | Hoàn thành |
| Freshness monitoring | `src/observability/quality.py` — `build_freshness_report` | DataFrame có `published`, `age_days`, freshness threshold | JSON freshness report | Hoàn thành |
| Baseline reporting | `src/observability/reporting.py` — `generate_phase1_report` | Source summary, metrics, quality, freshness | `data/reports/phase1_report.md` | Hoàn thành |
| Corruption comparison reporting | `src/observability/reporting.py` — `generate_corruption_report` | Metrics và quality/freshness của baseline, corrupted, repaired | `data/reports/corruption_report.md` | Hoàn thành |

Các hàm Observability được tích hợp trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`. Phạm vi ownership của tôi là quality, freshness và cách kết xuất báo cáo; không nhận ownership cho ingestion, retrieval hoặc evaluation.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra contract output và đường dẫn artifact | `src/core/config.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` | Dùng các path cấu hình như `quality_dir`, `freshness_report`, `baseline_report`, `comparison_report`; không hard-code đường dẫn |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Kiểm tra chất lượng dữ liệu | `quality.py` — `run_data_quality_checks` | Đếm tổng dòng, thiếu ID/title, summary rỗng, duplicate ID và stale rows; tạo cờ `passed` | Smoke test với DataFrame hợp lệ cho kết quả `passed=True`, các lỗi bằng `0` |
| Theo dõi freshness | `quality.py` — `build_freshness_report` | Tạo `latest_published`, `oldest_published`, `stale_rows`, `total_rows`, `is_fresh` | Smoke test parse ngày và ghi JSON thành công |
| Tạo baseline report | `reporting.py` — `generate_phase1_report` | Markdown gồm Source Summary, Evaluation Metrics, Data Quality, Freshness | Kiểm tra file được tạo đúng cấu trúc |
| Tạo comparison report | `reporting.py` — `generate_corruption_report` | Markdown có baseline/corrupted/repaired metrics và quality/freshness comparison | Smoke test tạo file so sánh thành công |

Một output cụ thể: với DataFrame smoke gồm 2 dòng hợp lệ, quality report trả `total_rows=2`, `missing_paper_id=0`, `duplicate_paper_id=0`, `missing_title=0`, `empty_summary=0`, `stale_rows=0`, `passed=true`; freshness report trả `is_fresh=true`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline RAG có thể vẫn chạy dù dữ liệu thiếu, trùng, summary rỗng hoặc quá cũ. Observability cần biến các vấn đề đó thành tín hiệu có cấu trúc, đồng thời cung cấp báo cáo dễ đọc để đối chiếu chất lượng dữ liệu với metrics của agent.

### Cách triển khai

`run_data_quality_checks` kiểm tra tổng số dòng, `paper_id` thiếu, duplicate `paper_id`, `title` thiếu, `summary` rỗng và số dòng vượt `settings.freshness_threshold_days` dựa trên `age_days`. `passed` chỉ là `True` khi DataFrame không rỗng và tất cả kiểm tra đều đạt. Kết quả được ghi vào `quality_dir/<report_name>.json`.

`build_freshness_report` đọc cột `published`, bỏ qua ngày thiếu và parse các giá trị ngày bằng `pd.to_datetime(..., utc=True)`. Report chứa ngày mới nhất/cũ nhất, số dòng stale, tổng số dòng và `is_fresh`. Hai hàm trong `reporting.py` nhận dictionary đã được tính từ pipeline rồi tuần tự kết xuất thành Markdown, tránh tự tính lại metrics.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | DataFrame cleaned/corrupted/repaired; `Settings`; dictionaries source summary, metrics, quality và freshness |
| Output | JSON quality/freshness artifacts và Markdown phase/comparison reports |
| Module phụ thuộc | `core.config.Settings`, `core.utils.ensure_parent`, `write_json`, `write_text`, `pandas` |
| Module sử dụng output | `pipelines.phase1`, `pipelines.corruption_flow`, người đọc artifact trong `data/quality/` và `data/reports/` |
| Điều kiện lỗi cần xử lý | Thiếu cột thì dùng giá trị mặc định; ngày không parse được thì bỏ qua; parent directory chưa có thì tạo trước khi ghi |

### Cách xác minh

```powershell
@'
from pathlib import Path
from types import SimpleNamespace
import tempfile
import pandas as pd
from src.observability.quality import run_data_quality_checks, build_freshness_report
from src.observability.reporting import generate_phase1_report, generate_corruption_report

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    settings = SimpleNamespace(
        freshness_threshold_days=180,
        paths=SimpleNamespace(quality_dir=root / "quality"),
    )
    df = pd.DataFrame([
        {"paper_id": "p1", "title": "Alpha", "summary": "A summary", "published": "2026-07-01", "age_days": 10},
        {"paper_id": "p2", "title": "Beta", "summary": "B summary", "published": "2026-06-01", "age_days": 40},
    ])
    quality = run_data_quality_checks(df, settings, "sample_quality")
    freshness = build_freshness_report(df, settings, root / "quality" / "freshness.json")
    generate_phase1_report(root / "reports" / "phase1.md", {"raw_records": 2}, {"retrieval_hit_rate": 1.0}, quality, freshness)
    generate_corruption_report(root / "reports" / "corruption.md", {"retrieval_hit_rate": 1.0}, {"retrieval_hit_rate": 0.5}, {"retrieval_hit_rate": 1.0}, quality, quality, freshness, freshness)
    print(quality)
    print(freshness)
'@ | .\.venv\Scripts\python.exe -
```

- **Kết quả mong đợi:** Quality report có `passed=True`, freshness report có `is_fresh=True`, hai Markdown files được tạo.
- **Kết quả thực tế:** Đạt; smoke test trả `passed=True`, `is_fresh=True` và tạo thành công các file output.
- **Artifact/log:** Smoke artifacts nằm trong thư mục tạm; contract production là `data/quality/*.json` và `data/reports/*.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Report function có thể tự đọc các file trong `data/` hoặc nhận kết quả đã tính từ pipeline.
- **Các phương án đã cân nhắc:** (1) Report tự đọc và tính lại mọi artifact; (2) pipeline tính quality/metrics một lần rồi truyền dictionaries vào report function.
- **Phương án đã chọn:** Chọn phương án (2); `quality.py` tính quality/freshness còn `reporting.py` chỉ định dạng và ghi kết quả.
- **Lý do:** Giảm coupling với filesystem/evaluator, tránh lệch số liệu do tính lại, dễ test với input nhỏ và tái sử dụng cho baseline/corruption.
- **Bằng chứng quyết định phù hợp:** Smoke test chỉ dùng dictionaries nhưng tạo được cả hai Markdown report; pipeline cũng truyền `evaluation.summary`, quality và freshness trực tiếp vào các hàm report.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `FileNotFoundError` khi ghi quality/report vào thư mục output chưa tồn tại.
- **Lệnh hoặc bước tái hiện:** Gọi các hàm report với đường dẫn nằm trong thư mục tạm chưa được tạo.
- **Nguyên nhân gốc:** File writer không thể tạo file con nếu parent directory chưa tồn tại.
- **Cách xử lý:** Gọi `ensure_parent(report_path)` trước `write_json` hoặc `write_text` trong các hàm Observability.
- **Cách xác minh sau khi sửa:** Chạy smoke test với thư mục tạm rỗng; quality JSON, freshness JSON, phase report và corruption report đều được tạo.
- **Điều học được:** Artifact writer nên tự đảm bảo cấu trúc thư mục, không giả định pipeline đã tạo sẵn toàn bộ `data/`.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** Crossref trả raw response; ingestion lưu raw records; cleaning tạo DataFrame với `paper_id`, metadata, `published`, `age_days` và `text_for_embedding`. Retrieval dùng text để tạo embedding và index. Observability kiểm tra DataFrame sau cleaning hoặc các bản corrupted/repaired.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** Test set cố định chứa câu hỏi, đáp án chuẩn và `ground_truth_doc_ids`. Evaluator so sánh document IDs retrieve được, token F1 và judge metrics. Quality report bổ sung tín hiệu về tình trạng dữ liệu, không thay thế evaluator.
3. **Quality checks khác freshness monitoring ở điểm nào?** Quality checks tập trung vào đầy đủ, hợp lệ và duy nhất của nội dung; freshness monitoring tập trung vào ngày publish, tuổi dữ liệu và số dòng vượt threshold. Dataset có thể quality pass nhưng không fresh, hoặc fresh nhưng quality fail.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Để mọi thay đổi metrics phản ánh corruption/repair thay vì khác biệt về câu hỏi hoặc độ khó của evaluation set.
5. **Repair được xem là thành công dựa trên artifact và metric nào?** Cần có repaired clean dataset/embedding manifest, repaired quality/freshness reports và `repaired_metrics.json`. Chỉ kết luận phục hồi khi quality/freshness hợp lệ và các metrics tiến gần baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | Chưa có artifact | Chưa có artifact | Chưa có artifact | Chưa có `data/results/*_metrics.json` để đối chiếu |
| `mean_token_f1` | Chưa có artifact | Chưa có artifact | Chưa có artifact | Không suy diễn từ quality report |
| `judge_accuracy` | Chưa có artifact | Chưa có artifact | Chưa có artifact | Cần evaluator/LLM judge chạy trước khi kết luận |
| `mean_judge_score` | Chưa có artifact | Chưa có artifact | Chưa có artifact | Chưa có số liệu thực tế trong workspace |
| Quality checks | Chưa có production artifact | Chưa có production artifact | Chưa có production artifact | Hàm đã được smoke-test; full pipeline chưa tạo artifact trong workspace |
| Freshness status | Chưa có production artifact | Chưa có production artifact | Chưa có production artifact | Chưa chạy flow đầy đủ để có ba trạng thái |

### Kết luận từ số liệu

Workspace hiện có raw records, cleaned CSV/JSON và evaluation set, nhưng chưa có `baseline_metrics.json`, quality/freshness production reports hoặc corruption comparison report. Vì vậy tôi chỉ kết luận về behavior của Observability từ smoke test, không khẳng định agent đã cải thiện.

1. **Data corruption** → quality/freshness signal có thể chuyển từ pass/fresh sang fail/stale → agent metrics cần được đo trên cùng test set; hiện chưa có số liệu delta.
2. **Repair từ raw snapshot** → quality/freshness kỳ vọng phục hồi → agent metrics chỉ được xem là phục hồi khi `repaired_metrics.json` được đối chiếu với baseline; hiện chưa có artifact production.

Chưa thể xác định corruption nào ảnh hưởng rõ nhất vì chưa có corruption log và ba bộ metrics. Smoke test đúng kỳ vọng: dữ liệu hợp lệ có `passed=True`, `is_fresh=True`, và report writer tự tạo parent directory.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Quality và freshness là hai tín hiệu khác nhau nhưng nên được ghi cạnh evaluation metrics để truy nguyên chất lượng RAG.
2. Report function nên nhận kết quả đã tính thay vì tự đọc/tính lại artifact; contract rõ hơn và dễ kiểm thử hơn.
3. Tạo thành công file không phải bằng chứng pipeline đúng; kết luận baseline/corrupted/repaired phải dựa trên artifact và metrics thực tế.

### Nếu có thêm thời gian

Tôi sẽ bổ sung schema/version và timestamp UTC vào các quality/freshness report, đồng thời thêm test cho DataFrame rỗng, thiếu `published`, ngày không parse được, duplicate count và stale row. Cải thiện được đo bằng metadata truy vết đầy đủ và test bao phủ các nhánh lỗi trước khi chạy full pipeline.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Minh Hoàng  
**Ngày xác nhận:** 2026-08-06
