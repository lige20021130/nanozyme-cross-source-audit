# -*- coding: utf-8 -*-
"""`--ask` 问答 agent 主循环（需 API，默认关闭）。

## 为什么不用原生 function-calling

`api_client.APIClient._build_payload` **强制** `response_format={"type":"json_object"}`
且没有 tools 参数位，接入原生 function-calling 要改底层客户端、牵动整条抽取流水线。
因此这里采用**文本 JSON 行动协议**：模型每轮只回一个 JSON 对象，本地解析后分派工具，
把结果作为下一轮观测回灌。代价是每轮多一次解析，收益是 provider 无关、零侵入。

## 行动协议

每轮必须只输出一个 json 对象，两种形态二选一：

    {"thought": "<简短推理>", "action": {"tool": "<工具名>", "args": {}}, "final": null}

    {"thought": "<简短推理>", "action": null, "final": "<给用户的最终回答，markdown>"}

`final` 非空即结束。解析层对三种常见写法做容错：
`{"action": {...}}` / `{"tool": ..., "args": ...}` / `{"action": "<工具名>"}`。

## 护栏（防止 agent 空转）

| 护栏 | 默认 | 行为 |
|---|---|---|
| 最大步数 | 8 | 达上限后强制要求用已观测信息收尾 |
| 观测截断 | 6000 字符 | 防单条工具结果撑爆上下文 |
| 重复调用 | 同 (tool,args) | 提示已执行过，要求直接作答 |
| 解析重试 | 2 次 | 解析失败回灌纠错消息，仍失败则中止并返回 trace |

## 零 API 可测性

`run()` 接受可注入的 `chat_fn(messages) -> str | None`，单测用假 LLM 即可跑通整条循环，
不消耗任何 token。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from kg.tools import TOOL_NAMES, WikiIndex, dispatch, tool_prompt

DEFAULT_MAX_STEPS = 8
MAX_OBS_CHARS = 6000
MAX_PARSE_RETRIES = 2

SYSTEM_PROMPT = """\
你是纳米酶催化动力学知识库的问答助手。你只能通过工具访问数据，禁止凭记忆编造数值。

## 铁律
1. 每一个数字必须来自工具返回的记录，并在回答中标注材料、条件与 DOI（或测定页链接）。
2. 工具没查到就说「未查到」，**禁止估算、禁止外推、禁止用领域常识补数**。
3. 数值问题优先用 `query_structured`；"随温度/pH 怎么变"用 `plot_gradient`；
   "和 X 相关的有哪些"用 `graph_neighbors`。
4. 区分 `provenance`：`extraction` 是系统抽取、`human` 是人工标注，回答时如实说明来源。
5. `predict` 是**推断类**工具（非检索），输出带证据分级 stage：
   - `retrieval`：引用文献实测值 + DOI + 组内冲突范围；
   - `extrapolation`：必须注明「模型外推」+ 预测区间 + 模型卡（DOI 分组 OOF R²），
     外推值不得与文献实测值混同；
   - `refusal`：如实转述「训练支撑不足，仅量级区间」，不得给出具体点值。
   当 `query_structured` 对目标组合无命中时，**必须**调用一次 `predict` 给量级参考：
   材料名与 pH/温度齐备 → 按 predict 返回的外推/拒答如实转述；
   材料名或条件缺失 → predict 无法运行，如实说明缺什么，禁止给任何数字。

## 可用工具（JSON Schema）
{schemas}

## 输出格式
每轮只输出一个 json 对象，不要输出任何解释性文字、不要 markdown 代码块围栏：

调用工具： {{"thought": "<简短推理>", "action": {{"tool": "<工具名>", "args": {{...}}}}, "final": null}}
给出结论： {{"thought": "<简短推理>", "action": null, "final": "<最终回答，markdown>"}}

