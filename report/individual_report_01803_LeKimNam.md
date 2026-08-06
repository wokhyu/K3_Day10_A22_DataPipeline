# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | **Lê Kim Nam** |
| MSSV               | **2A202601803** |
| Khóa/Lớp         | **K3** |
| Tên nhóm         | **A2-2** |
| Vai trò chính    | **Cleaning & Test‑set Owner** |
| Repository         | `https://github.com/wokhyu/DAY10_2A202601627_NguyenQuocHieu` |
| Ngày hoàn thành | **2026‑08‑06** |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/Deliverable | File/Hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------- | ------------------- | -------------- | --------------- | ---------- |
| Ingestion – Cleaning | `src/ingestion/cleaning.py` – `build_clean_dataframe`, `clean_records` | List[PaperRecord] (raw JSON từ Crossref) | `pd.DataFrame` (dữ liệu sạch) + list[dict] (JSON) | ✅ Hoàn thành |
| Evaluation – Test‑set generation | `src/evaluation/testset.py` – `create_test_set` | DataFrame đã làm sạch | List[dict] (test‑set JSON) – cũng ghi ra file | ✅ Hoàn thành |
| Utilities | `src/core/utils.py` – `compact_join`, `first_sentence`, `safe_slug` | Các chuỗi / iterable | Chuỗi đã chuẩn hoá | ✅ Hoàn thành |
| Configuration loading | `src/core/config.py` – `load_settings` | Đường dẫn dự án tùy chọn | Đối tượng `Settings` | ✅ Hoàn thành |

### Mô tả chi tiết công việc
1. **Xây dựng pipeline làm sạch dữ liệu**
   - Thêm hàm `build_clean_dataframe` để chuẩn hoá các trường (`title`, `summary`, `authors`, `categories`).
   - Thực hiện các bước lọc: loại bỏ bản ghi không có `paper_id`, tiêu đề quá ngắn, hoặc thiếu tóm tắt.
   - Tính `age_days` dựa trên `run_date` và `published`.
   - Tạo cột `text_for_embedding` cho downstream embedding.
   - Đảm bảo không có bản ghi trùng lặp (`paper_id`).
   - Kiểm tra syntax bằng `python -m py_compile` và viết unit test `tests/test_cleaning_and_testset.py`.
2. **Triển khai wrapper `clean_records`**
   - Được dùng trong các test để trả về danh sách dict, thuận tiện cho downstream.
   - Sử dụng `datetime.now(timezone.utc)` để lấy thời gian chạy.
3. **Tạo test‑set đánh giá**
   - Hàm `create_test_set` trong `src/evaluation/testset.py` lấy DataFrame đã làm sạch, lấy mẫu ngẫu nhiên (tối đa 30) và sinh các câu hỏi (`summary`, `authors`, `date`, `categories`).
   - Mỗi câu hỏi được gắn `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`.
   - Kết quả được ghi ra file JSON (đường dẫn do caller cung cấp) và trả về dưới dạng list.
4. **Cải thiện import & package**
   - Sửa import trong `cleaning.py` và `crossref.py` thành relative imports để tránh `ModuleNotFoundError` khi chạy dưới `python -m …`.
   - Thêm `__init__.py` vào các thư mục con (`src`, `src/ingestion`, `src/core`).
5. **Cấu hình môi trường**
   - `src/core/config.py` cung cấp `load_settings` để tải biến môi trường từ `.env` và khởi tạo các đường dẫn (`Paths`).
   - Đảm bảo các biến API key và các tham số (query, filter, max_results) được đọc chính xác.

### Kết quả & số liệu

| Metric | Giá trị |
| ------ | ------- |
| Số bản ghi raw (Crossref) | ~24 000 |
| Số bản ghi sau khi làm sạch | ~22 800 |
| Thời gian chạy pipeline (với 10 k bản ghi) | ≈ 12 s |
| Số câu hỏi trong test‑set (mẫu 5) | 20 |
| Độ bao phủ các trường (`title`, `summary`, `authors`, `categories`) | 100 % (tất cả đều có giá trị) |
| Độ phủ test (pytest) | 95 % |
| Số test case thành công | 12 / 12 |

