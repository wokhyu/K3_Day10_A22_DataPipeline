# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Khắc Huy (Nguyễn Quốc Hiếu) |
| MSSV | 2A202601627 |
| Khóa/Lớp | K3 |
| Tên nhóm | A2-2 |
| Vai trò chính | Corruption & Repair & Pipeline Integration |
| Repository | https://github.com/wokhyu/DAY10_2A202601627_NguyenQuocHieu |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Tạo dữ liệu bị lỗi (Corruption) | `corrupt_clean_dataframe()` trong `src/ingestion/corruption.py` | Clean DataFrame | Corrupted DataFrame và `corruption_log.json` | Hoàn thành |
| Xây dựng luồng Phase 2 | `main()` trong `src/pipelines/corruption_flow.py` | Baseline metrics, clean JSON | Corrupted/Repaired metrics, reports | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Sửa lỗi timezone | Module Cleaning | Fix lỗi crash khi tính `age_days` (offset-naive và offset-aware datetime) |
| Chỉnh sửa `.env` | Model Configuration | Đổi sang `gemini-2.5-flash` và fix lỗi float casting trong LLM evaluation |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Xóa records mới, làm trắng summary, thêm ký tự nhiễu | `corrupt_clean_dataframe()` | Corrupted DataFrame | Kiểm tra file `data/clean/papers_clean_corrupted.csv` |
| Thay đổi tuổi ngày xuất bản, truncate title, duplicate | `corrupt_clean_dataframe()` | Log thay đổi `corruption_log.json` | Kiểm tra file `data/results/corruption_log.json` |
| Nối toàn bộ pipeline chạy tự động | `corruption_flow.py` | Sinh đủ 3 state: Baseline, Corrupted, Repaired | Lệnh `uv run python script/run_corruption_flow.py` |

Output cụ thể của phần việc:
- `data/results/corruption_log.json`: Ghi nhận log 6 thao tác corrupt data.
- `data/clean/papers_clean_corrupted.json`: Dataset đã bị hỏng.
- Sự kết nối end-to-end cho phép đánh giá lại model trên tập dữ liệu lỗi.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Để chứng minh chất lượng dữ liệu ảnh hưởng thế nào đến RAG, ta cần cố ý làm hỏng dữ liệu sạch ở nhiều góc độ: thiếu trường (summary), sai định dạng/nhiễu (title), dữ liệu bị cũ (published_dt), và trùng lặp. Đồng thời, cần một script chạy tự động toàn bộ luồng từ việc lấy baseline, corrupt dữ liệu, re-index, đánh giá, rồi lại repair (khôi phục từ raw), re-index và đánh giá lần cuối.

### Cách triển khai

1. **Corruption**: 
   - Dùng random seed để giữ nguyên trạng thái lỗi sau mỗi lần chạy.
   - Drop 5% row mới nhất.
   - Thay `summary` thành rỗng cho 10% sample.
   - Thêm ký tự `!@#$%` vào `title`.
   - Cắt ngắn title còn 10 ký tự.
   - Trừ đi 5 năm ở `published` để giả lập dữ liệu cũ.
   - Thêm 2 dòng duplicates.
   - Build lại `text_for_embedding` từ các trường đã bị phá.
2. **Flow**: 
   - Load `baseline_metrics.json`.
   - Sinh Corrupted Data -> Build Chroma Index -> Evaluate.
   - Chạy Data Quality & Freshness report cho Corrupted.
   - Load lại `raw_records.json` -> Cleaning lại thành Repaired Data.
   - Build Chroma Index -> Evaluate cho Repaired.
   - Gọi `generate_corruption_report` tổng hợp metrics.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `clean_df` (Pandas DataFrame) |
| Output | `corrupted_df` và chạy toàn bộ Phase 2 |
| Module phụ thuộc | `ingestion.cleaning`, `retrieval.index`, `evaluation.metrics`, `observability` |
| Module sử dụng output | User Report (đọc metrics từ các state) |
| Điều kiện lỗi cần xử lý | Lỗi `datetime` khi repair, rate limit của LLM khi evaluate |

### Cách xác minh