`final` 非空即结束。用完工具仍缺数据时，也要用 `final` 如实说明缺口所在。
"""

# 解析失败 / 重复调用 / 步数耗尽时回灌给模型的纠错消息
_ERR_MSG = {
    "parse": "上一条回复不是合法的 json 对象，或缺少 tool/final 字段。请严格只输出一个 json 对象。",
    "unknown": "工具名不在可用列表 {tools} 中。请改用列表内的工具。",
    "repeat": "该调用与第 {step} 步完全相同，结果已在上面。请直接基于已有观测用 final 作答。",
    "last": "已达最大步数。请立即用 final 给出结论；数据不足则如实说明，不要再调用工具。",
}


# ------------------------------------------------------------------ 解析

def _strip_fences(text: str) -> str:
    """去掉 ```json ... ``` 围栏（模型偶尔不遵守"无围栏"约束）。"""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[: -3]
    return t.strip()


def _loads(text: str) -> dict | None:
    """容错 JSON 解析：去围栏 → 直解 → 截取最外层花括号再解。"""
    t = _strip_fences(text)
    if not t:
        return None
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        obj = json.loads(t[i: j + 1])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def parse_reply(text: str) -> tuple[dict | None, str | None, str | None]:
    """解析模型回复 → (action, final, error)。

    action 归一化 dict：`{"tool": str, "args": dict}`。三者均可为 None；
    error 非空时调用方应把 `_ERR_MSG` 回灌给模型重试。
    """
    obj = _loads(text)
    if obj is None:
        return None, None, "parse"

    final = obj.get("final")
    if isinstance(final, str) and final.strip():
        return None, final.strip(), None

    raw = obj.get("action")
    if raw is None:
        # 兼容顶层 tool / args 写法
        if isinstance(obj.get("tool"), str):
            raw = {"tool": obj["tool"], "args": obj.get("args") or {}}
        else:
            return None, None, "parse"

    if isinstance(raw, str):                       # {"action": "tool_name", "args": {...}}
        tool = raw
        args = obj.get("args") if isinstance(obj.get("args"), dict) else {}
    elif isinstance(raw, dict):                    # {"action": {...}}
        tool, args = raw.get("tool"), raw.get("args") or {}
    else:
        return None, None, "parse"

    if not isinstance(tool, str) or not tool.strip():
        return None, None, "parse"
    if not isinstance(args, dict):
        args = {}
    return {"tool": tool.strip(), "args": args}, None, None


def _observation(result: Any, max_chars: int = MAX_OBS_CHARS) -> str:
    """把工具结果序列化成观测文本，超长截断（防撑爆上下文）。"""
    try:
        text = json.dumps(result, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(result)
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n…[已截断，原始长度 {len(text)} 字符]"
    return text


def _key_of(action: dict) -> str:
    return json.dumps([action.get("tool"), action.get("args")],
                      ensure_ascii=False, sort_keys=True)


# ------------------------------------------------------------------ 主循环

def run(question: str, index: WikiIndex, chat_fn: Callable[[list[dict]], str | None],
        max_steps: int = DEFAULT_MAX_STEPS, verbose: bool = False) -> dict:
    """跑一轮问答。返回 `{"question","answer","steps","tool_calls","trace","ok"}`。

    `chat_fn` 注入点：签名 `(messages) -> str | None`，返回 None 视为调用失败。
    """
    system = SYSTEM_PROMPT.replace("{schemas}", tool_prompt())
    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"问题：{question}"},
    ]
    trace: list[dict] = []
    seen: dict[str, int] = {}
    answer: str | None = None

    for step in range(1, max_steps + 1):
        # 步数耗尽：强制收尾，不再给工具
        if step == max_steps:
            messages.append({"role": "user", "content": _ERR_MSG["last"]})

        reply = None
        for attempt in range(MAX_PARSE_RETRIES + 1):
            reply = chat_fn(messages)
            if reply is None:
                break
            action, final, err = parse_reply(reply)
            if final:
                answer = final
                break
            if not err:
                break
            if attempt < MAX_PARSE_RETRIES:
                messages += [{"role": "assistant", "content": reply},
                             {"role": "user", "content": _ERR_MSG["parse"]}]
        if reply is None:
            trace.append({"step": step, "error": "LLM 调用失败（返回 None）"})
            if verbose:
                print(f"  [ask] 第 {step} 步：LLM 调用失败，中止")
            break
        if answer:
            break

        action, final, err = parse_reply(reply)
        if final:
            answer = final
            break
        if err == "parse":
            trace.append({"step": step, "error": f"连续 {MAX_PARSE_RETRIES + 1} 次解析失败"})
            if verbose:
                print(f"  [ask] 第 {step} 步：解析失败，中止")
            break

        assert action is not None
        tool, args = action["tool"], action["args"]

        if tool not in TOOL_NAMES:
            obs = _ERR_MSG["unknown"].replace("{tools}", ", ".join(TOOL_NAMES))
            trace.append({"step": step, "tool": tool, "args": args,
                          "executed": False, "error": "未知工具"})
        else:
            k = _key_of(action)
            if k in seen:
                obs = _ERR_MSG["repeat"].replace("{step}", str(seen[k]))
                trace.append({"step": step, "tool": tool, "args": args,
                              "executed": False, "error": f"与第 {seen[k]} 步重复"})
            else:
                seen[k] = step
                result = dispatch(index, tool, args)
                obs = _observation(result)
                stage = result.get("stage") if isinstance(result, dict) else None
                trace.append({"step": step, "tool": tool, "args": args,
                              "executed": True, "obs_chars": len(obs), "stage": stage,
                              "error": result.get("error") if isinstance(result, dict) else None})
                if verbose:
                    print(f"  [ask] 第 {step} 步：{tool}({len(args)} 参数) → {len(obs)} 字符")

        messages += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": f"OBSERVATION（工具返回）:\n{obs}"}]

    # 只统计真正执行的调用：未知工具与重复调用被护栏拦下，不算数
    tool_calls = sum(1 for t in trace if t.get("executed"))
    return {"question": question, "answer": answer or "", "steps": len(trace),
            "tool_calls": tool_calls, "trace": trace, "ok": bool(answer)}


def ask(records_dir: str | Path, vault_dir: str | Path, question: str,
        provider: str | None = None, max_steps: int = DEFAULT_MAX_STEPS,
        temperature: float = 0.2, max_tokens: int = 2400,
        verbose: bool = True) -> dict:
    """端到端入口：建索引 → 跑循环。无 API 时返回 `ok=False` 且不抛异常。"""
    from kg import llm

    if not llm.available(verbose=verbose):
        return {"question": question, "answer": "", "steps": 0, "tool_calls": 0,
                "trace": [], "ok": False, "error": "LLM 不可用（config.yaml 缺失或无 provider）"}

    index = WikiIndex(records_dir, vault_dir)

    def chat_fn(messages: list[dict]) -> str | None:
        return llm.chat_messages(messages, preferred=provider,
                                 temperature=temperature, max_tokens=max_tokens,
                                 verbose=verbose)

    return run(question, index, chat_fn, max_steps=max_steps, verbose=verbose)


def save_page(index: WikiIndex, result: dict, title: str | None = None) -> dict:
    """把问答结论写入 `analysis/`（再吸收，带 inferred 标记）。"""
    head = title or result.get("question") or "问答"
    lines = [
        f"**问题**：{result.get('question', '')}",
        "",
        result.get("answer", ""),
        "",
        "## 工具调用轨迹",
        "",
        "| 步 | 工具 | 参数 | 观测字符 | 备注 |",
        "|---|---|---|---|---|",
    ]
    for t in result.get("trace", []):
        args = json.dumps(t.get("args") or {}, ensure_ascii=False)
        lines.append(f"| {t.get('step')} | {t.get('tool') or '—'} | {args[:80]} | "
                     f"{t.get('obs_chars', '—')} | {t.get('error') or ''} |")
    return index.write_analysis_page(f"问答_{head}"[:80], "\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser(description="纳米酶知识库问答 agent（需 API，默认关闭）")
    ap.add_argument("--records", required=True, help="抽取产出目录")
    ap.add_argument("--vault", required=True, help="Obsidian vault 目录")
    ap.add_argument("--question", required=True, help="要问的问题")
    ap.add_argument("--provider", default=None, help="provider 配置键")
    ap.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    ap.add_argument("--save-page", action="store_true",
                    help="把结论写入 vault/analysis/（带 inferred 标记）")
    args = ap.parse_args()

    result = ask(args.records, args.vault, args.question,
                 provider=args.provider, max_steps=args.max_steps)
    if not result.get("ok"):
        print(f"未获得回答：{result.get('error') or '循环中止'}")
        for t in result.get("trace", []):
            print(f"  步 {t.get('step')}: {t.get('error') or t.get('tool')}")
        sys.exit(1)

    print(result["answer"])
    print(f"\n---\n步数 {result['steps']} / 工具调用 {result['tool_calls']} 次")

    if args.save_page:
        index = WikiIndex(args.records, args.vault)
        print(f"已写入：{save_page(index, result)}")


if __name__ == "__main__":
    main()
