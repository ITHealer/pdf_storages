from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Storage settings
    storage_dir: Path = Path("storage") # Thư mục lưu trữ file upload
    max_file_size_mb: int = 200 # Giới hạn kích thước file upload (MB)
    allowed_extensions: str = "jpg,jpeg,png,gif,txt,pdf,docx,xlsx" # Các định dạng file được phép upload

    # App settings
    app_env: str = "development" # Môi trường ứng dụng (development, production, etc.)
    app_title: str = "File Storage API" # Tiêu đề ứng dụng
    app_version: str = "1.0.0" # Phiên bản ứng dụng

    @property 
    def max_file_size_bytes(self) -> int:
        """
        - Tính toán kích thước file tối đa cho phép (MB -> Bytes)
        - Gọi:
            settings.max_file_size_bytes: Sử dụng để lấy giá trị này dưới dạng bytes, rất tiện khi kiểm tra kích thước file upload.
            -> thay vì phải gọi kiểu: settings.max_file_size_bytes() vì call hàm / method: phải có ngoặc () 
        - Nhưng với @property, một hàm sẽ được dùng như thể nó là một thuộc tính.
        - When use:
            a. Giá trị được tính từ các thuộc tính khác của lớp, nhưng được truy cập như một thuộc tính thông thường.
            b. Muốn che giấu logic bên trong nhưng vẫn cho người dùng truy cập đơn giản
            c. Muốn sau này thay đổi cách tính mà code bên ngoài không phải sửa
        """
        return self.max_file_size_mb * 1024 * 1024
    
    @property
    def allowed_extensions_set(self) -> set[str]:
        """
        - Chuyển chuỗi allowed_extensions thành một tập hợp (set) để dễ dàng kiểm tra.
        - Khi sử dụng:
            settings.allowed_extensions_set: Trả về một set chứa các phần mở rộng file được phép, giúp việc kiểm tra nhanh hơn.
        """
        return set(ext.strip().lower() for ext in self.allowed_extensions.split(","))
    
settings = Settings()