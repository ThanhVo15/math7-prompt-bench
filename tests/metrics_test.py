def test_metrics_examples():
    from src.services.tokenizer import AdvancedTokenizer
    from src.services.metrics import BasicMetrics
    
    tokenizer = AdvancedTokenizer()
    metrics = BasicMetrics()
    
    # Test case 1: Simple Vietnamese math prompt
    prompt1 = "Giải phương trình: 2x + 5 = 11. Tìm giá trị của x."
    result1 = metrics.compute_detailed(prompt1, tokenizer)
    
    print(f"Prompt 1 MATTR: {result1['metrics'].mattr:.3f}")
    print(f"Prompt 1 Reading Ease: {result1['metrics'].reading_ease:.1f}")
    print(f"Token count: {result1['metrics'].token_count}")
    print(f"Text stats: {result1['text_stats']}")
    
    # Test case 2: Complex prompt  
    prompt2 = """Phân tích và giải quyết bài toán phức tạp sau đây: Trong một hệ thống phương trình vi phân tuyến tính đồng nhất bậc hai với các hệ số hằng số, hãy xác định nghiệm tổng quát."""
    result2 = metrics.compute_detailed(prompt2, tokenizer)
    
    print(f"\nPrompt 2 MATTR: {result2['metrics'].mattr:.3f}")
    print(f"Prompt 2 Reading Ease: {result2['metrics'].reading_ease:.1f}")
    
    # Verify: Prompt 2 should have lower reading ease (harder)
    assert result2['metrics'].reading_ease < result1['metrics'].reading_ease

# Run test
if __name__ == "__main__":
    test_metrics_examples()