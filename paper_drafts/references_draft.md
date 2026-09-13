# References (Draft, ACS style) — Track 1

> 状态：草稿（2026-09-11 第三轮）。格式：ACS（ACS Appl. Mater. Interfaces 标准，投稿二区适用）。
> **编号已按正文首次出现顺序重排（2026-09-11 第三轮）**，共 17 条。
> 本轮改用 KEY 基重编号（`workbench/_insert_audit_refs.py`）：先把正文引用换成稳定 KEY，
> 再按阅读顺序扫描首次出现位置赋号 —— 因为上一轮的"旧号→新号"映射在引用位置移动后会失效
> （§1.1 新增的 AI-ZYMES 版本说明让旧 [7] 出现在旧 [6] 之前）。
> 复核结果（构建产物实测）：`body first-citation order = [1..17]` PASS，无未被引用条目。
> 全部条目已核 DOI；[1][3][4][6][7][8] 已于 2026-09-11 逐篇回上传 PDF 原文核对。
> **[13] 已由 arXiv 预印本更新为正式刊出版本**（DOI 解析确认标题/作者一致）。
> ⚠️ 方括号式引用（SI 表内 `[n]`）已由 `_insert_audit_refs.py` 同步；构建脚本新增越界自检。

---

## 一、编号迁移表

### 1a. 第二轮（主题分组 → 首现顺序）

| 旧 | 第二轮 | 文献 |
|---|---|---|
| [1] | [1] | Gao 2007 Nat. Nanotechnol.（概念原点） |
| [5] | [2] | Razlivina 2024 JPCL（DiZyme 扩展版） |
| [4] | [3] | Razlivina 2022 Small（DiZyme 初始版） |
| [2] | [4] | Wei 2022 Adv. Mater. |
| [7] | [5] | Sun 2024 JCIM（AI-ZYMES 首篇） |
| [3] | [6] | Li 2023 J. Mater. Chem. B |
| [6] | [7] | Xuan 2025 Sci. Rep.（AI-ZYMES 扩版） |
| [8]–[14] | [8]–[14] | 编号不变 |

### 1b. 第三轮（本轮：并入 3 条新增文献）

| 第二轮 | **第三轮** | 文献 |
|---|---|---|
| [1] | **[1]** | Gao 2007 Nat. Nanotechnol. |
| — | **[2]** | **Himanen 2019 Adv. Sci.（新增：data veracity 领域级挑战）** |
| [2] | **[3]** | Razlivina 2024 JPCL（DiZyme 扩展版） |
| [3] | **[4]** | Razlivina 2022 Small（DiZyme 初始版） |
| — | **[5]** | **Wang Q. 2026 arXiv:2609.01621（新增：文献数据误导 AI）** |
| [4] | **[6]** | Wei 2022 Adv. Mater. |
| [5] | **[7]** | Sun 2024 JCIM（AI-ZYMES 首篇） |
| [7] | **[8]** | Xuan 2025 Sci. Rep.（AI-ZYMES 扩版） |
| [6] | **[9]** | Li 2023 J. Mater. Chem. B |
| [8] | **[10]** | NanozymeDB |
| [9] | **[11]** | nanozymes.net |
| — | **[12]** | **Xu 2022 BMJ e069155（新增：数据抽取可复现性）** |
| [10] | **[13]** | Kamatchi Sundaram 2026 Adv. Sci. |
| [11] | **[14]** | Wang X. 2025 arXiv:2510.05142 |
| [12] | **[15]** | Prasad 2024 arXiv:2402.11323 |
| [13] | **[16]** | Katsura 2025 Sci. Technol. Adv. Mater.: Methods |
| [14] | **[17]** | Pedregosa 2011 JMLR（sklearn / GroupKFold） |

> 第三轮迁移原因：(i) §1.1 新增"[2] Himanen / [5] Wang"两条质量审计定位文献；
> (ii) §3.1 新增"[12] Xu"抽取可靠性文献；(iii) §1.1 的 AI-ZYMES 版本说明使 Xuan 的
> 首次出现位置前移到 Li 2023 之前，故 [7]/[6] 互换。全部由脚本按首现顺序机械赋号，非手工指定。

