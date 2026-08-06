# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Duy Lâm |
| MSSV | 2A202601073 |
| Khóa/Lớp | K3 |
| Tên nhóm | A2-2 |
| Vai trò chính | Source Ingestion — Crossref |
| Repository | https://github.com/wokhyu/DAY10_2A202601627_NguyenQuocHieu|
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Định nghĩa raw data contract | `PaperRecord`, `parse_crossref_payload()` trong `src/ingestion/crossref.py` | JSON response từ Crossref `/works` | Danh sách `PaperRecord` có schema nhất quán | Hoàn thành |
| Thu thập và lưu raw data | `fetch_source_records()` trong `src/ingestion/crossref.py` | `Settings`: query, filter, số record và output paths | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Nạp lại raw snapshot | `load_raw_records()` trong `src/ingestion/crossref.py` | Parsed-record JSON snapshot | Danh sách `PaperRecord` đã kiểm tra schema | Hoàn thành |
| Kiểm thử Source Ingestion | `tests/test_crossref.py` | Payload mẫu và HTTP response giả lập | 7 unit tests cho parse, retry, artifact và round-trip | Hoàn thành |

Phạm vi ownership của tôi kết thúc tại raw-record artifact. Module cleaning nhận dữ liệu từ `data/raw/crossref_records.json`; tôi không nhận ownership cho logic cleaning, evaluation, observability hoặc orchestration.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Xác minh handoff raw → clean | `src/ingestion/cleaning.py` | Snapshot nạp lại được 24 `PaperRecord`, có DOI ổn định và đủ các trường theo raw contract |
| Cung cấp ground-truth document ID cho downstream | Cleaning, retrieval và evaluation | DOI đã chuẩn hóa lowercase được sử dụng xuyên suốt làm `paper_id` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Gọi Crossref `/works` với query/filter cấu hình | `fetch_source_records()` | Nhận 24 source items | Đếm `message.items` trong `crossref_response.json` |
| Parse metadata về schema nội bộ | `parse_crossref_payload()` | 24/24 item thành raw record hợp lệ, 24 DOI duy nhất | Nạp `crossref_records.json` và kiểm tra `paper_id` |
| Lưu source lineage | `data/raw/crossref_response.json` | Raw API response 245.259 byte | Kiểm tra file và đọc JSON |
| Lưu parsed snapshot | `data/raw/crossref_records.json` | Raw records 59.230 byte | Gọi `load_raw_records()` |


Output cụ thể của phần việc là hai artifact raw. `crossref_response.json` giữ nguyên payload nguồn để truy vết; `crossref_records.json` chứa 24 record đã chuẩn hóa để cleaning không phải đọc trực tiếp schema biến thiên của Crossref. Mỗi record có 11 trường:

```text
paper_id, title, summary, authors, categories, primary_category,
published, updated, abs_url, pdf_url, comment
```

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Crossref là nguồn dữ liệu sống và metadata do nhiều publisher cung cấp nên cấu trúc từng item không hoàn toàn đồng đều. Abstract có thể chứa JATS/HTML, ngày có thể chỉ có năm hoặc năm-tháng, author có nhiều cách biểu diễn, subject/PDF URL có thể thiếu và API có thể trả rate limit hoặc lỗi dịch vụ tạm thời. Source Ingestion cần chuyển dữ liệu này thành contract ổn định, đồng thời lưu payload gốc để mọi biến đổi đều truy vết được.

### Cách triển khai

1. Gọi endpoint `https://api.crossref.org/works` với:
   - `query=agentic retrieval augmented generation large language model`;
   - `filter=from-pub-date:2026-02-07,has-abstract:true` tại lần chạy tạo artifact;
   - `rows=24`.
