import re
from typing import List, Dict

# Định nghĩa một interface trừu tượng để dễ mở rộng sau này
class Tokenizer:
    def tokenize(self, text: str) -> List[str]:
        raise NotImplementedError

    def count(self, text: str) -> int:
        raise NotImplementedError

class AdvancedTokenizer(Tokenizer):
    """Tokenizer hỗ trợ đa ngôn ngữ và math symbols"""
    
    def __init__(self):
        self.patterns = {
            'math_expr': r'\d+\.?\d*\s*[+\-*/=<>≤≥≠]\s*\d+\.?\d*',
            'numbers': r'\d+\.?\d*',
            'vietnamese': r'[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]+',
            'english': r'[a-zA-Z]+(?:\'[a-zA-Z]+)?',
            'punctuation': r'[.!?…,;:()[\]{}"\'-]',
            'math_symbols': r'[+\-*/=<>≤≥≠∑∏∫√∞π∆∇]',
            'whitespace': r'\s+',
            'other': r'\S'
        }
        
        self.compiled_patterns = {
            name: re.compile(pattern, re.UNICODE | re.IGNORECASE) 
            for name, pattern in self.patterns.items()
        }
    
    def tokenize(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []
            
        tokens = []
        i = 0
        text_len = len(text)
        
        while i < text_len:
            # Ưu tiên match khoảng trắng để bỏ qua
            whitespace_match = self.compiled_patterns['whitespace'].match(text, i)
            if whitespace_match:
                i = whitespace_match.end()
                continue

            matched = False
            # Thử match theo thứ tự ưu tiên
            for pattern_name in ['math_expr', 'numbers', 'vietnamese', 'english', 'math_symbols', 'punctuation']:
                pattern = self.compiled_patterns[pattern_name]
                match = pattern.match(text, i)
                
                if match:
                    token = match.group(0)
                    tokens.append(token)
                    i = match.end()
                    matched = True
                    break
            
            if not matched:
                # Nếu không match pattern nào, lấy ký tự đơn
                tokens.append(text[i])
                i += 1
        
        return tokens
    
    def count(self, text: str) -> int:
        return len(self.tokenize(text))