---

## 二、文献表（按正文首现顺序）

**[1] Nanozyme 概念原点（§1.1 引言第一句）**
Gao, L.; Zhuang, J.; Nie, L.; Zhang, J.; Zhang, Y.; Gu, N.; Wang, T.; Feng, J.; Yang, D.; Perrett, S.; Yan, X.
Intrinsic Peroxidase-like Activity of Ferromagnetic Nanoparticles.
*Nat. Nanotechnol.* **2007**, *2*, 577–583. DOI: 10.1038/nnano.2007.260.

**[2] Data veracity as a materials-informatics challenge (§1.1: the quality of the data resource has not kept pace with its volume)**
Himanen, L.; Geurts, A.; Foster, A. S.; Rinke, P.
Data-Driven Materials Science: Status, Challenges, and Perspectives.
*Adv. Sci.* **2019**, *6*, 1900808. DOI: 10.1002/advs.201900808.
> ✅ 2026-09-11 新增并核实：PubMed 31728276 / DOI 解析一致。原文把 data veracity、
> standardisation、data longevity 列为阻碍该领域发展的核心挑战，用于支撑“数据质量是
> 领域级问题而非纳米酶特有”的定位。DOI 有官方勘误（10.1002/advs.201903667），不影响本引用。

**[3] DiZyme 扩展版 + Assistant（§1.1 人工采集瓶颈 / §6.1 对照 / §1.1 回归 R²=0.75）**
Razlivina, J.; Dmitrenko, A.; Vinogradov, V.
AI-Powered Knowledge Base Enables Transparent Prediction of Nanozyme Multiple Catalytic Activity.
*J. Phys. Chem. Lett.* **2024**, *15*, 5804–5813. DOI: 10.1021/acs.jpclett.4c00959.
> ✅ 2026-09-11 回原文核对：1210 experimental samples、R²=0.75 (Km)/0.77 (Vmax)，DiZyme Assistant (ChatGPT)。
> 正文 "DiZyme R²=0.75" 与 "1,210 samples / 390 compositions / 400 articles" 均出自本条（原稿误挂 [4]，已归位）。

**[4] DiZyme 初始版（§1.1 / §3.1 开头：人工整理瓶颈）**
Razlivina, J.; Serov, N.; Shapovalova, O.; Vinogradov, V.
DiZyme: Open-Access Expandable Resource for Quantitative Prediction of Nanozyme Catalytic Activity.
*Small* **2022**, *18*, 2105673. DOI: 10.1002/smll.202105673.
> ✅ 2026-09-11 回原文核对：初始版规模为 ">300 nanozymes from >100 articles"，
> Kcat R²=0.796、Km R²=0.627。正文 `>300 nanozymes from >100 papers ... still rely on manual collection` 引本条。

**[5] Literature-derived data mislead AI (§1.1: ML models inherit the inconsistencies)**
Wang, Q.; Li, Y.; Sato, R.; Kato, H.; Orimo, S.-i.; Li, H.; Cheng, E. J.
When Literature Data Mislead Artificial Intelligence in Materials Discovery.
*[arXiv]* **2026**, arXiv:2609.01621. https://doi.org/10.48550/arXiv.2609.01621.
> ✅ 2026-09-11 新增并核实：arXiv 页面确认标题/作者/提交日期（2026-07-18）。
> 原文以固态电解质电导率为案例，报告 text–figure mismatch、轴标注歧义、单位不一致，
> 并给出一个跨库 100 倍电导率误差的例子 —— 与本工作“单位/条件口径错配造成跨源分歧”同构，
> 且说明该失效模式并非纳米酶独有。投稿时按期刊政策确认预印本格式。

