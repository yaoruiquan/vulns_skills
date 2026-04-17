#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""加载 .env 配置文件"""

import os
from pathlib import Path
from typing import Optional


def get_skill_dir() -> Path:
    """获取 skill 目录路径"""
    return Path(__file__).parent.parent


def load_env() -> dict:
    """加载 .env 文件，返回配置字典"""
    skill_dir = get_skill_dir()
    env_file = skill_dir / ".env"

    config = {}
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    # 支持 ${HOME} 等环境变量展开
                    value = os.path.expandvars(value)
                    config[key.strip()] = value.strip()

    return config


# 预加载配置
_config = load_env()


def get(key: str, default: Optional[str] = None) -> Optional[str]:
    """获取配置值"""
    return _config.get(key, default)


def get_data_dir() -> str:
    """获取漏洞数据目录"""
    return get('VULNS_DATA_DIR', '/Users/yao/LLM/vulns/date')


def get_summary_path() -> str:
    """获取汇总表路径"""
    return get('SUMMARY_TABLE_PATH',
               '/Users/yao/Documents/网安- AI应用开发/监管上报/汇总表/漏洞汇总表.xlsx')


def get_company_name() -> str:
    """获取技术支持单位名称"""
    return get('COMPANY_NAME', '杭州安恒信息技术股份有限公司')


def get_default_phone() -> str:
    """获取默认联系电话"""
    return get('DEFAULT_CONTACT_PHONE', '15700082275')


def get_chrome_port() -> int:
    """获取 Chrome 调试端口"""
    return int(get('CHROME_DEBUG_PORT', '9333'))


def get_chrome_profile() -> str:
    """获取 Chrome profile 名称"""
    return get('CHROME_PROFILE_NAME', 'cnnvd-report')