#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import os
import re
import sys
import uuid

import requests

# 中文输出兜底：部分 Windows 控制台默认 GBK，直接 print 中文会抛 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


# ==========================================================
# 基础配置（每个 Skill 修改）
# ==========================================================

BASE_URL = "https://ai.stock.pingan.com" 

SKILL_PREFIX = "restapi/hotstock"

API_PATH = "isspContentService/hotStock/list"   # 平安热股榜单列表

SKILL_ID = "hot-stock"

TIMEOUT = 60

API_KEY = os.getenv("PINGAN_SKILL_APIKEY", "").strip()

REQUEST_ID = str(uuid.uuid4())


# ==========================================================
# 业务枚举与约束
# ==========================================================

# 榜单类型
MODULE_CODES = {
    "hot_stock":  "热搜榜",    # 平安证券用户都在搜索的标的榜单
    "hot_select": "加自选榜",  # 平安证券用户都在加自选的标的榜单
    "hot_watch":  "浏览榜",    # 平安证券用户都在看的标的榜单
    "hot_surge":  "飙升榜",    # 关注度飙升最快的标的榜单
}

# 二级 tab 类型
TYPE_CODES = {
    "aStock":  "A股",
    "etf":     "ETF",
    "block":   "板块概念",
    "hkStock": "港股",
    "bond":    "可转债",
}

# 时间区间
TIME_RANGES = {
    1: "1小时",
    2: "24小时",
}

MAX_SIZE = 100

# 默认值（不传时脚本主动补上，不依赖网关默认行为）
DEFAULT_TIME_RANGE = 2   # 24h
DEFAULT_PAGE = 1         # 固定取第 1 页，不对外暴露
DEFAULT_SIZE = 10        # 每页 10 条


# ==========================================================
# 返回结果精简
# ==========================================================

# 这些字段对回答无用，统一从返回结果里剔除，避免占用上下文
DROP_FIELDS = {
    "tagList",     # 标签汇总，噪声大
    "page",        # 固定第 1 页
    "size",        # 等于入参
    "total",       # 用不到
    "calcDate",    
    "cnt",         
    "firmVolume",  
    "fusion",      
    "avgPrice",
    "news"    
}

DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _date_only(value):
    """把 '2026-09-02 09:00:00' 截成 '2026-09-02'，非日期原样返回。"""

    if isinstance(value, str):
        match = DATE_PATTERN.match(value.strip())
        if match:
            return match.group(1)

    return value


def slim(node):
    """递归剔除无用字段，并把 updateTime 截断到日期。"""

    if isinstance(node, dict):
        result = {}
        for key, value in node.items():
            if key in DROP_FIELDS:
                continue
            if key == "updateTime":
                result[key] = _date_only(value)
                continue
            result[key] = slim(value)
        return result

    if isinstance(node, list):
        return [slim(item) for item in node]

    return node


# ==========================================================
# HTTP 请求
# ==========================================================

def call_api(payload: dict):

    if not API_KEY:
        raise RuntimeError("缺少环境变量 PINGAN_SKILL_APIKEY")

    url = f"{BASE_URL}/{SKILL_PREFIX}/{API_PATH}"

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
        "X-Skill-ID": SKILL_ID,
        "X-Request-ID": REQUEST_ID
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=TIMEOUT,
    )

    # ----------------------------
    # HTTP 错误处理
    # ----------------------------

    if response.status_code == 401:
        raise RuntimeError("缺少 API Key。")

    if response.status_code == 403:
        raise RuntimeError("API Key 无效或没有权限。")

    if response.status_code == 429:

        body = response.json()

        error_code = body.get("error_code")

        if error_code == "RATE_LIMIT_EXCEEDED":
            raise RuntimeError("接口调用频率超限。")

        if error_code == "DAILY_QUOTA_EXCEEDED":
            raise RuntimeError("今日调用次数已达上限。")

        raise RuntimeError("请求超过限制。")

    if response.status_code == 503:
        raise RuntimeError("服务暂时不可用，请稍后重试。")

    response.raise_for_status()

    body = response.json()

    # 网关层错误码
    if body.get("code") not in (0, None):
        raise RuntimeError(
            body.get("error_message", "接口调用失败。")
        )

    data = body.get("data", body)

    # 业务层错误码：status 1-成功，非1-失败
    if isinstance(data, dict) and "status" in data and data.get("status") != 1:
        raise RuntimeError(
            data.get("errmsg") or "榜单接口返回失败。"
        )

    if isinstance(data, dict) and "results" in data:
        data = data.get("results") or {}

    return slim(data)


# ==========================================================
# CLI
# ==========================================================

class JSONArgumentParser(argparse.ArgumentParser):
    """
    命令行解析出错提示，统一处理错误信息
    """
    def error(self, message):
        raise RuntimeError(message)


def _compact(payload: dict) -> dict:
    """去掉值为 None 的字段后返回，供 build_payload 组装请求体使用。"""
    return {k: v for k, v in payload.items() if v is not None}


def build_parser() -> argparse.ArgumentParser:

    parser = JSONArgumentParser(description="平安证券热股风向标 Skill —— 热股榜单列表")

    parser.add_argument(
        "--module_code", required=True, choices=sorted(MODULE_CODES),
        help="榜单类型：hot_stock 热搜榜（用户都在搜的标的）、"
             "hot_select 加自选榜（用户都在加自选的标的）、"
             "hot_watch 浏览榜（用户都在看的标的）、"
             "hot_surge 飙升榜（关注度飙升最快的标的）",
    )
    parser.add_argument(
        "--type_code", required=True, choices=sorted(TYPE_CODES),
        help="二级tab类型：aStock A股、etf ETF、block 板块概念、"
             "hkStock 港股、bond 可转债",
    )
    parser.add_argument(
        "--time_range", type=int, default=DEFAULT_TIME_RANGE,
        choices=sorted(TIME_RANGES),
        help=f"时间区间：1=1h、2=24h，不传默认 {DEFAULT_TIME_RANGE}=24h",
    )
    parser.add_argument(
        "--size", type=int, default=DEFAULT_SIZE,
        help=f"返回条数，不传默认 {DEFAULT_SIZE}，最大 {MAX_SIZE}",
    )

    return parser


def validate(args: argparse.Namespace) -> None:
    """本地参数校验，不合法直接拦截，不发起网络请求。"""

    if not (1 <= args.size <= MAX_SIZE):
        raise RuntimeError(f"参数 size 取值范围为 1～{MAX_SIZE}")


def build_payload(args: argparse.Namespace) -> dict:

    return _compact({
        "moduleCode": args.module_code,
        "typeCode": args.type_code,
        "timeRange": args.time_range,
        "page": DEFAULT_PAGE,
        "size": args.size,
    })


def main():

    parser = build_parser()

    args = parser.parse_args()

    validate(args)

    payload = build_payload(args)

    # 调用接口
    result = call_api(payload)

    print(
        json.dumps(
            result,
            ensure_ascii=False,
        )
    )


# ==========================================================
# 主程序入口
# ==========================================================

if __name__ == "__main__":

    try:
        main()
    except Exception as e:
        # 错误处理
        print(
            json.dumps(
                {
                    "error": str(e)
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )

        sys.exit(1)
