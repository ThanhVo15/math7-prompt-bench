# src/services/google_sheets.py
import streamlit as st
import gspread
from gspread_dataframe import set_with_dataframe
import pandas as pd
from typing import List
from pydantic import BaseModel

class GoogleSheetManager:
    def __init__(self):
        self.client = self._connect()
        try:
            self.spreadsheet_name = st.secrets["google_sheets"]["spreadsheet_name"]
        except Exception:
            self.spreadsheet_name = None

    def _connect(self):
        try:
            creds = st.secrets["gcp_service_account"]
            return gspread.service_account_from_dict(creds)
        except Exception as e:
            st.error(f"Lỗi kết nối Google Sheets: {e}")
            return None

    def _get_worksheet(self, sheet_name: str):
        if not self.client or not self.spreadsheet_name:
            return None
        try:
            spreadsheet = self.client.open(self.spreadsheet_name)
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="1", cols="1")
            return worksheet
        except gspread.SpreadsheetNotFound:
            st.error(
                f"Không tìm thấy Google Sheet với tên '{self.spreadsheet_name}'. "
                "Vui lòng tạo và chia sẻ quyền editor cho email service account."
            )
            return None
        except Exception as e:
            st.error(f"Lỗi khi mở worksheet '{sheet_name}': {e}")
            return None

    def append_data(self, sheet_name: str, records: list):
            worksheet = self._get_worksheet(sheet_name)
            if not worksheet or not records:
                return

            # ===================================================================
            # === NÂNG CẤP: Logic thông minh để xử lý cả object và dictionary ===
            # ===================================================================
            data_to_append = []
            for record in records:
                if isinstance(record, dict):
                    # Nếu đã là dictionary, dùng luôn
                    data_to_append.append(record)
                elif hasattr(record, 'model_dump'): # Dành cho Pydantic v2
                    data_to_append.append(record.model_dump())
                elif hasattr(record, 'dict'): # Dành cho Pydantic v1
                    data_to_append.append(record.dict())
                else:
                    # Fallback cho các loại khác như dataclass
                    from dataclasses import asdict, is_dataclass
                    if is_dataclass(record):
                        data_to_append.append(asdict(record))
                    else:
                        # Nếu không nhận dạng được, cứ thử append
                        data_to_append.append(record)
            
            # Nếu data_to_append vẫn rỗng, thoát sớm
            if not data_to_append:
                return
                
            df_to_append = pd.DataFrame(data_to_append)

            # Chuẩn hóa datetime UTC -> string
            for col in df_to_append.select_dtypes(include=["datetime64[ns, UTC]"]).columns:
                df_to_append[col] = df_to_append[col].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            try:
                # Kiểm tra xem sheet có header chưa
                header = worksheet.row_values(1)
                if not header:
                    # Nếu chưa có, ghi cả header và dữ liệu
                    set_with_dataframe(worksheet, df_to_append, include_index=False, resize=True)
                else:
                    # Nếu có rồi, chỉ nối thêm dòng
                    # Sắp xếp lại cột của dataframe cho khớp với header của sheet
                    df_aligned = df_to_append.reindex(columns=header).fillna('')
                    worksheet.append_rows(
                        df_aligned.values.tolist(), value_input_option="USER_ENTERED"
                    )
                # st.toast(f"Đã lưu vào sheet '{sheet_name}'!", icon="✅") # Có thể bỏ comment dòng này nếu muốn thấy toast
            except Exception as e:
                st.error(f"Lỗi khi ghi dữ liệu vào sheet '{sheet_name}': {e}")

    def get_df(self, sheet_name: str) -> pd.DataFrame:
        """
        Đọc toàn bộ tab Google Sheets thành DataFrame.
        - Dòng đầu là header.
        - Tự xử lý hàng thiếu cột (pad/truncate).
        - Loại hàng trống hoàn toàn.
        """
        ws = self._get_worksheet(sheet_name)
        if not ws:
            return pd.DataFrame()

        try:
            # Lấy tất cả ô (list[list])
            data = ws.get_all_values()
            if not data or not data[0]:
                return pd.DataFrame()

            header = [str(h).strip() for h in data[0]]
            rows = data[1:]

            # Chuẩn hoá số cột mỗi hàng khớp header
            ncol = len(header)
            norm_rows = []
            for r in rows:
                r = list(r)
                if len(r) < ncol:
                    r += [""] * (ncol - len(r))
                elif len(r) > ncol:
                    r = r[:ncol]
                norm_rows.append([str(x) if x is not None else "" for x in r])

            df = pd.DataFrame(norm_rows, columns=header)

            # Bỏ các hàng trống hoàn toàn
            df = df[~df.apply(lambda s: all(str(x).strip() == "" for x in s), axis=1)]
            return df

        except Exception as e:
            st.error(f"Lỗi khi đọc sheet '{sheet_name}': {e}")
            return pd.DataFrame()


@st.cache_resource
def get_gsheet_manager(_version: int = 2):
    return GoogleSheetManager()