**[6] Wei 2022（§1.1 分类 90.6% / §6.1 对照）**
Wei, Y.; Wu, J.; Wu, Y.; Liu, H.; Meng, F.; Liu, Q.; Midgley, A. C.; Zhang, X.; Qi, T.; Kang, H.; Chen, R.; Kong, D.; Zhuang, J.; Yan, X.; Huang, X.
Prediction and Design of Nanozymes using Explainable Machine Learning.
*Adv. Mater.* **2022**, *34*, 2201736. DOI: 10.1002/adma.202201736.
> ✅ 2026-09-11 回原文核对：90.6% 分类准确率、回归 R² up to 0.80、920 条记录 —— 三项全部一致。

**[7] AI-ZYMES 首篇（§1.1 / §3.1 / §6.1 / §6.3：GBR Km R²≈0.65）**
Sun, L.; Hu, J.; Yang, Y.; Wang, Y.; Wang, Z.; Gao, Y.; Nie, Y.; Liu, C.; Kan, H.
ChatGPT Combining Machine Learning for the Prediction of Nanozyme Catalytic Types and Activities.
*J. Chem. Inf. Model.* **2024**, *64*, 6736–6744. DOI: 10.1021/acs.jcim.4c00600.
> ✅ 2026-09-11 回原文核对：GBR Km R²=0.6476、Kcat R²=0.95；**AI-ZYMES 平台与 ChatGPT copilot 在此论文首次提出**。
> 正文所有 "AI-ZYMES GBR R²=0.648 / ≈0.65" 唯一正确出处即本条。

**[8] AI-ZYMES 扩版（§2.3 四公开库之一 / §1.1 回归 R²≤0.85）**
Xuan, W.; Li, X.; Gao, H.; Zhang, L.; Hu, J.; Sun, L.; Kan, H.
Artificial Intelligence Driven Platform for Rapid Catalytic Performance Assessment of Nanozymes.
*Sci. Rep.* **2025**, *15*, 13305. DOI: 10.1038/s41598-025-96815-9.
> ✅ 2026-09-11 回原文核对：1,085 entries / 400 types / GBR R² up to 0.85。
> ⚠️ 口径注意：[5] 与 [7] 是同一平台的两个版本，R² 不同（0.65 vs 0.85）源于数据集规模不同，非矛盾。

**[9] Li 2023（§1.2 立论支点）**
Li, Y.; Zhang, R.; Yan, X.; Fan, K.
Machine Learning Facilitating the Rational Design of Nanozymes.
*J. Mater. Chem. B* **2023**, *11*, 6466–6477. DOI: 10.1039/d3tb00842h.
> ✅ 2026-09-11 回原文核对：展望第(1)条原文为
> "(1) establishment and development of nanozyme databases. ... it is important and indispensable to
> develop databases with enough available information on nanozymes ... some standard and unified
> detection and representation methods of activity, structure, structure–activity relationship, etc.,
> are needed to guarantee the quality of data and database." —— 正文引原文句，未作转述。

**[10] NanozymeDB（§2.3 四公开库之一）**
Sharma, S.; Singh, K.; Kalra, A.; Sharma, S.
Nanozymedb: A Manually Curated Database to Understand and Match Kinetics of Nanozymes with Natural Enzymes.
*J. Nanotechnol. Res.* **2023**, *5*(4), 22–27. DOI: 10.26502/jnr.2688-85210039.
> 注：发表于小刊（Fortune Journals）；若审稿质疑期刊质量，保留为数据引用即可。

**[11] nanozymes.net（§2.3 四公开库之一，kinetics 子库）**
Nanozymes.net — Kinetics Database. https://nanozymes.net/ (accessed 2026-09-11).
> 注：四公开库中唯一无正式论文的，以网站资源引用。
> ⚠️ 2026-09-11 从沙箱内无法访问该站点（HTTP 000），无法确认链接存活 —— 投稿前需人工复查一次。