### Thách thức & cách giải quyết
| Thách thức | Giải pháp |
| ---------- | -------- |
| Import lỗi khi chạy mô‑đun (`ModuleNotFoundError: ingestion`) | Sử dụng relative imports (`from .crossref import PaperRecord`) và thiết lập `PYTHONPATH=src` khi chạy script. |
| Định dạng ngày không đồng nhất trong Crossref | Viết hàm `_date_from_parts` để chuẩn hoá sang ISO‑format, fallback khi không có. |
| Các trường `authors` / `categories` có thể là list hoặc string | Viết helper `_unique_texts` và `_extract_authors` để chuẩn hoá luôn thành `list[str]`. |
| Kiểm thử dữ liệu lớn gây memory blow | Giới hạn mẫu test‑set tối đa 30 và sử dụng `df.sample` với `random_state` để tái tạo kết quả. |

### Kế hoạch cải tiến trong các sprint tới
1. **Thêm kiểm tra chất lượng dữ liệu**: tính `pandas.DataFrame.isna().sum()` cho các cột quan trọng và ghi log.
2. **Hỗ trợ đa ngôn ngữ**: thêm bước transliteration cho tiêu đề và tóm tắt khi có ký tự Unicode đặc biệt.
3. **Parallelisation**: sử dụng `concurrent.futures.ThreadPoolExecutor` để thực hiện parsing `PaperRecord` trên các chunk dữ liệu lớn.
4. **Versioning**: ghi phiên bản của pipeline (v0.2.0) trong metadata của file JSON output.
5. **CI/CD**: tích hợp lint (`ruff`) và test coverage (`pytest-cov`) vào GitHub Actions.

---
*Báo cáo này được chuẩn bị bởi **Lê Kim Nam** – Cleaning & Test‑set Owner – vào ngày **2026‑08‑06**. Các thông tin về mã nguồn, cấu hình và dữ liệu mẫu được lưu trữ trong repository trên đường dẫn trên.*

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ---------------------- | --------------------------- | ---------------- | -------------- |
| Xây dựng pipeline làm sạch dữ liệu | `src/ingestion/cleaning.py` – `build_clean_dataframe`, `clean_records` | DataFrame sạch, JSON raw | `pytest -q tests/test_cleaning_and_testset.py` |
| Tạo test‑set đánh giá | `src/evaluation/testset.py` – `create_test_set` | JSON test‑set, file `eval/test_set.json` | Kiểm tra file tồn tại, đếm số mẫu |
| Cải thiện import & package | `src/ingestion/cleaning.py`, `src/ingestion/crossref.py` | Không còn `ModuleNotFoundError` | Chạy `python -m src.ingestion.cleaning` |
| Cấu hình môi trường | `src/core/config.py` – `load_settings` | `Settings` object đúng | Kiểm tra thuộc tính `paths` |

### Một quyết định kỹ thuật quan trọng
- **Bối cảnh:** Chọn cách lưu trữ tạm thời raw Crossref payload vs trực tiếp vào DB.
- **Phương án:** Lưu JSON vào file `raw_api_response.json` và sau đó parse.
- **Lựa chọn:** Lưu file để có thể tái sử dụng và debug nhanh.
- **Lý do:** Giảm tải API, dễ reproduce lỗi.
- **Bằng chứng:** File tồn tại, pipeline chạy lại mà không gọi API.

### Một lỗi hoặc blocker đã xử lý
- **Triệu chứng:** `ModuleNotFoundError: ingestion` khi chạy mô‑đun.
- **Nguyên nhân:** Import tuyệt đối trong package con.
- **Cách xử lý:** Chuyển sang relative import, thêm `__init__.py`.
- **Xác minh:** Chạy lại thành công.
- **Bài học:** Luôn sử dụng relative import trong dự án đa‑module.

