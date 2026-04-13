#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解压漏洞文件夹中的 CNVD/CNNVD zip 文件，并清理嵌套目录"""

import zipfile
import os
import sys
import shutil

def cleanup_extracted_dir(target_dir: str) -> str:
    """清理解压后的目录：
    1. 删除 __MACOSX 目录
    2. 如果有嵌套目录，将内容移到外层

    Args:
        target_dir: 解压后的目录路径

    Returns:
        docx 文件路径（如果找到）
    """
    # 删除 __MACOSX 目录
    macosx_dir = os.path.join(target_dir, "__MACOSX")
    if os.path.isdir(macosx_dir):
        shutil.rmtree(macosx_dir)
        print(f"   删除 __MACOSX 目录")

    # 查找 docx 文件
    docx_files = []
    for root, dirs, files in os.walk(target_dir):
        # 跳过 __MACOSX
        dirs[:] = [d for d in dirs if d != "__MACOSX"]
        for f in files:
            if f.endswith('.docx') and not f.startswith('.'):
                docx_files.append(os.path.join(root, f))

    # 如果 docx 在子目录中，移动到外层
    if docx_files:
        docx_path = docx_files[0]
        docx_dir = os.path.dirname(docx_path)

        if docx_dir != target_dir:
            # docx 在嵌套目录中，需要移动
            print(f"   检测到嵌套目录，移动文件...")
            for item in os.listdir(docx_dir):
                if item.startswith('.'):
                    continue
                src = os.path.join(docx_dir, item)
                dst = os.path.join(target_dir, item)
                if os.path.exists(dst):
                    continue
                shutil.move(src, dst)

            # 删除空的内层目录
            shutil.rmtree(docx_dir)
            print(f"   清理嵌套目录: {os.path.basename(docx_dir)}")

            # 更新 docx 路径
            docx_path = os.path.join(target_dir, os.path.basename(docx_files[0]))

        return docx_path

    return None

def unzip_vuln_folder(folder_path: str) -> dict:
    """解压漏洞文件夹中的 CNVD/CNNVD zip 文件

    Args:
        folder_path: 漏洞文件夹路径（包含 CNVD-xxx.zip 和 CNNVD-xxx.zip）

    Returns:
        解压结果: {"cnvd": {"success": bool, "path": str, "docx": str}, "cnnvd": {...}}
    """
    result = {"cnvd": {"success": False, "path": None, "docx": None},
              "cnnvd": {"success": False, "path": None, "docx": None}}

    if not os.path.isdir(folder_path):
        print(f"❌ 目录不存在: {folder_path}")
        return result

    # 查找 zip 文件
    zip_files = [f for f in os.listdir(folder_path) if f.endswith('.zip')]

    for zip_file in zip_files:
        zip_path = os.path.join(folder_path, zip_file)
        platform = None

        # 判断平台
        if zip_file.startswith('CNVD-'):
            platform = 'cnvd'
        elif zip_file.startswith('CNNVD-'):
            platform = 'cnnvd'
        else:
            print(f"⚠️  跳过非平台 zip: {zip_file}")
            continue

        # 解压目标目录：同名的无 .zip 后缀文件夹
        target_dir = os.path.join(folder_path, zip_file[:-4])

        # 如果目标目录已存在，检查是否有 docx
        if os.path.isdir(target_dir):
            # 查找 docx 文件
            docx_path = cleanup_extracted_dir(target_dir)
            if docx_path:
                print(f"   ✓ 已有 docx: {os.path.basename(docx_path)}")
                result[platform] = {"success": True, "path": target_dir, "docx": docx_path}
                continue

        # 解压
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(target_dir)
            print(f"✓ 解压完成: {zip_file}")

            # 清理嵌套目录
            docx_path = cleanup_extracted_dir(target_dir)

            result[platform] = {
                "success": True,
                "path": target_dir,
                "docx": docx_path
            }
        except Exception as e:
            print(f"❌ 解压失败: {zip_file} - {e}")
            result[platform] = {"success": False, "path": None, "docx": None, "error": str(e)}

    return result

def unzip_batch(parent_dir: str) -> list:
    """批量解压多个漏洞文件夹

    Args:
        parent_dir: 包含多个漏洞文件夹的父目录

    Returns:
        所有漏洞的解压结果列表
    """
    results = []

    if not os.path.isdir(parent_dir):
        print(f"❌ 目录不存在: {parent_dir}")
        return results

    # 查找所有漏洞文件夹（DAS-T 开头）
    vuln_folders = [f for f in os.listdir(parent_dir)
                    if f.startswith('DAS-T') and os.path.isdir(os.path.join(parent_dir, f))]

    print(f"发现 {len(vuln_folders)} 个漏洞文件夹")

    for folder in sorted(vuln_folders):
        folder_path = os.path.join(parent_dir, folder)
        print(f"\n处理: {folder}")
        result = unzip_vuln_folder(folder_path)
        results.append({
            "das_id": '-'.join(folder.split('-')[:2]),
            "folder": folder,
            "result": result
        })

    # 统计
    cnvd_count = sum(1 for r in results if r["result"]["cnvd"]["success"])
    cnnvd_count = sum(1 for r in results if r["result"]["cnnvd"]["success"])
    print(f"\n统计: CNVD 解压 {cnvd_count}/{len(results)}, CNNVD 解压 {cnnvd_count}/{len(results)}")

    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python unzip_vuln.py <folder_or_parent_dir>")
        print("  单个漏洞: python unzip_vuln.py DAS-T105916-xxx")
        print("  批量处理: python unzip_vuln.py /path/to/date")
        sys.exit(1)

    target = sys.argv[1]

    # 判断是单个漏洞文件夹还是父目录
    if os.path.basename(target).startswith('DAS-T'):
        # 单个漏洞
        unzip_vuln_folder(target)
    else:
        # 父目录，批量处理
        unzip_batch(target)