**[12] Reproducibility of data extraction (§3.1: human extraction is itself imperfect)**
Xu, C.; Yu, T.; Furuya-Kanamori, L.; Lin, L.; Zorzela, L.; Zhou, X.; Dai, H.; Loke, Y.; Vohra, S.
Validity of Data Extraction in Evidence Synthesis Practice of Adverse Events: Reproducibility Study.
*BMJ* **2022**, *377*, e069155. DOI: 10.1136/bmj-2021-069155.
> ✅ 2026-09-11 新增并核实：PubMed 35537752 / DOI 解析一致。原文报告 10,386 条试验记录中
> 1,762 条（17.0%）无法从原始来源复现，误差以数值错误（49.2%）与定义歧义（29.9%）为主。
> 用于给“人工抽取本身有误差率”提供可引证数字；同时是 §4.2 参考源本身可能含错的外部依据。

**[13] Kamatchi Sundaram et al.（§3.1 LLM 提取先例）★ 已由预印本更新为正式刊出**
Kamatchi Sundaram, A.; Chakraborty, M.; Devathi, S. M. K.; Prusty, B. P.; Batra, R.
Automated Extraction of Multicomponent Alloy Data Using Large Language Models for Sustainable Design.
*Adv. Sci.* **2026**, e75916. DOI: 10.1002/advs.75916.
> ✅ 2026-09-11 更新：原引 arXiv:2602.04602。该文已于 2026-06-09 正式刊出于 *Advanced Science*，
> DOI `10.1002/advs.75916` 经解析确认标题与作者完全一致（IIT Madras, Rohit Batra 通讯）。
> arXiv 编号 `2602.*` 前缀对应 2026 年 2 月，与所标年份一致，非笔误。

**[14] Wang et al. 2025（§3.1 LLM 提取先例，47 特征多阶段 + 来源追踪）**
Wang, X.; Raj, A.; Luebbe, M.; Wen, H.; Xu, S.; Lu, K.
Reliable End-to-End Material Information Extraction from the Literature with Source-Tracked Multi-Stage Large Language Models.
*[arXiv]* **2025**, arXiv:2510.05142. https://arxiv.org/abs/2510.05142.
> 2026-09-11 核实：仍为预印本，未见正式刊出版本 —— 按期刊政策决定保留 arXiv 格式。

**[15] Prasad et al. 2024（§3.1 LLM 提取先例，材料知识图谱自动构建）**
Prasad, D.; Pimpude, M.; Alankar, A.
Towards Development of Automated Knowledge Maps and Databases for Materials Engineering Using Large Language Models.
*[arXiv]* **2024**, arXiv:2402.11323. https://arxiv.org/abs/2402.11323.
> 2026-09-11 核实：仍为预印本，未见正式刊出版本。

**[16] Katsura et al. 2025（§3.1 LLM 提取先例，Starrydata 策展）**
Katsura, Y.; Mato, T.; Takada, Y.; Koyama, E.; Yana, D.; Tanaka, A.; Kumagai, M.
Development of LLM-Assisted Data Curation Tools for the Starrydata Materials Science Database.
*Sci. Technol. Adv. Mater.: Methods* **2025**, *5*, 2590811. DOI: 10.1080/27660400.2025.2590811.

**[17] Odobesku et al. 2025（§3.1 最近的同域先例：nanoMINER，多智能体多模态纳米酶提取）**
Odobesku, R.; Romanova, K.; Mirzaeva, S.; Zagorulko, O.; Sim, R.; Khakimullin, R.;
Razlivina, J.; Dmitrenko, A.; Vinogradov, V. Agent-Based Multimodal Information Extraction
for Nanomaterials. *npj Comput. Mater.* **2025**, *11*, 194. DOI: 10.1038/s41524-025-01674-7.
> 2026-09-12 新增（round 14）。正文原称"none of these targets condition-bound nanozyme
> kinetics"，而该文正是纳米酶域内的多智能体（Text+Vision+NER）参数抽取系统，抽取 Kₘ /
> Vmax / pH / 温度并给出逐参数 P/R —— 属直接的最近先例，必须引用并据此重新定位本文创新点
> （条件绑定 schema + 跨源审计 + 泄漏重评，而非"多智能体抽取"本身）。
> CrossRef 核实：npj Computational Materials 2025, 11, 194；作者含 DiZyme 团队
> （Razlivina / Dmitrenko / Vinogradov），与本文对比的 DiZyme 同源。

