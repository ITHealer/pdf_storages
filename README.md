pdf_storage/
├── app/
│   ├── main.py           ← FastAPI app, lifespan, global error handler
│   ├── config.py         ← Pydantic-settings đọc từ .env
│   ├── routers/upload.py ← 3 endpoints: POST, GET, DELETE
│   ├── services/storage.py ← toàn bộ filesystem logic
│   ├── schemas/upload.py ← Pydantic response models
│   └── utils/validators.py ← extension + magic bytes + size check
├── tests/test_upload.py  ← 9 integration tests
├── storage/              ← PDF lưu ở đây
└── requirements.txt
