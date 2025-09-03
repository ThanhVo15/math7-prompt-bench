import re
from typing import List, Dict
from src.contracts.contracts import Tokenizer

class AdvancedTokenizer(Tokenizer):
    """Tokenizer hỗ trợ đa ngôn ngữ và math symbols"""
    
    def __init__(self):
        # Patterns cho các loại token
        self.patterns = {
            'math_expr': r'\d+\.?\d*\s*[+\-*/=<>≤≥≠]\s*\d+\.?\d*',  # 2+3, x=5
            'numbers': r'\d+\.?\d*',                                 # 123, 3.14
            'vietnamese': r'[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]+',
            'english': r'[a-zA-Z]+(?:\'[a-zA-Z]+)?',                # words + contractions
            'punctuation': r'[.!?…,;:()[\]{}"\'-]',
            'math_symbols': r'[+\-*/=<>≤≥≠∑∏∫√∞π∆∇]',
            'whitespace': r'\s+',
            'other': r'\S'
        }
        
        # Compile patterns
        self.compiled_patterns = {
            name: re.compile(pattern, re.UNICODE | re.IGNORECASE) 
            for name, pattern in self.patterns.items()
        }
    
    def tokenize(self, text: str) -> List[str]:
        """Advanced tokenization với classification"""
        if not text.strip():
            return []
            
        tokens = []
        i = 0
        text = text.strip()
        
        while i < len(text):
            matched = False
            
            # Thử match theo thứ tự ưu tiên
            for pattern_name in ['math_expr', 'numbers', 'vietnamese', 'english', 
                               'math_symbols', 'punctuation']:
                pattern = self.compiled_patterns[pattern_name]
                match = pattern.match(text, i)
                
                if match:
                    token = match.group().strip()
                    if token:  # Bỏ token rỗng
                        tokens.append(token)
                    i = match.end()
                    matched = True
                    break
            
            if not matched:
                # Skip whitespace hoặc lấy ký tự đơn
                if text[i].isspace():
                    i += 1
                else:
                    tokens.append(text[i])
                    i += 1
        
        return tokens
    
    def count(self, text: str) -> int:
        return len(self.tokenize(text))
    
    def get_token_types(self, text: str) -> Dict[str, List[str]]:
        """Phân loại tokens theo type"""
        tokens = self.tokenize(text)
        categorized = {pattern_name: [] for pattern_name in self.patterns}
        
        for token in tokens:
            for pattern_name, pattern in self.compiled_patterns.items():
                if pattern.fullmatch(token):
                    categorized[pattern_name].append(token)
                    break
        
        return {k: v for k, v in categorized.items() if v}