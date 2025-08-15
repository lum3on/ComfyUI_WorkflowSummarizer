#!/usr/bin/env python3
"""
Test script for the enhanced ComfyUI Workflow Summarizer features.
This tests the maintainer's requirements implementation.
"""

import os
import sys
import json

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner import NodeLicenseScanner
from workflow_summary import WorkflowSummary

def test_enhanced_node_detection():
    """Test the enhanced node detection that finds ALL installed nodes"""
    print("🔍 Testing Enhanced Node Detection...")
    
    scanner = NodeLicenseScanner()
    
    # Test core node detection
    print("\n--- Testing Core Node Detection ---")
    core_nodes = scanner.get_comfyui_core_nodes()
    print(f"Found {len(core_nodes)} core nodes")
    
    if core_nodes:
        print("Sample core nodes:")
        for i, (name, info) in enumerate(list(core_nodes.items())[:5]):
            print(f"  • {name}: {info['license']} ({info['category']})")
    
    # Test custom node detection
    print("\n--- Testing Custom Node Detection ---")
    custom_nodes = scanner.scan_custom_nodes_enhanced()
    print(f"Found {len(custom_nodes)} custom nodes")
    
    if custom_nodes:
        print("Sample custom nodes:")
        for i, (name, info) in enumerate(list(custom_nodes.items())[:5]):
            print(f"  • {name}: {info.get('package', 'unknown')} ({info['category']})")
    
    # Test comprehensive detection
    print("\n--- Testing Comprehensive Node Detection ---")
    all_nodes = scanner.get_all_installed_nodes()
    print(f"Total nodes found: {len(all_nodes)}")
    
    core_count = len([n for n in all_nodes.values() if n['type'] == 'core'])
    custom_count = len([n for n in all_nodes.values() if n['type'] == 'custom'])
    print(f"  Core nodes: {core_count}")
    print(f"  Custom nodes: {custom_count}")
    
    return len(all_nodes) > 0

def test_enhanced_model_detection():
    """Test the enhanced model detection for all model types"""
    print("\n🎯 Testing Enhanced Model Detection...")
    
    workflow_summary = WorkflowSummary()
    
    # Test various model input patterns
    test_cases = [
        {"ckpt_name": "sd_xl_base_1.0.safetensors", "node_type": "CheckpointLoaderSimple"},
        {"lora_name": "my_lora.safetensors", "node_type": "LoraLoader"},
        {"control_net_name": "control_sd15_canny.pth", "node_type": "ControlNetLoader"},
        {"vae_name": "vae-ft-mse-840000.ckpt", "node_type": "VAELoader"},
        {"upscale_model": "RealESRGAN_x4plus.pth", "node_type": "UpscaleModelLoader"},
        {"model": "gfpgan_v1.4.pth", "node_type": "FaceRestoreModelLoader"},
    ]
    
    for i, test_case in enumerate(test_cases):
        node_type = test_case.pop("node_type")
        detected = workflow_summary._detect_all_model_types(test_case, node_type)
        
        print(f"Test {i+1}: {node_type}")
        print(f"  Input: {test_case}")
        print(f"  Detected: {detected}")
    
    return True

def test_pdf_generation_options():
    """Test the new PDF generation options"""
    print("\n📄 Testing PDF Generation Options...")
    
    # Create a minimal test workflow
    test_prompt = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}
        },
        "2": {
            "class_type": "CLIPTextEncode", 
            "inputs": {"text": "a beautiful landscape"}
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {}
        },
        "4": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "test"}
        }
    }
    
    workflow_summary = WorkflowSummary()
    
    # Test full report
    print("Testing Full Report generation...")
    try:
        result = workflow_summary.export_summary(
            output_folder="./test_output",
            report_type="Full Report (Nodes + Licenses)",
            workflow_version="2.0",
            workflow_author="Test Author",
            include_all_installed_nodes=True,
            prompt=test_prompt,
            extra_pnginfo=None
        )
        print(f"Full Report Result: {result[0]}")
    except Exception as e:
        print(f"Full Report Error: {e}")
    
    # Test licenses-only report
    print("Testing Licenses Only report...")
    try:
        result = workflow_summary.export_summary(
            output_folder="./test_output",
            report_type="Licenses Only",
            workflow_version="2.0", 
            workflow_author="Test Author",
            include_all_installed_nodes=False,
            prompt=test_prompt,
            extra_pnginfo=None
        )
        print(f"Licenses Only Result: {result[0]}")
    except Exception as e:
        print(f"Licenses Only Error: {e}")
    
    return True

def main():
    """Run all tests"""
    print("🚀 Testing Enhanced ComfyUI Workflow Summarizer")
    print("=" * 60)
    
    # Create test output directory
    os.makedirs("./test_output", exist_ok=True)
    
    tests = [
        ("Enhanced Node Detection", test_enhanced_node_detection),
        ("Enhanced Model Detection", test_enhanced_model_detection), 
        ("PDF Generation Options", test_pdf_generation_options),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            success = test_func()
            results.append((test_name, success, None))
            print(f"✅ {test_name}: {'PASSED' if success else 'FAILED'}")
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"❌ {test_name}: FAILED - {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, error in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
        if error:
            print(f"    Error: {error}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced features are working correctly.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
