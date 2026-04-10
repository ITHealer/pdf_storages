from pydantic import BaseModel, Field
from datetime import datetime


class UploadResponse(BaseModel):
    # SHA-256: là một chuỗi ký tự dài 64 ký tự (hệ thập lục phân) được tạo ra từ thuật toán băm mật mã, dùng để xác minh tính toàn vẹn của tệp tin
    file_id: str = Field(..., description="SHA-256 checksum (dedup key) của file đã upload") 
    filename: str = Field(..., description="Tên gốc của file đã upload")
    size_bytes: int = Field(..., description="Kích thước file đã upload (bytes)")
    path: str = Field(..., description="Đường dẫn lưu trữ file trên server")
    uploaded_at: datetime = Field(..., description="Thời gian file được upload (UTC)")
    already_exists: bool = Field(..., description="True nếu file đã tồn tại (dựa trên SHA-256), False nếu file mới được lưu")


class FileListItem(BaseModel):
    file_id: str = Field(..., description="SHA-256 checksum (dedup key) của file")
    filename: str = Field(..., description="Tên gốc của file")
    size_bytes: int = Field(..., description="Kích thước file (bytes)")
    path: str = Field(..., description="Đường dẫn lưu trữ file trên server")
    created_at: datetime = Field(..., description="Thời gian file được tạo (UTC)")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Thông tin chi tiết về lỗi xảy ra")