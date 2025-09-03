from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime

from src.domain.entities import (
    Sessions, Messages, PromptMetrics, Solution
)

class Tokenizer(ABC):
    "Interface để đếm và chia nhỏ văn bản thành tokens"

    @abstractmethod
    def count(self, text: str) -> int:
        """Đếm số lượng token trong text"""
        ...
    
    @abstractmethod
    def tokenize(self, text: str) -> List[str]:
        """Chia text thành các danh sách token"""
        ...

class MetricsService(ABC):
    """Interface để tính toán các metrics của prompt"""

    @abstractmethod
    def compute(self, prompt_text: str,
                tokenizer:Tokenizer,
                w: int = 25) -> PromptMetrics:
        """Tính MATTR, token count, reading ease cho prompt"""
        ...

class ModelClient(ABC):
    """Interface để gọi AI model"""
    
    @abstractmethod
    def generate(self, full_prompt: str, **kwargs) -> str:
        """Gửi prompt tới AI model và nhận response (raw text chứa JSON)"""
        ...

class Repository(ABC):
    """Interface để lưu trữ data (có thể là database, file, Google Sheets, v.v.)"""
    
    @abstractmethod
    def save_session(self, session: Sessions) -> None:
        """Lưu thông tin phiên làm việc"""
        ...
    
    @abstractmethod
    def save_message(self, message: Messages) -> None:
        """Lưu tin nhắn chat"""
        ...
    
    # @abstractmethod
    # def save_prompt_template(self, template: Dict[str, Any]) -> None:
    #     """Lưu prompt template"""
    #     ...
    
    @abstractmethod
    def save_metrics(self, metrics: PromptMetrics) -> None:
        """Lưu kết quả tính toán metrics"""
        ...
    
    # @abstractmethod
    # def save_model_run(self, run_info: Dict[str, Any]) -> None:
    #     """Lưu thông tin chạy model (prompt + response + metadata)"""
    #     ...
    
    # Methods để đọc data
    @abstractmethod
    def get_messages_by_session(self, session_id: str) -> List[Messages]:
        """Lấy tất cả messages của 1 session"""
        ...
    
    # @abstractmethod
    # def get_prompt_templates(self) -> List[Dict[str, Any]]:
    #     """Lấy danh sách prompt templates"""
    #     ...

class AuthService(ABC):
    """Interface để xác thực người dùng"""
    
    @abstractmethod
    def authenticate(self, username: str, password: str) -> bool:
        """Kiểm tra username/password có đúng không"""
        ...
    
    @abstractmethod
    def get_user_role(self, username: str) -> str:
        """Lấy role của user (admin/user)"""
        ...
    
    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash password để lưu trữ an toàn"""
        ...

# class ConfigService(ABC):
#     """Interface để quản lý cấu hình"""
    
#     @abstractmethod
#     def load_prompt_templates(self) -> Dict[str, Any]:
#         """Load prompt templates từ file config"""
#         ...
    
#     @abstractmethod
#     def save_prompt_templates(self, templates: Dict[str, Any]) -> None:
#         """Lưu prompt templates vào file config"""
#         ...
    
#     @abstractmethod
#     def get_app_settings(self) -> Dict[str, Any]:
#         """Lấy các settings của app"""
#         ...