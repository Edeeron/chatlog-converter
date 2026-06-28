"""
ChatLog Converter - Comprehensive Test Suite
Tests for all core functionality after refactoring
"""

import os
import sys
import csv
import json
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import (
    convert_to_json,
    parse_file,
    auto_detect_columns,
    extract_agent,
    classify_agents,
    get_file_size_mb
)


def create_test_csv(file_path: str, num_rows: int = 100):
    """
    Create a test CSV file with sample chat data.
    
    Args:
        file_path: Path to save the CSV file
        num_rows: Number of rows to generate
    """
    agents = ['GPT-4', 'Claude', '助手A', 'Bot-X']
    roles = ['user', 'assistant']
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['agent_name', 'role', 'content', 'timestamp'])
        
        for i in range(num_rows):
            agent = agents[i % len(agents)]
            role = roles[i % 2]
            content = f"这是第{i+1}条消息，来自{agent}的{role}回复。" * 3
            timestamp = f"2024-01-{(i % 28) + 1:02d} {(i % 24):02d}:{(i % 60):02d}:00"
            writer.writerow([agent, role, content, timestamp])
    
    return file_path


def test_parse_and_detect():
    """Test 1: Parse file and auto-detect columns."""
    print("\n" + "="*70)
    print("Test 1: Parse and Auto-Detect")
    print("="*70)
    
    # Create test file
    test_dir = Path(__file__).parent / "test_output"
    test_file = test_dir / "test_basic.csv"
    create_test_csv(str(test_file), 100)
    
    file_size = get_file_size_mb(str(test_file))
    print(f"✓ Test file created: {test_file} ({file_size:.2f} MB)")
    
    # Parse file
    result = parse_file(str(test_file))
    detected = auto_detect_columns(result)
    print(f"✓ Parsed {len(result.rows)} rows, {len(result.headers)} columns")
    print(f"  Detected columns:")
    print(f"    - Agent: {detected.agent_col}")
    print(f"    - Role: {detected.role_col}")
    print(f"    - Content: {detected.content_col}")
    print(f"    - Time: {detected.time_col}")
    
    assert detected.agent_col == 'agent_name'
    assert detected.role_col == 'role'
    assert detected.content_col == 'content'
    assert detected.time_col == 'timestamp'
    
    print("✅ Test 1 PASSED\n")
    return True


def test_convert_finetune_mode():
    """Test 2: Convert to JSON (finetune mode)."""
    print("\n" + "="*70)
    print("Test 2: Convert to JSON (Finetune Mode)")
    print("="*70)
    
    test_dir = Path(__file__).parent / "test_output"
    test_file = test_dir / "test_basic.csv"
    
    result = parse_file(str(test_file))
    detected = auto_detect_columns(result)
    
    output_file = test_dir / "test_finetune.json"
    start_time = time.time()
    
    proc_result = convert_to_json(
        result=result,
        agent_col=detected.agent_col,
        role_col=detected.role_col,
        content_col=detected.content_col,
        time_col=detected.time_col,
        mode='finetune',
        save_path=str(output_file),
        reverse=False
    )
    
    elapsed = time.time() - start_time
    
    print(f"✓ Conversion completed in {elapsed:.2f}s")
    print(f"  Message: {proc_result.message}")
    print(f"  Success: {proc_result.success}")
    
    # Verify output
    assert proc_result.success, "Conversion failed"
    assert output_file.exists(), "Output file not created"
    
    with open(output_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"  Conversations: {len(data)}")
    total_msgs = sum(len(conv['messages']) for conv in data)
    print(f"  Total messages: {total_msgs}")
    
    assert len(data) > 0, "No conversations generated"
    assert total_msgs == 100, f"Expected 100 messages, got {total_msgs}"
    
    # Check finetune structure
    first_conv = data[0]
    assert 'conversation_id' in first_conv, "Should have conversation_id"
    assert 'agent_name' in first_conv, "Should have agent_name"
    
    first_msg = first_conv['messages'][0]
    assert 'message_id' in first_msg, "Should have message_id"
    assert 'turn_id' in first_msg, "Should have turn_id"
    assert 'token_count' in first_msg, "Should have token_count"
    assert 'role' in first_msg, "Should have role"
    assert 'content' in first_msg, "Should have content"
    
    print(f"  ✓ Finetune metadata present (message_id, turn_id, token_count)")
    print(f"  Sample message_id: {first_msg['message_id']}")
    print(f"  Sample turn_id: {first_msg['turn_id']}")
    print(f"  Sample token_count: {first_msg['token_count']}")
    
    print("✅ Test 2 PASSED\n")
    return True


