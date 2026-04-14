# Hướng dẫn tích hợp ml_clo vào Backend

**Phiên bản:** 1.0  
**Ngày:** 2026-04-13  
**Áp dụng cho:** Backend FastAPI (hoặc bất kỳ Python backend nào)

---

## Mục lục

1. [Kiểm tra sẵn sàng tích hợp](#1-kiểm-tra-sẵn-sàng-tích-hợp)
2. [Cài đặt](#2-cài-đặt)
3. [Khởi động ứng dụng (startup)](#3-khởi-động-ứng-dụng-startup)
4. [Data contract — Backend chuẩn bị gì trước khi gọi ml_clo](#4-data-contract)
5. [API Predict (cá nhân)](#5-api-predict-cá-nhân)
6. [API Analyze Class (phân tích lớp)](#6-api-analyze-class-phân-tích-lớp)
7. [API Train (huấn luyện lại model)](#7-api-train-huấn-luyện-lại-model)
8. [Output schemas — JSON trả về Frontend](#8-output-schemas)
9. [Xử lý lỗi](#9-xử-lý-lỗi)
10. [Cấu hình nâng cao](#10-cấu-hình-nâng-cao)
11. [Lưu ý threading / async](#11-lưu-ý-threading--async)

---

## 1. Kiểm tra sẵn sàng tích hợp

### ✅ Đã sẵn sàng

| Hạng mục | Trạng thái | Chi tiết |
|----------|-----------|---------|
| Package install | ✅ | `pip install -e /path/to/modelAI` |
| Public API | ✅ | `from ml_clo import TrainingPipeline, PredictionPipeline, AnalysisPipeline` |
| JSON output | ✅ | Tất cả output có `.to_dict()` / `.to_json()` |
| Model path qua parameter | ✅ | Không hard-code path, backend truyền vào |
| Không có print()/input() | ✅ | Chỉ dùng logger nội bộ |
| Audit log opt-in | ✅ | No-op khi không cấu hình |
| Encoding tự xác thực | ✅ | Model reject nếu encoding_method không khớp |
| Xử lý unknown entity | ✅ | Lecturer/Subject mới → hash default |
| Exception types rõ ràng | ✅ | `ModelLoadError`, `DataValidationError`, `PredictionError` |
| Thread-safe audit log | ✅ | Dùng `threading.Lock()` |

### ⚠️ Backend cần xử lý thêm

| Hạng mục | Backend phải làm |
|----------|----------------|
| Data source | ml_clo đọc từ **file Excel**. Backend phải export dữ liệu từ MySQL ra file hoặc build DataFrame rồi truyền trực tiếp. |
| HTTP layer | ml_clo không có HTTP — backend bọc các pipeline call trong FastAPI endpoint. |
| Async | Pipeline calls là **synchronous**. Gọi trong `asyncio.get_event_loop().run_in_executor()` để không block event loop. |
| Model file | Lưu `model.joblib` ngoài git (object storage / volume mount). Backend cung cấp path khi khởi động. |
| Model retrain trigger | Backend quyết định khi nào gọi `TrainingPipeline.run()`. |

---

## 2. Cài đặt

### Trong môi trường backend

```bash
# Cài ml_clo như editable package (nếu cùng server / volume mount)
pip install -e /path/to/modelAI

# Hoặc build wheel rồi cài
cd /path/to/modelAI && python -m build
pip install dist/ml_clo-0.1.0-py3-none-any.whl
```

### requirements.txt của backend

```
ml-clo @ file:///path/to/modelAI   # editable path
# hoặc sau khi build:
# ml-clo==0.1.0
fastapi>=0.100.0
uvicorn>=0.23.0
sqlalchemy>=2.0.0
pandas>=1.5.0
openpyxl>=3.0.0
```

### Kiểm tra cài đặt

```python
import ml_clo
print(ml_clo.__version__)  # "0.1.0"
from ml_clo import PredictionPipeline, AnalysisPipeline, TrainingPipeline
```

---

## 3. Khởi động ứng dụng (startup)

Khởi tạo pipeline **một lần** khi ứng dụng start, cache lại để tái sử dụng.

```python
# app/lifespan.py (FastAPI lifespan context)
from contextlib import asynccontextmanager
from fastapi import FastAPI
from ml_clo import PredictionPipeline, AnalysisPipeline
from ml_clo.utils.audit_log import set_audit_log_path
import os

# Global instances
_predict_pipeline: PredictionPipeline = None
_analysis_pipeline: AnalysisPipeline = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _predict_pipeline, _analysis_pipeline

    model_path = os.environ["MODEL_PATH"]           # e.g. "models/model.joblib"
    data_dir   = os.environ.get("DATA_DIR", "data") # thư mục chứa Excel

    # --- Audit log (opt-in) ---
    log_path = os.environ.get("AUDIT_LOG_PATH")
    if log_path:
        set_audit_log_path(log_path)  # e.g. "logs/predictions.jsonl"

    # --- PredictionPipeline: Mode 1 (cache mode) ---
    # Load toàn bộ Excel một lần, mỗi request predict chỉ cần ID
    _predict_pipeline = PredictionPipeline(
        model_path=model_path,
        exam_scores_path=f"{data_dir}/DiemTong.xlsx",          # optional
        demographics_path=f"{data_dir}/nhankhau.xlsx",
        teaching_methods_path=f"{data_dir}/PPGDfull.xlsx",
        assessment_methods_path=f"{data_dir}/PPDGfull.xlsx",
        conduct_scores_path=f"{data_dir}/diemrenluyen.xlsx",   # optional
        attendance_path=f"{data_dir}/Dữ liệu điểm danh Khoa FIRA.xlsx",  # optional
        study_hours_path=f"{data_dir}/tuhoc.xlsx",             # optional
    )
    _predict_pipeline.load_model()

    # --- AnalysisPipeline ---
    _analysis_pipeline = AnalysisPipeline(model_path=model_path)
    _analysis_pipeline.load_model()

    yield  # ứng dụng chạy

    # Cleanup nếu cần
    # _predict_pipeline.explainer.clear_cache()

app = FastAPI(lifespan=lifespan)
```

> **Lưu ý:** `DiemTong.xlsx` là optional khi predict. Nếu MSSV/môn không có trong DiemTong,  
> pipeline tự động fallback dùng nhân khẩu + PPGD/PPDG.

---

## 4. Data contract

### 4.1 Khi backend dùng file Excel (đơn giản nhất)

Backend export MySQL ra file Excel rồi đặt vào thư mục `data/`. Pipeline tự đọc.

```
data/
├── DiemTong.xlsx          # điểm thi hệ 10 (optional cho predict)
├── nhankhau.xlsx          # nhân khẩu sinh viên
├── PPGDfull.xlsx          # phương pháp giảng dạy
├── PPDGfull.xlsx          # phương pháp đánh giá
├── diemrenluyen.xlsx      # điểm rèn luyện (optional)
├── tuhoc.xlsx             # giờ tự học (optional)
└── Dữ liệu điểm danh Khoa FIRA.xlsx   # điểm danh (optional)
```

### 4.2 Cột tối thiểu cần có trong mỗi file

| File | Cột bắt buộc |
|------|-------------|
| DiemTong.xlsx | `Student_ID`, `Subject_ID`, `Lecturer_ID`, `Score` (điểm hệ 10) |
| nhankhau.xlsx | `Student_ID`, `Gender`, `Province` (hoặc tương đương) |
| PPGDfull.xlsx | `Subject_ID`, `TM_score` (hoặc Teaching_Method_score) |
| PPDGfull.xlsx | `Subject_ID`, `EM_score` (hoặc Assessment_Method_score) |

> Xem chi tiết cột trong [docs/data_model.md](data_model.md).

### 4.3 Khi backend muốn truyền DataFrame trực tiếp (tích hợp sâu hơn)

```python
import pandas as pd
from ml_clo.data.mergers import create_student_record_from_ids

# Lấy từ MySQL → DataFrame
demographics_df  = pd.read_sql("SELECT * FROM students", conn)
teaching_df      = pd.read_sql("SELECT * FROM teaching_methods", conn)
assessment_df    = pd.read_sql("SELECT * FROM assessment_methods", conn)
study_hours_df   = pd.read_sql("SELECT * FROM study_hours", conn)

# Tạo record cho một sinh viên cụ thể
record_df = create_student_record_from_ids(
    student_id="19050006",
    subject_id="INF0823",
    lecturer_id="90316",
    demographics_df=demographics_df,
    teaching_methods_df=teaching_df,
    assessment_methods_df=assessment_df,
    study_hours_df=study_hours_df,      # optional
)

# Truyền vào pipeline (cần tích hợp thêm ở pipeline layer)
```

> Hiện tại pipeline đọc file trực tiếp. Nếu muốn truyền DataFrame, cần thêm overload vào pipeline (xem [Lộ trình phát triển](#lộ-trình-phát-triển)).

---

## 5. API Predict (cá nhân)

### FastAPI endpoint

```python
# app/routers/predict.py
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ml_clo.utils.exceptions import ModelLoadError, PredictionError, DataValidationError

router = APIRouter()

class PredictRequest(BaseModel):
    student_id: str
    subject_id: str
    lecturer_id: str
    actual_clo_score: Optional[float] = None  # điểm thực (môn đã học)

class PredictResponse(BaseModel):
    predicted_clo_score: float
    actual_clo_score: Optional[float] = None
    summary: str
    reasons: list
    student_id: Optional[str] = None
    subject_id: Optional[str] = None
    lecturer_id: Optional[str] = None

@router.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    from app.lifespan import _predict_pipeline

    loop = asyncio.get_event_loop()
    try:
        output = await loop.run_in_executor(
            None,  # default thread pool
            lambda: _predict_pipeline.predict(
                student_id=req.student_id,
                subject_id=req.subject_id,
                lecturer_id=req.lecturer_id,
                actual_clo_score=req.actual_clo_score,
            )
        )
    except DataValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except PredictionError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ModelLoadError as e:
        raise HTTPException(status_code=503, detail=f"Model không sẵn sàng: {e}")

    return output.to_dict()
```

### Ví dụ request / response

**Request:**
```json
POST /predict
{
  "student_id": "19050006",
  "subject_id": "INF0823",
  "lecturer_id": "90316",
  "actual_clo_score": 4.2
}
```

**Response:**
```json
{
  "predicted_clo_score": 3.85,
  "actual_clo_score": 4.2,
  "summary": "Sinh viên có điểm học lực ổn định nhưng thiếu chuyên cần.",
  "student_id": "19050006",
  "subject_id": "INF0823",
  "lecturer_id": "90316",
  "reasons": [
    {
      "reason_key": "Chuyên cần",
      "reason_text": "Đáng kể: Tỷ lệ điểm danh thấp ảnh hưởng đến kết quả học tập.",
      "impact_percentage": 22.5,
      "solutions": ["Nhắc nhở sinh viên tham gia đầy đủ các buổi học."],
      "calibrated": true
    }
  ]
}
```

### Các trường hợp predict

| Trường hợp | Cách gọi |
|-----------|---------|
| Môn đã học, có điểm thực | Truyền `actual_clo_score` — output ưu tiên điểm thực, SHAP vẫn giải thích |
| Môn chưa học | Không truyền `actual_clo_score` — output là điểm dự đoán + lý do |
| MSSV chỉ có trong nhankhau (không có DiemTong) | Pipeline tự fallback, không cần thay đổi gì |
| GV mới (chưa có trong training data) | Pipeline dùng encoding mặc định `__UNKNOWN__` |

---

## 6. API Analyze Class (phân tích lớp)

### FastAPI endpoint

```python
# app/routers/analyze.py
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Union, Dict

router = APIRouter()

class AnalyzeClassRequest(BaseModel):
    subject_id: str
    lecturer_id: str
    # Điểm CLO: một trong các dạng sau:
    clo_scores: Union[
        Dict[str, float],          # {"19050006": 4.2, "19050007": 3.8}
        List[float],               # [4.2, 3.8, 5.1]   (không có MSSV)
        List[List]                 # [["19050006", 4.2], ...]
    ]
    demographics_path: Optional[str] = None  # ghi đè path nếu cần
    teaching_methods_path: Optional[str] = None
    assessment_methods_path: Optional[str] = None

@router.post("/analyze-class")
async def analyze_class(req: AnalyzeClassRequest):
    from app.lifespan import _analysis_pipeline

    loop = asyncio.get_event_loop()
    try:
        output = await loop.run_in_executor(
            None,
            lambda: _analysis_pipeline.analyze_class_from_scores(
                subject_id=req.subject_id,
                lecturer_id=req.lecturer_id,
                clo_scores=req.clo_scores,
                demographics_path=req.demographics_path,
                teaching_methods_path=req.teaching_methods_path,
                assessment_methods_path=req.assessment_methods_path,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return output.to_dict()
```

### Các dạng clo_scores được hỗ trợ

```python
# Dạng 1: Dict {student_id: score}
clo_scores = {"19050006": 4.2, "19050007": 3.8, "19050008": 5.1}

# Dạng 2: List chỉ điểm (không cần MSSV) — phân tích thống kê
clo_scores = [4.2, 3.8, 5.1, 2.0, 4.8]

# Dạng 3: List of tuples/pairs [(student_id, score), ...]
clo_scores = [("19050006", 4.2), ("19050007", 3.8)]
```

> **Lưu ý:** Dạng 1 và 3 (có MSSV) → dùng SHAP → lý do chi tiết theo 7 nhóm sư phạm.  
> Dạng 2 (chỉ điểm) → phân tích thống kê → lý do dựa trên phân phối điểm.

### Response mẫu

```json
{
  "summary": "Lớp có điểm CLO trung bình thấp (3.2/6). Chuyên cần và Học lực là hai yếu tố ảnh hưởng nhiều nhất.",
  "subject_id": "INF0823",
  "lecturer_id": "90316",
  "total_students": 35,
  "common_reasons": [
    {
      "reason_key": "Chuyên cần",
      "reason_text": "Rất nghiêm trọng: Tỷ lệ vắng mặt cao ảnh hưởng đến toàn lớp.",
      "average_impact_percentage": 28.3,
      "affected_students_count": 18,
      "priority_solutions": [
        "Xây dựng chính sách điểm danh nghiêm ngặt hơn.",
        "Liên hệ sớm với sinh viên có nguy cơ vắng mặt."
      ],
      "calibrated": true
    }
  ]
}
```

---

## 7. API Train (huấn luyện lại model)

```python
# app/routers/train.py — thường chỉ gọi nội bộ hoặc admin
import asyncio
from fastapi import APIRouter, BackgroundTasks
from ml_clo import TrainingPipeline

router = APIRouter()

@router.post("/train")
async def trigger_training(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_training)
    return {"status": "training started"}

def _run_training():
    pipeline = TrainingPipeline(
        exam_scores_path="data/DiemTong.xlsx",
        conduct_scores_path="data/diemrenluyen.xlsx",
        demographics_path="data/nhankhau.xlsx",
        teaching_methods_path="data/PPGDfull.xlsx",
        assessment_methods_path="data/PPDGfull.xlsx",
        attendance_path="data/Dữ liệu điểm danh Khoa FIRA.xlsx",
        study_hours_path="data/tuhoc.xlsx",
        output_path="models/model.joblib",
    )
    result = pipeline.run()
    # result chứa: mae, r2, version, n_samples, ...

    # Optional: cross-validate trước khi deploy
    # pipeline.cross_validate(X, y, n_splits=5)

    # Optional: kiểm tra chất lượng dữ liệu
    # report = pipeline.report_data_quality(training_df)
```

### Kết quả train

```python
result = pipeline.run()
# {
#   "version": "v1.0_20260413_120000",
#   "mae": 0.3945,
#   "r2": 0.7980,
#   "n_samples": 1234,
#   "output_path": "models/model.joblib"
# }
```

> **Quan trọng:** Sau khi train, cần reload lại `PredictionPipeline` và `AnalysisPipeline`  
> để dùng model mới. Xem [Hot-reload model](#hot-reload-model).

---

## 8. Output schemas

### IndividualAnalysisOutput (predict cá nhân)

| Field | Type | Mô tả |
|-------|------|-------|
| `predicted_clo_score` | `float` | Điểm dự đoán (0–6) |
| `actual_clo_score` | `float \| null` | Điểm thực (nếu được truyền vào) |
| `summary` | `str` | Tóm tắt lý do bằng tiếng Việt |
| `reasons` | `List[Reason]` | Danh sách lý do chi tiết |
| `student_id` | `str \| null` | MSSV |
| `subject_id` | `str \| null` | Mã môn |
| `lecturer_id` | `str \| null` | Mã giảng viên |

**Reason object:**

| Field | Type | Mô tả |
|-------|------|-------|
| `reason_key` | `str` | Nhóm sư phạm (Tự học, Chuyên cần, Rèn luyện, Học lực, Giảng dạy, Đánh giá, Cá nhân) |
| `reason_text` | `str` | Lý do bằng tiếng Việt (có prefix mức độ) |
| `impact_percentage` | `float` | Tỷ lệ ảnh hưởng (0–100) |
| `solutions` | `List[str]` | Giải pháp đề xuất |
| `calibrated` | `bool` | Lý do có được calibrate theo giá trị feature thực không |

### ClassAnalysisOutput (phân tích lớp)

| Field | Type | Mô tả |
|-------|------|-------|
| `summary` | `str` | Tóm tắt lớp |
| `subject_id` | `str \| null` | Mã môn |
| `lecturer_id` | `str \| null` | Mã giảng viên |
| `total_students` | `int \| null` | Số sinh viên phân tích |
| `common_reasons` | `List[ClassReason]` | Lý do chung cho lớp |

**ClassReason object:**

| Field | Type | Mô tả |
|-------|------|-------|
| `reason_key` | `str` | Nhóm sư phạm |
| `reason_text` | `str` | Lý do tiếng Việt |
| `average_impact_percentage` | `float` | Trung bình tỷ lệ ảnh hưởng |
| `affected_students_count` | `int` | Số SV bị ảnh hưởng (SHAP âm) |
| `priority_solutions` | `List[str]` | Giải pháp ưu tiên |
| `calibrated` | `bool` | Có calibrate không |

### Serialize

```python
# Dict (cho FastAPI response)
output.to_dict()

# JSON string (ghi file / log)
output.to_json(indent=2)

# ClassAnalysisOutput: thêm average_predicted_score (ẩn mặc định)
output.to_dict(include_average_predicted=True)
```

---

## 9. Xử lý lỗi

### Exception hierarchy

```
MLCLOError (base)
├── ModelLoadError     — model file không tồn tại, encoding không khớp
├── DataValidationError — dữ liệu đầu vào sai (thiếu cột, ID rỗng, v.v.)
├── PredictionError    — lỗi trong quá trình tính toán
├── DataLoadError      — không đọc được file Excel
└── ConfigurationError — cấu hình sai
```

### Mapping sang HTTP status

```python
from ml_clo.utils.exceptions import (
    ModelLoadError, DataValidationError, PredictionError,
    DataLoadError, ConfigurationError
)

@app.exception_handler(ModelLoadError)
async def model_load_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})

@app.exception_handler(DataValidationError)
async def validation_error(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

@app.exception_handler(PredictionError)
async def prediction_error(request, exc):
    return JSONResponse(status_code=500, content={"detail": str(exc)})

@app.exception_handler(DataLoadError)
async def data_load_error(request, exc):
    return JSONResponse(status_code=500, content={"detail": f"Data error: {exc}"})
```

### Ví dụ lỗi thường gặp

| Lỗi | Nguyên nhân | Cách xử lý |
|-----|------------|-----------|
| `ModelLoadError: encoding_method mismatch` | Model cũ (train trước hash_v2) | Retrain model mới |
| `DataValidationError: student_id is empty` | MSSV rỗng hoặc None | Validate đầu vào trước khi gọi |
| `DataValidationError: score out of range` | Điểm CLO không nằm trong [0, 6] | Kiểm tra dữ liệu đầu vào |
| `DataLoadError: file not found` | Path Excel sai | Kiểm tra env variable DATA_DIR |
| `PredictionError` | Thiếu features / lỗi SHAP | Xem log chi tiết |

---

## 10. Cấu hình nâng cao

### Điều chỉnh ensemble weights

```python
# Sau khi load model, có thể điều chỉnh trọng số RF vs GB
pipeline = PredictionPipeline(model_path="models/model.joblib", ...)
pipeline.load_model()

# Tăng GB weight (tốt hơn với outlier)
pipeline.model.set_weights(rf_weight=0.4, gb_weight=0.6)
```

### Dự đoán với khoảng tin cậy

```python
import numpy as np

# Gọi trực tiếp trên model nếu cần confidence interval
X = ...  # feature vector đã chuẩn bị
result = pipeline.model.predict_with_uncertainty(X)
# result = {
#   "prediction": 3.85,
#   "rf_std": 0.42,
#   "confidence_interval_low": 3.01,
#   "confidence_interval_high": 4.69
# }
```

### Quản lý bộ nhớ SHAP

```python
# SHAP explainer cache tốn bộ nhớ — xóa khi cần
# (thường không cần, trừ khi có nhiều model chạy song song)
pipeline.explainer.clear_cache()
```

### Hot-reload model

```python
import threading

_pipeline_lock = threading.Lock()
_predict_pipeline = None

def reload_model(new_model_path: str):
    """Load model mới rồi swap atomic."""
    global _predict_pipeline

    new_pipeline = PredictionPipeline(
        model_path=new_model_path,
        exam_scores_path=...,
        # ... các path khác
    )
    new_pipeline.load_model()

    with _pipeline_lock:
        _predict_pipeline = new_pipeline
```

### Audit log

```python
from ml_clo.utils.audit_log import set_audit_log_path

# Gọi một lần khi startup
set_audit_log_path("logs/predictions.jsonl")

# Mỗi lần predict() tự động ghi vào file này:
# {"timestamp": "...", "student_id": "19050006", "subject_id": "INF0823",
#  "lecturer_id": "90316", "predicted_score": 3.85, "model_version": "v1.0_..."}
```

---

## 11. Lưu ý threading / async

### Vấn đề

Pipeline gọi Pandas, scikit-learn, SHAP — tất cả **synchronous**. Gọi trực tiếp trong `async def` sẽ block event loop của FastAPI.

### Giải pháp: `run_in_executor`

```python
import asyncio

@router.post("/predict")
async def predict(req: PredictRequest):
    loop = asyncio.get_event_loop()

    output = await loop.run_in_executor(
        None,   # dùng default ThreadPoolExecutor
        lambda: _predict_pipeline.predict(
            student_id=req.student_id,
            subject_id=req.subject_id,
            lecturer_id=req.lecturer_id,
        )
    )
    return output.to_dict()
```

### Thread safety

- `PredictionPipeline.predict()`: **thread-safe** (không có shared mutable state trong predict call).
- `AnalysisPipeline.analyze_class_from_scores()`: **thread-safe**.
- `set_audit_log_path()`: **thread-safe** (dùng `threading.Lock()`).
- `EnsembleModel.set_weights()`: **không thread-safe** — gọi khi startup, không gọi concurrent.
- `EnsembleSHAPExplainer.clear_cache()`: **không thread-safe** — gọi khi idle.

### Số workers

SHAP tính toán nặng. Khuyến nghị:

```python
# uvicorn hoặc gunicorn
uvicorn app.main:app --workers 2 --host 0.0.0.0 --port 8000

# Hoặc dùng ProcessPoolExecutor cho SHAP nặng
from concurrent.futures import ProcessPoolExecutor
executor = ProcessPoolExecutor(max_workers=2)
```

---

## Lộ trình phát triển

Các cải tiến có thể làm trong tương lai (không cần ngay cho tích hợp ban đầu):

| Hạng mục | Mô tả |
|---------|-------|
| DataFrame input | Thêm overload vào pipeline để nhận DataFrame thay vì file path — loại bỏ bước export Excel từ MySQL |
| Async-native | Bọc pipeline trong `asyncio.to_thread()` (Python 3.9+) thay vì `run_in_executor` |
| Tích hợp khảo sát | File `Khảo sát...xlsx` (280 SV) chưa được dùng — tích hợp sẽ bổ sung feature điểm khảo sát vào model |
| Model versioning | Quản lý nhiều version model, cho phép A/B test hoặc rollback |

---

## Checklist tích hợp

- [ ] Cài `ml_clo` vào môi trường backend
- [ ] Set env variables: `MODEL_PATH`, `DATA_DIR`, `AUDIT_LOG_PATH` (optional)
- [ ] Khởi tạo pipeline trong lifespan handler (startup)
- [ ] Bọc pipeline calls trong `run_in_executor` (async endpoints)
- [ ] Map exceptions → HTTP status codes
- [ ] Test endpoint `/predict` với MSSV có sẵn trong DiemTong
- [ ] Test endpoint `/predict` với MSSV chỉ có trong nhankhau (fallback mode)
- [ ] Test endpoint `/analyze-class` với dict điểm có MSSV
- [ ] Test endpoint `/analyze-class` với list điểm không MSSV
- [ ] Verify model file không commit vào git — lưu ở object storage / volume
