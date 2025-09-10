import streamlit as st
import gspread
from gspread_dataframe import set_with_dataframe
import pandas as pd
from typing import List
from pydantic import BaseModel

# --- LỚP QUẢN LÝ GOOGLE SHEETS ---
class GoogleSheetManager:
    def __init__(self):
        self.client = self._connect()
        self.spreadsheet_name = st.secrets["google_sheets"]["spreadsheet_name"]

    def _connect(self):
        try:
            creds = st.secrets["gcp_service_account"]
            return gspread.service_account_from_dict(creds)
        except Exception as e:
            st.error(f"Lỗi kết nối Google Sheets: {e}")
            return None

    def _get_worksheet(self, sheet_name: str):
        if not self.client:
            return None
        try:
            spreadsheet = self.client.open(self.spreadsheet_name)
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="1", cols="1")
            return worksheet
        except gspread.SpreadsheetNotFound:
            st.error(f"Không tìm thấy Google Sheet với tên '{self.spreadsheet_name}'. Vui lòng tạo và chia sẻ quyền editor cho email service account.")
            return None
        except Exception as e:
            st.error(f"Lỗi khi mở worksheet '{sheet_name}': {e}")
            return None

    def append_data(self, sheet_name: str, records: List[BaseModel]):
        worksheet = self._get_worksheet(sheet_name)
        if not worksheet or not records:
            return

        # Chuyển đổi Pydantic models thành list of dicts
        data_to_append = [record.dict() for record in records]
        df_to_append = pd.DataFrame(data_to_append)

        # Đảm bảo các cột datetime được định dạng đúng
        for col in df_to_append.select_dtypes(include=['datetime64[ns, UTC]']).columns:
            df_to_append[col] = df_to_append[col].dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        try:
            # Lấy tất cả dữ liệu hiện có để kiểm tra header
            existing_data = worksheet.get_all_records()
            if not existing_data:
                # Nếu sheet rỗng, ghi cả header
                set_with_dataframe(worksheet, df_to_append, include_index=False, resize=True)
            else:
                # Nếu đã có dữ liệu, chỉ append
                worksheet.append_rows(df_to_append.values.tolist(), value_input_option='USER_ENTERED')
            st.toast(f"Đã lưu vào sheet '{sheet_name}'!", icon="✅")
        except Exception as e:
            st.error(f"Lỗi khi ghi dữ liệu vào sheet '{sheet_name}': {e}")

# --- KHỞI TẠO SINGLETON OBJECT ---
# Sử dụng @st.cache_resource để chỉ khởi tạo một lần mỗi session
@st.cache_resource
def get_gsheet_manager():
    return GoogleSheetManager()