def test_convert_context_mode():
    """Test 3: Convert to JSON (context mode)."""
    print("\n" + "="*70)
    print("Test 3: Convert to JSON (Context Mode)")
    print("="*70)
    
    test_dir = Path(__file__).parent / "test_output"
    test_file = test_dir / "test_basic.csv"
    
    result = parse_file(str(test_file))
    detected = auto_detect_columns(result)
    
    output_file = test_dir / "test_context.json"
    
    proc_result = convert_to_json(
        result=result,
        agent_col=detected.agent_col,
        role_col=detected.role_col,
        content_col=detected.content_col,
        time_col=detected.time_col,
        mode='context',
        save_path=str(output_file),
        reverse=False
    )
    
    print(f"✓ Conversion completed")
    print(f"  Message: {proc_result.message}")
    
    # Verify simplified structure
    with open(output_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    first_conv = data[0]
    print(f"  Conversation keys: {list(first_conv.keys())}")
    
    first_msg = first_conv['messages'][0]
    print(f"  Message keys: {list(first_msg.keys())}")
    
    # Context mode should NOT have message_id, turn_id, token_count
    assert 'message_id' not in first_msg, "Context mode should not have message_id"
    assert 'turn_id' not in first_msg, "Context mode should not have turn_id"
    assert 'token_count' not in first_msg, "Context mode should not have token_count"
    
    # Should have role and content
    assert 'role' in first_msg, "Message should have role"
    assert 'content' in first_msg, "Message should have content"
    
    print(f"  ✓ Context mode has no extra metadata")
    
    print("✅ Test 3 PASSED\n")
    return True


def test_extract_agent():
    """Test 4: Extract specific agent."""
    print("\n" + "="*70)
    print("Test 4: Extract Specific Agent")
    print("="*70)
    
    test_dir = Path(__file__).parent / "test_output"
    test_file = test_dir / "test_basic.csv"
    
    result = parse_file(str(test_file))
    detected = auto_detect_columns(result)
    
    output_file = test_dir / "test_extracted.csv"
    proc_result = extract_agent(
        result=result,
        agent_col=detected.agent_col,
        target='GPT-4',
        save_path=str(output_file)
    )
    
    print(f"✓ Extraction completed")
    print(f"  Message: {proc_result.message}")
    
    assert proc_result.success, "Extraction failed"
    
    # Verify extracted file
    with open(output_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        extracted_rows = list(reader)
    
    print(f"  Extracted {len(extracted_rows)} rows")
    assert all(row['agent_name'] == 'GPT-4' for row in extracted_rows), "All rows should be GPT-4"
    
    print("✅ Test 4 PASSED\n")
    return True


def test_classify_agents():
    """Test 5: Classify by agent."""
    print("\n" + "="*70)
    print("Test 5: Classify by Agent")
    print("="*70)
    
    test_dir = Path(__file__).parent / "test_output"
    test_file = test_dir / "test_basic.csv"
    
    result = parse_file(str(test_file))
    detected = auto_detect_columns(result)
    
    proc_result = classify_agents(
        result=result,
        agent_col=detected.agent_col,
        out_dir=str(test_dir)
    )
    
    print(f"✓ Classification completed")
    print(f"  Message: {proc_result.message}")
    
    assert proc_result.success, "Classification failed"
    print(f"  Created {len(proc_result.files)} files")
    
    # Verify files exist
    for fname in proc_result.files:
        fpath = test_dir / fname
        assert fpath.exists(), f"File {fname} should exist"
        print(f"    - {fname}")
    
    print("✅ Test 5 PASSED\n")
    return True


def test_reverse_order():
    """Test 6: Reverse message order."""
    print("\n" + "="*70)
    print("Test 6: Reverse Message Order")
    print("="*70)
    
    test_dir = Path(__file__).parent / "test_output"
    test_file = test_dir / "test_basic.csv"
    
    result = parse_file(str(test_file))
    detected = auto_detect_columns(result)
    
    # Normal order
    output_normal = test_dir / "normal_order.json"
    convert_to_json(
        result=result,
        agent_col=detected.agent_col,
        role_col=detected.role_col,
        content_col=detected.content_col,
        time_col=detected.time_col,
        mode='context',
        save_path=str(output_normal),
        reverse=False
    )
    
    # Reversed order
    output_reversed = test_dir / "reversed_order.json"
    convert_to_json(
        result=result,
        agent_col=detected.agent_col,
        role_col=detected.role_col,
        content_col=detected.content_col,
        time_col=detected.time_col,
        mode='context',
        save_path=str(output_reversed),
        reverse=True
    )
    
    # Compare first conversation's first message
    with open(output_normal, 'r', encoding='utf-8') as f:
        normal_data = json.load(f)
    
    with open(output_reversed, 'r', encoding='utf-8') as f:
        reversed_data = json.load(f)
    
    normal_first_msg = normal_data[0]['messages'][0]['content']
    reversed_first_msg = reversed_data[0]['messages'][0]['content']
    
    print(f"  Normal first message: {normal_first_msg[:50]}...")
    print(f"  Reversed first message: {reversed_first_msg[:50]}...")
    
    # They should be different if reversal worked
    assert normal_first_msg != reversed_first_msg, "Reversal should change order"
    
    print("✅ Test 6 PASSED\n")
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("ChatLog Converter - Comprehensive Test Suite")
    print("="*70)
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    
    tests = [
        ("Parse and Auto-Detect", test_parse_and_detect),
        ("Convert to JSON (Finetune)", test_convert_finetune_mode),
        ("Convert to JSON (Context)", test_convert_context_mode),
        ("Extract Specific Agent", test_extract_agent),
        ("Classify by Agent", test_classify_agents),
        ("Reverse Message Order", test_reverse_order),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            failed += 1
            errors.append((test_name, str(e)))
            print(f"❌ Test FAILED: {test_name}")
            print(f"   Error: {e}\n")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if errors:
        print("\nFailed tests:")
        for test_name, error in errors:
            print(f"  - {test_name}: {error}")
    
    print("\n" + "="*70)
    if failed == 0:
        print("All tests PASSED!")
    else:
        print(f"{failed} test(s) FAILED")
    print("="*70 + "\n")
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
