# -*- coding: utf-8 -*-
"""LLM 调用的统一封装（唯一入口，含优雅降级）。

## 为什么单独抽一层

`api_client.APIClient` 的接口有三处极易写错：

1. **是 async** —— 必须用 `asyncio.run` 包一层同步入口；
2. **第一个参数是 provider 的**配置键**（`text_llm` / `vision_llm` / `integrator_llm`），
   不是模型名、也不是 client 对象；
3. **入口是 messages 列表**，不是单个 prompt 字符串。

kg/ 下的 taxonomy、hub_summary、ask 都要调 LLM，重复三遍必然写歪，
因此收敛到本模块。**所有失败一律返回 `None`，绝不抛异常** ——
这样任何 LLM 能力缺失都只是"少了推断块"，不会污染事实层或中断编译。
"""
from __future__ import annotations

import asyncio
from typing import Any

# provider 优先级：推理/归纳类任务优先用 integrator_llm（与抽取系统选型一致）
_PREFERRED_ORDER = ("integrator_llm", "text_llm")


def load_cfg() -> Any | None:
    """读 config.yaml。失败返回 None。"""
    try:
        from config_loader import load_config
        return load_config()
    except Exception:
        return None


def pick_provider(cfg: Any, preferred: str | None = None) -> str | None:
    """选一个可用的 provider 配置键。"""
    providers = getattr(cfg, "providers", {}) or {}
    if not providers:
        return None
    if preferred and preferred in providers:
        return preferred
    for name in _PREFERRED_ORDER:
        if name in providers:
            return name
    return next(iter(providers), None)


async def _chat_async(cfg: Any, provider: str, messages: list[dict],
                      temperature: float, max_tokens: int) -> str:
    from api_client import APIClient

    async with APIClient(cfg.providers, cfg.rate_limit) as client:
        res = await client.chat_text(provider, messages,
                                     temperature=temperature, max_tokens=max_tokens)
    text = (getattr(res, "content", "") or "").strip()
    if getattr(res, "truncated", False):
        text += "\n> ⚠️ 响应被截断，内容可能不完整。"
    return text


def chat_messages(messages: list[dict], preferred: str | None = None,
                  temperature: float = 0.2, max_tokens: int = 1200,
                  verbose: bool = False) -> str | None:
    """多轮对话入口（messages 由调用方自行组装）。

    与 `chat()` 的区别只在于消息列表的构造权：**多轮工具调用必须复用同一
    messages 列表逐轮追加**，因此 `kg/ask.py` 用本函数；而 `chat()` 只是
    本函数在「system + 单条 user」下的便捷包装。

    **任何失败都返回 None，不抛异常。**
    """
    cfg = load_cfg()
    if cfg is None:
        if verbose:
            print("  [llm] 读取 config.yaml 失败，跳过（返回 None）")
        return None
    provider = pick_provider(cfg, preferred)
    if not provider:
        if verbose:
            print("  [llm] config.yaml 中无可用 provider，跳过")
        return None
    try:
        return asyncio.run(_chat_async(cfg, provider, messages, temperature, max_tokens))
    except Exception as e:
        if verbose:
            print(f"  [llm] 调用失败（{provider}）：{e}")
        return None


def chat(system: str, user: str, preferred: str | None = None,
         temperature: float = 0.2, max_tokens: int = 1200,
         verbose: bool = False) -> str | None:
    """同步单轮聊天入口。**任何失败都返回 None，不抛异常。**

    返回 None 的语义是「本次推断不可用」，调用方应静默跳过该推断块。
    """
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    return chat_messages(messages, preferred=preferred, temperature=temperature,
                         max_tokens=max_tokens, verbose=verbose)


def available(verbose: bool = False) -> bool:
    """LLM 能力是否可用（供 CLI 提前判断，避免白跑一轮）。"""
    cfg = load_cfg()
    ok = cfg is not None and pick_provider(cfg) is not None
    if verbose and not ok:
        print("  [llm] 不可用：config.yaml 缺失或无 provider")
    return ok