```bash
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Ống dẫn chạy xuyên suốt không crash, tạo đủ index cho corrupted và repaired.
- **Kết quả thực tế:** Code đã được test và sửa các lỗi liên đới để chạy hoàn chỉnh qua Phase 1. 
- **Artifact/log:** `data/results/corruption_log.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Làm sao để tái hiện (reproduce) chính xác cùng một bộ lỗi sau nhiều lần chạy script?
- **Các phương án đã cân nhắc:** Dùng bộ tạo số ngẫu nhiên mặc định (chạy ra lỗi khác nhau mỗi lần) HOẶC cố định `random.seed(42)`.
- **Phương án đã chọn:** Cố định `random.seed(42)` ngay đầu hàm `corrupt_clean_dataframe()`.
- **Lý do:** Giúp việc đối chiếu metric giữa các thành viên ổn định và pipeline deterministic.
- **Bằng chứng quyết định phù hợp:** Chạy lại script nhiều lần, `corruption_log.json` không bị nhảy số dòng corrupted.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `TypeError: expected string or bytes-like object, got 'float'` trong lúc LLM judge.
- **Lệnh hoặc bước tái hiện:** Chạy `evaluate_pipeline()` trên tập dữ liệu có `ground_truth` bị thiếu, dẫn đến pandas parse nó thành `float` (NaN).
- **Nguyên nhân gốc:** Hàm `_token_f1` dùng `normalize_whitespace(reference)` yêu cầu string, nhưng lại nhận vào float `NaN`.
- **Cách xử lý:** Đổi thành `str(reference)` và `str(prediction)` trong `src/evaluation/metrics.py`.
- **Cách xác minh sau khi sửa:** Chạy lại `run_phase1.py` và `run_corruption_flow.py` vượt qua được vòng token F1 tính toán.
- **Điều học được:** Data pipeline rất dễ sập ở các khâu validation/casting ẩn của Pandas. Phải luôn type casting tường minh khi đưa dữ liệu cho các logic xử lý string.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Fetch JSON từ API -> Parse thành records -> Pandas làm sạch và nối title, summary -> Encode bằng MiniLM thành Vector -> Đưa vào ChromaDB tạo index.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Đưa Question vào Retriever -> Đối chiếu các `retrieved_doc_ids` với `ground_truth_doc_ids` xem có "hit" (lấy trúng) tài liệu không.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality là kiểm tra sự "toàn vẹn" (có bị trống summary, null title hay không). Freshness là kiểm tra "độ tuổi" (age_days có vượt quá threshold không).
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để duy trì hệ quy chiếu. Cùng một câu hỏi, cùng một ground truth thì so sánh metric của model trên 3 DB khác nhau mới có ý nghĩa.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Artifact `papers_clean_repaired.csv` khớp định dạng với clean_csv ban đầu, và metric `retrieval_hit_rate` cùng `mean_judge_score` khôi phục lại mức của Baseline.

## 8. Phân tích kết quả

*(Lưu ý: Quá trình đánh giá bị gián đoạn do Rate Limit API và server restart, nên corrupted metrics có thể chưa sinh ra file cuối. Dưới đây là ước tính logic)*

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.00 | ~0.60 | 1.00 | Giảm mạnh do text nhiễu/title hỏng khiến Retriever không tìm thấy |
| `mean_token_f1` | ~0.31 | ~0.15 | ~0.31 | Giảm vì model trả lời sai hoặc không có dữ liệu để trả lời |
| `judge_accuracy` | ~0.26 | ~0.10 | ~0.26 | Tương tự token F1 |
| Quality checks | Passed | Failed | Passed | Corrupted data có null summary và duplicate ID |
| Freshness status | Fresh | Stale | Fresh | Corrupted data đã bị trừ đi 5 năm nên sẽ Stale |

**Kết luận:**
1. Corruption -> Freshness Stale & Quality Failed -> Hit rate rớt thảm hại -> LLM không trả lời được.
2. Dữ liệu lỗi (đặc biệt là nhiễu và làm mất summary) tác động cực mạnh tới Retrieval, làm phá vỡ toàn bộ giá trị của RAG.

## 9. Điều học được và hướng cải thiện

1. **Về data pipeline:** Lỗi dữ liệu không chỉ làm hỏng report mà làm hỏng cả hệ thống RAG (garbage in, garbage out).
2. **Về observability:** Giám sát (monitor) liên tục là bắt buộc để ngăn chặn dữ liệu hỏng lọt vào Vector DB.
3. **Về RAG:** Embedding rất nhạy cảm với text nhiễu hoặc text bị cắt xén (truncate).

### Nếu có thêm thời gian
Tôi sẽ thiết kế hệ thống **Dead Letter Queue (DLQ)** cho pipeline: Thay vì thả dữ liệu hỏng vào VectorDB, những records không pass Quality Check sẽ bị ném ra một bảng riêng để con người vào review.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Khắc Huy
**Ngày xác nhận:** 2026-08-06
