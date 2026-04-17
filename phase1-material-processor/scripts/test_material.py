#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试材料整理功能的辅助脚本"""

import sys
import os
import argparse

# 添加项目根目录到 path
sys.path.insert(0, '/Users/yao/LLM/vulns')

from app.services.material_service import MaterialService


def test_single(data_dir: str, das_id: str, submitter: str = None):
    """测试单个漏洞处理"""
    service = MaterialService(data_dir)
    result = service.process_single(das_id, submitter)

    print(f"\n{'='*60}")
    print(f"DAS-ID: {das_id}")
    print(f"{'='*60}")

    if result["cnvd"]["path"]:
        print(f"CNVD: {'✓' if result['cnvd']['modified'] else '○'} {result['cnvd']['message']}")
        print(f"  路径: {result['cnvd']['path']}")
    else:
        print(f"CNVD: ✗ {result['cnvd']['message']}")

    if result["cnnvd"]["path"]:
        print(f"CNNVD: {'✓' if result['cnnvd']['modified'] else '○'} {result['cnnvd']['message']}")
        print(f"  路径: {result['cnnvd']['path']}")
    else:
        print(f"CNNVD: ✗ {result['cnnvd']['message']}")

    print(f"\n总体: {'成功' if result['success'] else '失败'}")
    return result


def test_batch(data_dir: str):
    """测试批量处理"""
    service = MaterialService(data_dir)
    results = service.process_all()

    print(f"\n处理了 {len(results)} 个漏洞:\n")

    success_count = 0
    for r in results:
        cnvd_ok = "✓" if r["cnvd"]["modified"] else "○"
        cnnvd_ok = "✓" if r["cnnvd"]["modified"] else "○"
        print(f"  {r['das_id']}: CNVD={cnvd_ok} CNNVD={cnnvd_ok}")
        if r["success"]:
            success_count += 1

    print(f"\n成功: {success_count}/{len(results)}")
    return results


def list_vulns(data_dir: str):
    """列出所有漏洞状态"""
    service = MaterialService(data_dir)
    vulns = service.list_vulns()

    print(f"\n发现 {len(vulns)} 个漏洞:\n")
    print(f"{'DAS-ID':<15} {'CNVD':<8} {'CNNVD':<8} {'提交人':<10}")
    print("-" * 50)

    for v in vulns:
        cnvd = "✓" if v["cnvd_processed"] else ("○" if v["has_cnvd"] else "-")
        cnnvd = "✓" if v["cnnvd_processed"] else ("○" if v["has_cnnvd"] else "-")
        print(f"{v['das_id']:<15} {cnvd:<8} {cnnvd:<8} {v['submitter']:<10}")

    return vulns


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="测试材料整理功能")
    parser.add_argument("--dir", "-d", required=True, help="数据目录路径")
    parser.add_argument("action", nargs="?", default=None, help="操作: batch, list, 或 DAS-ID")
    parser.add_argument("submitter", nargs="?", help="提交人员 (可选)")

    args = parser.parse_args()

    if args.action == "batch":
        test_batch(args.dir)
    elif args.action == "list":
        list_vulns(args.dir)
    elif args.action:
        # 当作 DAS-ID 处理
        test_single(args.dir, args.action, args.submitter)
    else:
        # 默认列出状态
        list_vulns(args.dir)