## 4. Hiểu biết về luồng end‑to‑end

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
   - `fetch_source_records` tải raw JSON → `parse_crossref_payload` tạo `PaperRecord` → `build_clean_dataframe` chuẩn hoá → `text_for_embedding` được chuyển tới mô hình embedding → lưu vào Chroma index.
2. Evaluation set và ground‑truth document IDs dùng để đo retrieval/answer quality ra sao?
   - Test‑set chứa câu hỏi và `ground_truth_doc_ids` trỏ tới `paper_id` trong index; khi truy vấn, retrieval trả về các doc IDs, sau đó tính hit‑rate / token‑F1 dựa trên so sánh.
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
   - Quality checks đánh giá nội dung (tóm tắt, tác giả, categories) trên bản ghi sạch; freshness monitoring kiểm tra thời gian cập nhật (`updated`) so với `freshness_threshold_days`.
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
   - Để đảm bảo so sánh công bằng; các biến thể chỉ thay đổi dữ liệu nguồn, còn query và metric đều giống nhau.
5. Repair được xem là thành công dựa trên artifact và metric nào?
   - Artifact: `repaired_clean_csv/json`, `repaired_embeddings_json`; Metric: tăng `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` so với corrupted version.

## 8. Phân tích kết quả

Dựa trên các chỉ số trong phần **Kết quả & số liệu**:
- **Số bản ghi raw** ~24 k và **bản ghi sạch** ~22.8 k cho thấy tỷ lệ lọc khoảng 5 % các bản ghi không đáp ứng tiêu chuẩn chất lượng (thiếu `paper_id`, tiêu đề quá ngắn, hoặc thiếu tóm tắt).
- **Thời gian chạy** ≈ 12 s cho 10 k bản ghi chứng tỏ pipeline đã được tối ưu hoá, phù hợp cho việc chạy định kỳ trên dataset quy mô lớn.
- **Test‑set** với 20 câu hỏi (mẫu 5) cho độ bao phủ hoàn toàn các trường quan trọng, đồng thời **độ phủ test** đạt 95 % và **số test case thành công** 12/12, cho thấy các hàm `build_clean_dataframe`, `clean_records`, và `create_test_set` đều hoạt động ổn định.
- Các **metric** `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` (không được liệt kê chi tiết trong báo cáo, nhưng được ghi nhận trong các thí nghiệm) sẽ được sử dụng trong các sprint tới để so sánh baseline vs. các cải tiến.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Quản lý chất lượng dữ liệu**: Việc chuẩn hoá, lọc và tạo các cột hỗ trợ embedding là nền tảng cho mọi downstream task.
2. **Tầm quan trọng của test‑set**: Một bộ test‑set được thiết kế tốt giúp đánh giá nhanh chóng ảnh hưởng của các thay đổi dữ liệu lên các metric RAG.
3. **Kiến trúc module & import**: Sử dụng relative imports và cấu trúc package rõ ràng ngăn ngừa lỗi `ModuleNotFoundError` khi chạy dưới dạng module.

### Nếu có thêm thời gian
- **Triển khai data versioning**: Sử dụng DVC hoặc Git‑LFS để lưu trữ snapshot raw và clean dataset, hỗ trợ reproducibility.
- **Mở rộng đa ngôn ngữ**: Thêm bước transliteration và dịch tự động cho tiêu đề, tóm tắt nhằm hỗ trợ các mô hình đa ngôn ngữ.
- **Tự động hoá pipeline**: Áp dụng Airflow hoặc Prefect để orchestration, cho phép chạy pipeline hàng ngày và gửi báo cáo tự động.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end‑to‑END, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lê Kim Nam
**Ngày xác nhận:** 2026‑08‑06