**[18] 分组交叉验证（§6.2 GroupKFold 方法来源）**
Pedregosa, F.; Varoquaux, G.; Gramfort, A.; Michel, V.; Thirion, B.; Grisel, O.;
Blondel, M.; Prettenhofer, P.; Weiss, R.; Dubourg, V.; et al. Scikit-learn: Machine
Learning in Python. *J. Mach. Learn. Res.* **2011**, *12*, 2825–2830.
> 注：§6 使用 sklearn `GroupKFold` 语义。2026-09-12 由 [17] 顺延为 [18]；作者列按 ACS
> 体例补前 10 位 + et al.（原为 "Pedregosa, F.; et al."）。

---

## 三、引用点核对（新编号）

| 正文位置 | 引用内容 | 新编号 |
|---|---|---|
| §1.1 首句 | Fe₃O₄ 模拟过氧化物酶 | [1] |
| §1.1 | data veracity 是数据驱动材料科学的领域级挑战 | **[2]** |
| §1.1 | DiZyme 人工采集（1,210 samples / 390 compositions / 400 papers） | [3] |
| §1.1 | DiZyme 初始版（>300 纳米酶 / >100 篇） | [4] |
| §1.1 | 文献衍生数据误导 ML：text–figure 错配 / 单位不一致 / 跨库 100× 误差 | **[5]** |
| §1.1/§6.1 | Wei 90.6% 随机划分（R² up to 0.80，920 条） | [6] |
| §1.1/§6.1 | DiZyme R²=0.75（Kₘ）/0.77（Vmax）/ Assistant 对照 | [3] |
| §1.1/§3.1/§6.1/§6.3 | AI-ZYMES GBR R²≈0.65（Kₘ R²=0.6476，首版） | [7] |
| §1.1/§2.3（Table S2） | AI-ZYMES 扩版 GBR R²≤0.85（1,085 entries / 400 types） | [8] |
| §1.2 | Li 2023 立论支点（展望第(1)条原文句） | [9] |
| §2.3 | 四公开库：AI-ZYMES / DiZyme / NanozymeDB / nanozymenet-k | [8][4][10][11] |
| §3.1 | 人工抽取可复现性（17.0% 无法复现） | **[12]** |
| §3.1 | LLM 提取先例（材料领域） | [13][14][15][16] |
| §3.1 | 同域最近先例：nanoMINER（多智能体多模态纳米酶抽取） | **[17]** |
| §6.2 | GroupKFold 分组交叉验证 | [18] |

---

## 四、待办（投稿前）

> 1. ✅ 已核对（2026-09-11）：[1][3][4][6][7][8] 逐篇回上传 PDF 原文；[13] 已更新为 *Adv. Sci.* 正式版。
> 2. ✅ 本轮新增 [2][5][12]，三条均经 DOI/PubMed/arXiv 页面解析确认标题、作者、年份一致（详见各条目注）。
> 3. ⚠️ [11] nanozymes.net 链接存活需人工复查（沙箱不可达）。
> 4. ⚠️ [5][14][15] 仍为 arXiv 预印本；投稿时按期刊政策决定是否保留预印本格式。
> 5. 序号已按首现顺序重排（KEY 基脚本 `workbench/_insert_audit_refs.py`）；定稿时仍需用期刊模板
>    （ACS 或备选 JCIM）复核一遍格式与标点。正文 `<sup>` 与 SI 方括号 `[n]` 两种形式均已覆盖。
> 6. 若正文 §3 增加"为何用 LLM 而非传统 NLP"论述，可再补 ChemDataExtractor / MaScQA 等经典；
>    §6.4 检索优先若需对口可补 Top-k 检索文献——当前清单覆盖最小充分集。
> 7. 自引（本工作前作/预印本）若无则留空；若有需在投稿时补。
