# schema.py - 25 字段扁平 Pydantic 模型
"""纳米酶文献提取系统的唯一数据模型。输出即 List[FlatRecord]。"""
from __future__ import annotations

import contextvars
import re
from typing import ClassVar, Optional

from pydantic import BaseModel, Field, PrivateAttr, ValidationError, field_validator, model_validator

# 元素符号 → 原子序数（覆盖常见纳米酶金属）
_ATOMIC_NUM: dict[str, int] = {
    "Fe": 26, "Mn": 25, "Co": 27, "Au": 79, "Pt": 78, "Pd": 46,
    "Ag": 47, "Ce": 58, "Cu": 29, "Ni": 28, "Zn": 30, "Ti": 22,
    "V": 23, "Cr": 24, "Al": 13, "Mo": 42, "Ru": 44, "Rh": 45,
    "Ir": 77, "Os": 76, "Bi": 83, "La": 57, "Pr": 59, "Nd": 60,
}

# 科学计数法上标/Unicode 乘号 → e 记法（LLM 常输出 "1.664×10⁻⁷"，需先归一才能 float 解析）
_SUPERSCRIPT_TRANS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")


def _sci_to_e(s: str) -> str:
    """把 Unicode 科学计数法 '1.664×10⁻⁷' / '2.5·10⁶' 归一为 '1.664e-7' / '2.5e6'。

    仅匹配 '<数字> [×x·] 10<上标指数>' 形态，避免误伤 's⁻¹' 等单位的上下标。
    否则 '1.664×10⁻⁷ M·s⁻¹' 会被 _normalize_numeric 当作 '1.664' 丢失整个量级（§16.4 评审发现）。
    """

    def _repl(m: "re.Match") -> str:
        base = m.group(1)
        exp = m.group(2).translate(_SUPERSCRIPT_TRANS)
        return f"{base}e{exp}"

    return re.sub(r"(\d+(?:\.\d+)?)\s*[×x·]\s*10([⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)", _repl, s)


def _to_atomic_num(v) -> Optional[int]:
    """接受元素符号('Mn')/带括号('Co(27)')/数字字符串('27')/整数，统一转原子序数。"""
    if v is None or v == "" or v == " ":
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip()
    # 提取括号内数字：Co(27) -> 27
    m = re.search(r"\((\d+)\)", s)
    if m:
        return int(m.group(1))
    # 纯数字字符串
    if s.isdigit():
        return int(s)
    # 元素符号（首字母大写）
    sym = s[:1].upper() + s[1:2].lower()
    if sym in _ATOMIC_NUM:
        return _ATOMIC_NUM[sym]
    return None


def _to_ratio(v) -> Optional[float]:
    """比例容错：'Mn:Co=1:2'->33.33, '1:2'->33.33, '50%'->50.0, 数字->float。"""
    if v is None or v == "" or v == " ":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    try:
        return float(s)
    except ValueError:
        pass
    # 比例式 A:B 或 A:B:C -> 第一个数字 / 所有数字之和 * 100
    if ":" in s:
        nums = re.findall(r"\d+(?:\.\d+)?", s)
        if len(nums) >= 2:
            nums = [float(n) for n in nums]
            total = sum(nums)
            return round(nums[0] / total * 100, 2) if total else None
    if s.endswith("%"):
        try:
            return float(s[:-1])
        except ValueError:
            return None
    return None


def _to_valence(v) -> Optional[int]:
    """价态容错：'+3'->3, '3+'->3, '+2,+3'->3, 'Mn2+/Mn3+'->3。

    混合价态取**较高价态**（与 gold 标注习惯一致：Co3O4 Co2+/Co3+→3, Fe3O4 Fe2+/Fe3+→3）。
    """
    if v is None or v == "" or v == " ":
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip()
    if s.isdigit():
        return int(s)
    # 提取所有 ±数字，取最大值（混合价态取较高）
    nums = [int(m.group(1)) for m in re.finditer(r"[+-]?(\d+)", s)]
    if nums:
        return max(nums)
    return None