2. Dùng timeout kết nối/đọc và tối đa 4 lần thử. Các status `429`, `500`, `502`, `503`, `504` được retry theo exponential backoff; nếu có `Retry-After` thì ưu tiên giá trị này.
3. Lưu raw API response trước khi parse để không mất source evidence nếu một item lỗi schema.
4. Chuẩn hóa DOI về lowercase và dùng DOI làm `paper_id`. Record thiếu DOI, title hoặc abstract hữu ích bị loại.
5. Dùng HTML parser để bỏ markup JATS/HTML và chuẩn hóa khoảng trắng. Author được ghép từ `given` và `family`; subject được chuẩn hóa và loại trùng không phân biệt hoa thường.
6. Chuẩn hóa `date-parts` thành ISO date, chọn URL landing page và ưu tiên link có content type PDF.
7. Serialize dataclass bằng JSON; khi load lại, kiểm tra đủ 11 field và đúng kiểu dữ liệu thay vì âm thầm dùng snapshot hỏng.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref `/works` JSON, trong đó danh sách paper nằm tại `message.items`; query/filter/rows lấy từ `Settings` |
| Output trả về | `list[PaperRecord]` |
| Output artifact | `data/raw/crossref_response.json` và `data/raw/crossref_records.json` |
| Module phụ thuộc | `src/core/config.py`, `src/core/utils.py`, thư viện `requests` |
| Module sử dụng output | `src/ingestion/cleaning.py`, sau đó là retrieval/index, evaluation và observability |
| Điều kiện lỗi cần xử lý | Timeout/network error, HTTP 429/5xx, invalid JSON, thiếu `message.items`, item thiếu DOI/title/abstract, snapshot thiếu field hoặc sai kiểu |

Các field tùy chọn không được tự bịa dữ liệu. Ví dụ, nếu Crossref không có subject thì `categories=[]`; nếu không có PDF link thì `pdf_url=""`; `comment` để rỗng vì Crossref không có field tương đương trực tiếp.

### Cách xác minh

Chạy unit tests:

```powershell
.\myenv\Scripts\python.exe -m unittest tests.test_crossref -v
```

Chạy ingestion thật:

```powershell
.\myenv\Scripts\python.exe -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); records=fetch_source_records(s); print(len(records)); print(s.paths.raw_api_response); print(s.paths.raw_records_json)"
```

Kiểm tra khả năng nạp lại snapshot:

```powershell
.\myenv\Scripts\python.exe -c "from core.config import load_settings; from ingestion.crossref import load_raw_records; s=load_settings(); records=load_raw_records(s.paths.raw_records_json); print(len(records)); print(len({r.paper_id for r in records}))"
```

- **Kết quả mong đợi:** Hai JSON tồn tại; số parsed record không vượt `rows=24`; mọi record có DOI/title/summary; snapshot load lại được.
- **Kết quả thực tế:** Source items = 24, parsed records = 24, unique IDs = 24; 7/7 unit tests đạt.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`; không chứa API key hoặc secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Pipeline cần một document ID ổn định để nối raw data, clean data, Chroma metadata và `ground_truth_doc_ids` trong evaluation set.
- **Các phương án đã cân nhắc:** Dùng DOI; tạo hash từ title; hoặc dùng vị trí item trong API response.
- **Phương án đã chọn:** Chuẩn hóa DOI bằng cách bỏ khoảng trắng/prefix resolver, chuyển lowercase và dùng DOI làm `paper_id`.
- **Lý do:** DOI là định danh bền vững do nguồn cung cấp. Hash title có thể thay đổi khi publisher sửa title; vị trí item thay đổi theo kết quả tìm kiếm và thời gian chạy. DOI giúp repair từ raw snapshot và đối chiếu retrieval result mà không phải đoán lại ID.
- **Bằng chứng quyết định phù hợp:** Artifact thực tế có 24 parsed records và 24 `paper_id` duy nhất; sample ID là `10.47576/2949-1894.2026.7.7.023`. Snapshot load lại giữ nguyên các ID này.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `406 Client Error: Not Acceptable for url: https://api.crossref.org/works?...`
- **Lệnh hoặc bước tái hiện:** Chạy `fetch_source_records(load_settings())` với header `Accept: application/vnd.crossref-api-message+json`.
- **Nguyên nhân gốc:** Endpoint Crossref đang dùng trả `406` cho vendor media type trong request `Accept`, dù response JSON của dịch vụ vẫn chứa Crossref API message.
- **Cách xử lý:** Đổi request header thành `Accept: application/json`; giữ timeout, User-Agent và retry/backoff.
- **Cách xác minh sau khi sửa:** Chạy lại live ingestion; HTTP request thành công, nhận 24 items và tạo đủ hai raw artifacts. Unit test cũng kiểm tra chính xác request header và artifact output.
- **Điều học được:** Không chỉ dựa vào giả định về media type; cần kiểm tra hành vi endpoint thật, nhưng vẫn phải giữ unit test để kết quả có thể tái lập mà không phụ thuộc mạng.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**

Crossref `/works` trả metadata. Source Ingestion lưu nguyên response và parse thành `PaperRecord`. Cleaning đọc snapshot, chuẩn hóa/dedupe, tính `age_days` và tạo `text_for_embedding`. `LocalEmbeddingIndex` dùng MiniLM tạo embedding, ghi manifest và đưa vector cùng metadata vào collection Chroma riêng cho baseline, corrupted hoặc repaired.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**