class FlatRecord(BaseModel):
    """单条纳米酶记录，严格 25 字段。缺失字段为 None，不臆造。"""

    # 标识字段（3）
    nanozyme: str = Field(..., description="材料名，保留原文表述")
    mimic_enzyme_activity: Optional[str] = Field(None, description="酶活性类型")
    doi: Optional[str] = Field(None, description="文献 DOI")

    # 非金属掺杂（5）：0/1，表示是否晶格掺杂。配体/蛋白/核酸/聚合物/本征阴离子不算掺杂
    doped_N: Optional[int] = Field(None, description="是否晶格掺杂 N（配体/蛋白/DNA/PVP 中的 N 不算）")
    doped_P: Optional[int] = Field(None, description="是否晶格掺杂 P（DNA/ATP/磷酸盐中的 P 不算）")
    doped_S: Optional[int] = Field(None, description="是否晶格掺杂 S（金属硫化物/SDS 中的 S 不算）")
    doped_B: Optional[int] = Field(None, description="是否晶格掺杂 B")
    doped_F: Optional[int] = Field(None, description="是否晶格掺杂 F")

    # 主金属（3）：按摩尔占比判定，含量最高者为主金属（2026-07-20 删除第二金属 3 字段）
    metal_ratio: Optional[float] = Field(None, description="主金属占比（单金属单一价态=100）")
    metal_type: Optional[int] = Field(None, description="主金属原子序数")
    metal_valence: Optional[int] = Field(None, description="主金属价态（混合价取最高；零价金属态 Au/Pt/Pd 填 0，禁止填 1/2/4）")

    # 物理特征（3）
    shape: Optional[str] = Field(None, description="形貌")
    size_nm: Optional[float] = Field(None, description="颗粒尺寸 nm")
    surface_modification: Optional[str] = Field(None, description="表面修饰")

    # 反应条件（4）
    dispersion_medium: Optional[str] = Field(None, description="分散介质，不含 pH")
    buffer_ph_value: Optional[float] = Field(None, description="缓冲液 pH")
    temperature_c: Optional[float] = Field(None, description="反应温度 ℃")
    substrate1: Optional[str] = Field(None, description="主底物")

    # 动力学参数（7 字段：substrate2 + Km/Vmax/Kcat/催化效率/归属底物/方法）
    substrate2: Optional[str] = Field(None, description="第二底物，单底物为 None")
    Km_mM: Optional[float] = Field(None, description="米氏常数 mM")
    Vmax_uM_s_minus1: Optional[float] = Field(None, description="最大反应速率 μM·s⁻¹")
    Kcat_s_minus1: Optional[float] = Field(None, description="转换数 s⁻¹")
    catalytic_efficiency_M_s_minus1: Optional[float] = Field(None, description="催化效率 M⁻¹·s⁻¹")
    # 2026-07-02 新增 2 字段：动力学归属底物与测定方法
    kinetic_substrate: Optional[str] = Field(None, description="该 Km/Vmax/Kcat 归属的底物名，如 H2O2/TMB/O2")
    kinetic_method: Optional[str] = Field(None, description="动力学测定方法，如 UV-vis/SERS，未知填 null")

    # 2026-07-17：代码层实验包绑定（P1-A 方案 C，不进 LLM prompt，不进输出 JSON）
    # 由 integrator_agent._bind_experiments_by_rules 在 _post_filter 前赋值
    # 用于检测 Km/Vmax 不对称丢失和跨条件拼值异常
    _experiment_id: Optional[str] = PrivateAttr(default=None)
    # 确定性单位层(§16.4): 在数值解析前捕获 6 字段的源单位字符串，供 integrator 换算。
    # LLM 转录 "数值 单位" 原文字符串（不换算），此处仅记录原文单位，不改动业务语义/字段。
    _raw_inputs: dict[str, str] = PrivateAttr(default_factory=dict)

    # 捕获用 ContextVar：before-validator 写入、after-validator 读出并写入 _raw_inputs。
    # 同一次同步校验内 before→field→after 共享上下文，故 ContextVar 可靠；线程局部，并发安全。
    # （Pydantic v2 的 model_validator(before) 返回含私有属性名的 dict 不会赋值给实例，故用此桥接。）
    _RAW_INPUTS_CTX: ClassVar[contextvars.ContextVar] = contextvars.ContextVar(
        "raw_inputs", default=None)

    @model_validator(mode="before")
    @classmethod
    def _capture_raw_inputs(cls, data):
        raw: dict[str, str] = {}
        if isinstance(data, dict):
            for f in ("Km_mM", "Vmax_uM_s_minus1", "Kcat_s_minus1",
                     "size_nm", "temperature_c"):
                v = data.get(f)
                if isinstance(v, str) and v.strip():
                    raw[f] = v.strip()
        cls._RAW_INPUTS_CTX.set(raw or None)
        return data

    @model_validator(mode="after")
    def _attach_raw_inputs(self):
        raw = self.__class__._RAW_INPUTS_CTX.get()
        if raw:
            self._raw_inputs = raw
        return self

    @field_validator("metal_type", mode="before")
    @classmethod
    def _normalize_metal_type(cls, v):
        return _to_atomic_num(v)

    @field_validator("metal_ratio", mode="before")
    @classmethod
    def _normalize_ratio(cls, v):
        return _to_ratio(v)

    @field_validator("metal_valence", mode="before")
    @classmethod
    def _normalize_valence(cls, v):
        return _to_valence(v)

    @field_validator("doped_N", "doped_P", "doped_S", "doped_B", "doped_F", mode="before")
    @classmethod
    def _normalize_doped(cls, v):
        """掺杂字段容错：'1'/'0'/1/0/'yes'/'no' -> 1/0，元素符号(N/P/S/B/F)->1，空值 None。"""
        if v is None or v == "" or v == " ":
            return None
        if isinstance(v, int):
            return v
        s = str(v).strip()
        # 元素符号表示"有该元素掺杂"（N/P/S/B/F 都可能被 LLM 用来表示掺杂）
        if s.upper() in ("N", "P", "S", "B", "F"):
            return 1
        sl = s.lower()
        if sl in ("1", "yes", "true", "y"):
            return 1
        if sl in ("0", "no", "false"):
            return 0
        try:
            return int(float(s))
        except ValueError:
            return None

    @field_validator("buffer_ph_value", "temperature_c", mode="before")
    @classmethod
    def _normalize_multi_float(cls, v):
        """多值容错：'4.5, 7.0'->4.5, 'pH 7.0'->7.0, 'room temperature'->25.0。"""
        if v is None or v == "" or v == " ":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        sl = s.lower()
        # 自然语言温度映射（pH 不会出现这些词）
        if sl in ("room temperature", "room temp", "rt"):
            return 25.0
        if sl in ("physiological temperature", "body temperature"):
            return 37.0
        # 整体解析（含负数）
        try:
            return float(s)
        except ValueError:
            pass
        # 分隔符取首值（- 仅在非开头位置当分隔符，保护负数符号）
        parts = re.split(r"[,;~]|(?<=\d)-", s)
        for p in parts:
            p = p.strip()
            try:
                return float(p)
            except ValueError:
                m = re.search(r"[-+]?\d+(?:\.\d+)?", p)
                if m:
                    return float(m.group())
        return None

    @field_validator("size_nm", "Km_mM", "Vmax_uM_s_minus1", "Kcat_s_minus1",
                     mode="before")
    @classmethod
    def _normalize_numeric(cls, v):
        """通用数值预处理：剥离单位、±误差取主值、科学计数法解析。

        - '1.2 ± 0.1' → 1.2（取主值，剥离误差）
        - '0.5 mM' → 0.5（剥离单位）
        - '1.2e-3' → 0.0012（科学计数法）
        - '50nm' → 50.0（单位连写）
        - size_nm 区间 '10-20' → 15.0（取均值，与 gold 标注习惯一致）
        - 动力学区间不取均值，返回 None
        """
        if v is None or v == "" or v == " ":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        if not s:
            return None
        # 科学计数法归一：'1.664×10⁻⁷' → '1.664e-7'（§16.4 评审修复：否则量级丢失）
        s = _sci_to_e(s)
        # ± 误差：取主值（± 前部分）
        if "±" in s:
            s = s.split("±")[0].strip()
        # 科学计数法直接解析
        try:
            return float(s)
        except ValueError:
            pass
        # 剥离常见单位后解析（mM/nM/μM/nm/℃/s⁻¹ 等）
        # 修静默单位泄漏(§16.4): 旧名单不含 μm/Å/pm，致 "0.1 μm"→0.1nm、"100 Å"→100nm 误存。
        cleaned = re.sub(r"\s*(mM|nM|μM|uM|μm|µm|Å|pm|umol/L|mmol/L|nm|nmol/L|℃|°C|s⁻¹|min⁻¹|M⁻¹|L/mol|mol/L)\s*", "", s, flags=re.I)
        try:
            return float(cleaned)
        except ValueError:
            pass
        # 提取首个数值（含科学计数法）
        m = re.search(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", cleaned)
        if m:
            return float(m.group())
        return None

    @field_validator("size_nm", mode="before")
    @classmethod
    def _normalize_size_range(cls, v):
        """size_nm 区间取均值（'10-20 nm' → 15.0），与 gold 区间标注习惯一致。

        其他动力学字段区间不在此处理（不取均值）。
        """
        if v is None or v == "" or v == " ":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        # 区间模式：数字-数字（非负号减号）
        m = re.match(r"^(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)", s)
        if m:
            lo, hi = float(m.group(1)), float(m.group(2))
            return round((lo + hi) / 2, 2)
        return v  # 交给 _normalize_numeric 处理


# 25 字段名清单，供评估层和智能体对齐使用
FIELD_NAMES: tuple[str, ...] = tuple(FlatRecord.model_fields.keys())

# nanozyme 是必填字段，不能被 safe_validate 置 None
_REQUIRED_FIELDS = {"nanozyme"}


def safe_validate(data: dict) -> tuple[FlatRecord | None, list[str]]:
    """字段级容错验证：从 ValidationError 的 loc 提取坏字段置 None 重试。

    流程：
    1. 尝试 FlatRecord.model_validate(data)
    2. 失败 → 从 e.errors() 提取 loc（字段名）
    3. 将出错的 Optional 字段置 None（不动 nanozyme 等必填字段）
    4. 重新 model_validate，迭代直到成功或仅剩必填字段出错
    5. nanozyme 不可恢复时返回 (None, warnings)

    返回 (record_or_None, warnings)
    """
    warnings: list[str] = []
    if not isinstance(data, dict):
        return None, [f"输入非 dict: {type(data).__name__}"]
    cleaned = dict(data)
    for _ in range(10):  # 最多迭代 10 次
        try:
            record = FlatRecord.model_validate(cleaned)
            return record, warnings
        except ValidationError as e:
            bad_fields = set()
            for err in e.errors():
                loc = err.get("loc", ())
                if loc and isinstance(loc, tuple) and len(loc) > 0:
                    field_name = str(loc[0])
                    if field_name in _REQUIRED_FIELDS:
                        # 必填字段不可恢复 → 整条删除
                        nanozyme_val = cleaned.get("nanozyme", "?")
                        warnings.append(
                            f"记录 nanozyme='{nanozyme_val}' 的必填字段 {field_name} 不可恢复: {err.get('msg', '')}，已丢弃"
                        )
                        return None, warnings
                    bad_fields.add(field_name)
            if not bad_fields:
                return None, [f"记录验证失败但无法定位字段: {str(e)[:200]}"]
            for field in bad_fields:
                original = cleaned.get(field)
                warnings.append(
                    f"记录 nanozyme='{cleaned.get('nanozyme', '?')}' 的 {field} 格式错误已置空: 原值={repr(original)[:100]}"
                )
                cleaned[field] = None
    return None, [f"记录 nanozyme='{cleaned.get('nanozyme', '?')}' 迭代 10 次仍验证失败，已丢弃"]