Mỗi test item có question, ground truth và danh sách `ground_truth_doc_ids`. Khi retriever trả document IDs, evaluator kiểm tra có lấy đúng tài liệu nguồn hay không để tính `retrieval_hit_rate`. Answer được so với ground truth bằng token F1 và judge score. Vì vậy `paper_id` ổn định từ ingestion là điều kiện để metric retrieval có ý nghĩa.

**3. Quality checks khác freshness monitoring ở điểm nào?**

Quality checks đánh giá tính đầy đủ, hợp lệ và duy nhất của dữ liệu, ví dụ title/summary thiếu hoặc DOI trùng. Freshness monitoring tập trung vào tuổi dữ liệu theo `published`, `age_days`, ngày mới nhất/cũ nhất và ngưỡng stale. Dữ liệu có thể đúng schema nhưng đã cũ, hoặc mới nhưng thiếu/trùng field.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**

Giữ nguyên test set giúp ba trạng thái được đo trên cùng câu hỏi và ground truth. Nếu đổi test set giữa các lần chạy thì metric delta có thể đến từ độ khó của mẫu, không phải từ corruption hay repair.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**

Repair phải được tạo lại từ raw snapshot, không sửa tay kết quả corrupted. Cần đối chiếu repaired clean artifact, collection/embedding manifest, quality/freshness report và `repaired_metrics.json`. Chỉ kết luận phục hồi khi signal chất lượng và các metric như retrieval hit rate, token F1, judge accuracy/score tiến gần hoặc trở lại baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | Chưa có | Chưa có | Chưa có | Chưa thể kết luận vì baseline/corruption flow chưa tạo metrics |
| `mean_token_f1` | Chưa có | Chưa có | Chưa có | Source Ingestion không tự sinh answer metric |
| `judge_accuracy` | Chưa có | Chưa có | Chưa có | Chờ evaluator và LLM judge chạy trên cùng test set |
| `mean_judge_score` | Chưa có | Chưa có | Chưa có | Chưa có artifact trong `data/results/` để đối chiếu |
| Quality checks | Chưa có | Chưa có | Chưa có | `data/quality/` chưa có report ngoài file giữ chỗ |
| Freshness status | Chưa có | Chưa có | Chưa có | Chưa chạy freshness reporting |

### Kết luận từ số liệu

Hiện tại mới có bằng chứng cho Source Ingestion: 24 source items → 24 parsed records → 24 DOI duy nhất. Chưa có `baseline_metrics.json`, corrupted/repaired artifact, quality report hoặc freshness report, vì vậy chưa đủ bằng chứng để hoàn thành hai chuỗi nguyên nhân–kết quả về corruption và repair.

1. **Corruption:** chưa chạy → chưa có quality/freshness signal → chưa có agent metric delta.
2. **Repair:** chưa chạy → chưa có repaired signal → chưa thể đánh giá mức phục hồi.

Chưa thể xác định corruption nào ảnh hưởng rõ nhất. Kết luận này chỉ được đưa ra sau khi dùng cùng raw snapshot, clean contract, test set và evaluator cho cả ba trạng thái. Kết quả Source Ingestion phù hợp kỳ vọng ban đầu về số lượng và tính duy nhất; chưa có kết quả downstream để so sánh với kỳ vọng.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw response và parsed snapshot cần được lưu tách biệt: một file giữ source evidence, một file cung cấp data contract ổn định cho downstream.
2. Data quality bắt đầu ngay tại ingestion qua stable ID, schema validation, timeout và retry; không nên chờ đến cuối pipeline mới phát hiện dữ liệu lỗi.
3. Chất lượng RAG phụ thuộc vào lineage: nếu DOI bị thay đổi hoặc abstract còn markup/rỗng, retrieval và ground-truth mapping có thể sai dù mô hình embedding/LLM không đổi.

### Nếu có thêm thời gian

Tôi sẽ bổ sung ingestion manifest gồm thời điểm fetch UTC, endpoint, query/filter, source item count, parsed count và lý do từng item bị loại. Cải thiện được đo bằng khả năng đối chiếu `source_items = parsed + skipped_by_reason`, đồng thời thêm fault-injection tests cho timeout, invalid JSON và trường hợp retry cạn số lần.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Duy Lâm<br>
**Ngày xác nhận:** 2026-08-06
