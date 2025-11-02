# 知识库模块详细技术文档

## 📋 目录

1. [模块概述](#模块概述)
2. [核心组件详解](#核心组件详解)
3. [知识库构建流程](#知识库构建流程)
4. [知识库检索流程](#知识库检索流程)
5. [文本处理详解](#文本处理详解)
6. [向量化与索引](#向量化与索引)
7. [项目故事库](#项目故事库)
8. [UI交互流程](#ui交互流程)

---

## 模块概述

### 功能定位

知识库模块（Knowledge Base Module）是RAG（Retrieval-Augmented Generation）系统的核心组件，负责：

1. **文本收集与处理**：扫描、读取、清理、分块文本文件
2. **向量化**：将文本转换为数值向量
3. **索引构建**：使用FAISS构建高效的向量索引
4. **相似度检索**：根据查询文本检索最相关的文本片段

### 模块结构

```
知识库模块
├── ingest.py: 知识库构建
│   ├── IngestConfig: 配置类
│   └── KnowledgeBaseIngestor: 构建器类
│
├── search.py: 知识库检索
│   ├── SearchConfig: 配置类
│   └── KnowledgeBaseSearcher: 检索器类
│
├── kb_mixin.py: UI交互
│   └── KbMixin: UI控制类
│
└── utils/text.py: 文本处理工具
    ├── discover_text_files(): 文件发现
    ├── read_file_text(): 文件读取
    ├── clean_text(): 文本清理
    └── split_by_length(): 文本分块
```

---

## 核心组件详解

### 1. KnowledgeBaseIngestor（知识库构建器）

#### 类定义

```python
class KnowledgeBaseIngestor:
    """知识库构建器：负责将文本文件转换为向量索引"""
    
    def __init__(self, config: IngestConfig):
        self.config = config
        # 延迟加载模型（首次使用会下载，约3-5秒）
        self.model = SentenceTransformer(config.embedding_model_name)
        # 默认模型: paraphrase-multilingual-MiniLM-L12-v2
        # 特点：
        # - 支持多语言（中文、英文等）
        # - 轻量级（12层Transformer）
        # - 优化用于语义相似度任务
        # - 输出384维向量
    
    def _embed(self, texts: List[str]) -> np.ndarray:
        """将文本列表转换为向量数组"""
        return self.model.encode(
            texts,
            show_progress_bar=False,  # 不显示进度条（避免干扰）
            convert_to_numpy=True,    # 返回numpy数组
            normalize_embeddings=True  # 归一化向量（用于内积相似度）
        )
        # 返回: numpy.ndarray, shape=(N, 384)
        # N = 文本数量
        # 384 = 向量维度
    
    def build(self) -> None:
        """构建知识库索引的完整流程"""
        # 详见下方"知识库构建流程"章节
```

#### IngestConfig（配置类）

```python
@dataclass
class IngestConfig:
    """知识库构建配置"""
    data_root: Path          # 数据目录（包含文本文件）
    index_dir: Path          # 索引目录（保存索引文件）
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    max_chars: int = 800     # 每个文本块的最大字符数
    overlap: int = 120       # 相邻块之间的重叠字符数
```

**配置参数说明**：

- **data_root**: 包含`.txt`/`.md`/`.markdown`文件的目录
- **index_dir**: 索引文件保存目录，将创建以下文件：
  - `kb.index`: FAISS索引文件
  - `chunks.npy`: 文本块数组
  - `meta.npy`: 元数据数组（文件路径，块索引）
- **max_chars**: 每个文本块的最大字符数（800字符）
  - 太小：可能丢失上下文
  - 太大：检索精度下降，向量化耗时增加
  - 800字符是平衡点：约200-300字中文，足够包含完整段落
- **overlap**: 重叠字符数（120字符）
  - 保证相邻块之间的上下文连续性
  - 避免在句子中间切分

### 2. KnowledgeBaseSearcher（知识库检索器）

#### 类定义

```python
class KnowledgeBaseSearcher:
    """知识库检索器：负责根据查询检索相关文本片段"""
    
    def __init__(self, config: SearchConfig):
        self.config = config
        # 加载模型（与Ingestor使用相同模型）
        self.model = SentenceTransformer(config.embedding_model_name)
        # 加载索引（初始化时自动加载）
        self._load()
    
    def _load(self) -> None:
        """加载知识库索引"""
        # 检查必需文件
        index_path = self.config.index_dir / "kb.index"
        chunks_path = self.config.index_dir / "chunks.npy"
        meta_path = self.config.index_dir / "meta.npy"
        
        # 验证文件存在
        missing_files = []
        if not index_path.exists():
            missing_files.append("kb.index")
        if not chunks_path.exists():
            missing_files.append("chunks.npy")
        if not meta_path.exists():
            missing_files.append("meta.npy")
        
        if missing_files:
            raise RuntimeError(
                f"知识库文件缺失: {', '.join(missing_files)}\n"
                f"请先构建索引：点击「构建索引」按钮"
            )
        
        # 加载索引和数据
        self.index = faiss.read_index(str(index_path))
        self.chunks: List[str] = list(np.load(chunks_path, allow_pickle=True))
        self.metas: List[Tuple[str, int]] = list(np.load(meta_path, allow_pickle=True))
        
        # 验证数据一致性
        if len(self.chunks) != len(self.metas):
            raise RuntimeError(f"数据不一致: chunks数量({len(self.chunks)}) != metas数量({len(self.metas)})")
        
        if self.index.ntotal != len(self.chunks):
            raise RuntimeError(f"索引不一致: 索引条目({self.index.ntotal}) != chunks数量({len(self.chunks)})")
    
    def search(self, query: str, top_k: int | None = None) -> List[Tuple[str, float, Tuple[str, int]]]:
        """检索最相关的文本片段"""
        topk = top_k or self.config.top_k
        
        # 步骤1: 将查询文本转换为向量
        emb = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype("float32")
        # emb形状: (1, 384)
        
        # 步骤2: 在FAISS索引中搜索
        scores, idxs = self.index.search(emb, topk)
        # scores: 相似度分数（内积值，越大越相似）
        # idxs: 对应的向量索引
        
        # 步骤3: 组装结果
        results: List[Tuple[str, float, Tuple[str, int]]] = []
        for score, idx in zip(scores[0], idxs[0]):
            if int(idx) < 0:  # FAISS返回-1表示无效结果
                continue
            results.append((
                self.chunks[int(idx)],      # 文本内容
                float(score),               # 相似度分数
                self.metas[int(idx)]        # 元数据（文件路径，块索引）
            ))
        
        return results
```

#### SearchConfig（配置类）

```python
@dataclass
class SearchConfig:
    """知识库检索配置"""
    index_dir: Path          # 索引目录（读取索引文件）
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    top_k: int = 6          # 返回最相关的K个结果
```

**配置参数说明**：

- **index_dir**: 索引文件所在目录
- **top_k**: 返回最相关的K个结果
  - 太小（如3）：可能遗漏重要信息
  - 太大（如20）：可能包含不相关内容，增加Prompt长度
  - 6是平衡点：足以覆盖多个角度，不会过度冗余

---

## 知识库构建流程

### 完整流程图

```
用户点击"构建索引"按钮
  │
  ├─→ KbMixin.on_ingest()
  │   ├─→ 检查数据目录是否存在
  │   ├─→ 检查是否有文本文件
  │   └─→ 确认构建（弹窗）
  │
  ├─→ 启动后台线程
  │   └─→ threading.Thread(target=task, daemon=True).start()
  │
  ├─→ 后台任务执行
  │   │
  │   ├─→ 步骤1: 延迟导入知识库模块
  │   │   └─→ from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
  │   │       # 首次导入会下载sentence-transformers模型（约3-5秒）
  │   │
  │   ├─→ 步骤2: 创建配置对象
  │   │   └─→ cfg = IngestConfig(
  │   │           data_root=Path(self.data_dir.get()),
  │   │           index_dir=Path(self.index_dir.get())
  │   │       )
  │   │
  │   ├─→ 步骤3: 创建构建器
  │   │   └─→ ingestor = KnowledgeBaseIngestor(cfg)
  │   │       # 初始化时会加载SentenceTransformer模型
  │   │
  │   └─→ 步骤4: 执行构建
  │       └─→ ingestor.build()
  │           │
  │           ├─→ 4.1: 创建索引目录
  │           │   └─→ self.config.index_dir.mkdir(parents=True, exist_ok=True)
  │           │
  │           ├─→ 4.2: 扫描文本文件
  │           │   └─→ files = discover_text_files(self.config.data_root)
  │           │       # 递归扫描所有.txt/.md/.markdown文件
  │           │
  │           ├─→ 4.3: 读取和分块文本
  │           │   └─→ 对每个文件:
  │           │       ├─→ text = clean_text(read_file_text(fp))
  │           │       │   # 读取文件内容并清理
  │           │       │
  │           │       └─→ parts = split_by_length(text, max_chars=800, overlap=120)
  │           │           # 将文本分割成800字符的块，重叠120字符
  │           │
  │           ├─→ 4.4: 向量化文本块
  │           │   └─→ embeddings = self._embed(chunks)
  │           │       # 使用SentenceTransformer将文本转换为向量
  │           │       # 返回: numpy.ndarray, shape=(N, 384)
  │           │
  │           ├─→ 4.5: 构建FAISS索引
  │           │   └─→ index = faiss.IndexFlatIP(384)
  │           │       ├─→ 创建内积索引（384维）
  │           │       ├─→ index.add(embeddings)
  │           │       └─→ 添加所有向量到索引
  │           │
  │           └─→ 4.6: 保存到磁盘
  │               ├─→ faiss.write_index(index, "kb.index")
  │               ├─→ np.save("chunks.npy", chunks)
  │               └─→ np.save("meta.npy", metas)
```

### 详细步骤说明

#### 步骤1: 文件扫描 (`discover_text_files`)

```python
def discover_text_files(root: str | os.PathLike[str]) -> List[Path]:
    """
    递归扫描文本文件
    
    参数:
        root: 根目录路径
    
    返回:
        文本文件路径列表
    
    支持的格式:
        - .txt
        - .md
        - .markdown
    """
    root_path = Path(root)
    candidates: List[Path] = []
    
    # 使用rglob递归扫描所有文件
    for path in root_path.rglob("*"):
        if path.is_file():
            lower = path.name.lower()
            # 检查文件扩展名
            if lower.endswith((".txt", ".md", ".markdown")):
                candidates.append(path)
    
    # 返回排序后的文件列表
    return sorted(candidates)
```

**示例**：

```
data/
├── story1.txt
├── story2.md
└── subdir/
    └── story3.txt

扫描结果: [Path("data/story1.txt"), Path("data/story2.md"), Path("data/subdir/story3.txt")]
```

#### 步骤2: 文本读取 (`read_file_text`)

```python
def read_file_text(path: Path) -> str:
    """
    读取文本文件内容
    
    参数:
        path: 文件路径
    
    返回:
        文件内容（字符串）
    
    编码处理:
        - 使用UTF-8编码
        - errors="ignore": 遇到无法解码的字符时忽略，继续读取
    """
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return f.read()
```

**错误处理**：
- 如果文件不是UTF-8编码，`errors="ignore"`会忽略无法解码的字符
- 避免因编码问题导致整个构建失败

#### 步骤3: 文本清理 (`clean_text`)

```python
def clean_text(text: str) -> str:
    """
    清理文本：统一换行符、清理空白字符
    
    处理内容:
        1. 统一换行符: \r\n → \n, \r → \n
        2. 全角空格转半角空格: \u3000 → 空格
        3. 合并多个连续换行: \n{3,} → \n\n
        4. 去除首尾空白
    """
    # 统一换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # 全角空格转半角空格
    text = re.sub("\u3000", " ", text)
    
    # 合并多个连续换行（最多保留两个换行）
    text = re.sub("\n{3,}", "\n\n", text)
    
    # 去除首尾空白
    return text.strip()
```

**示例**：

```python
# 输入
text = "这是第一段\r\n\r\n\r\n这是第二段\u3000\u3000有全角空格"

# 输出
"这是第一段\n\n这是第二段  有全角空格"
```

#### 步骤4: 文本分块 (`split_by_length`)

```python
def split_by_length(text: str, max_chars: int = 800, overlap: int = 120) -> List[str]:
    """
    按字符数分割文本，尽量保持句子完整性
    
    参数:
        text: 要分割的文本
        max_chars: 每个块的最大字符数
        overlap: 相邻块之间的重叠字符数
    
    返回:
        文本块列表
    
    分割策略:
        1. 按句子边界分割（中文句号、英文句号等）
        2. 尽量保持句子完整性
        3. 相邻块重叠overlap字符
    """
    if not text:
        return []
    
    # 步骤1: 按句子分割（匹配句号、问号、感叹号后的空白）
    sentences = re.split(r"(?<=[。！？!?.])\s+", text)
    # (?<=...) 是正向后顾断言，匹配句号后但不包含句号本身
    # \s+ 匹配一个或多个空白字符
    
    chunks: List[str] = []
    current: List[str] = []  # 当前块中的句子列表
    current_len = 0           # 当前块的总字符数
    
    # 步骤2: 逐个处理句子
    for s in sentences:
        s_len = len(s)
        
        # 如果当前块加上这个句子不超过max_chars，或者当前块为空
        if current_len + s_len <= max_chars or not current:
            current.append(s)
            current_len += s_len
        else:
            # 当前块已满，保存当前块
            chunks.append("".join(current).strip())
            
            # 添加重叠：取前一个块的末尾overlap字符
            if overlap > 0 and chunks[-1]:
                tail = chunks[-1][-overlap:]  # 取末尾overlap字符
                current = [tail, s]           # 新块以重叠部分开始
                current_len = len(tail) + s_len
            else:
                current = [s]
                current_len = s_len
    
    # 步骤3: 保存最后一个块
    if current:
        chunks.append("".join(current).strip())
    
    # 步骤4: 过滤太小的块（小于20字符）
    return [c for c in chunks if len(c) > 20]
```

**示例**：

```python
# 输入文本（假设500字符）
text = "这是第一段。这是第二段。这是第三段。这是第四段。这是第五段。"

# 分割（max_chars=200, overlap=50）
chunks = split_by_length(text, max_chars=200, overlap=50)

# 结果
[
    "这是第一段。这是第二段。这是第三段。",
    "这是第三段。这是第四段。这是第五段。"
]
# 注意：第二个块的开头包含了第一个块的末尾（重叠部分）
```

**重叠的作用**：

```
块1: [-----------800字符-----------]
块2:              [-----------800字符-----------]
                  ↑
                重叠120字符

好处：
1. 保证上下文连续性
2. 避免在句子中间切分
3. 提高检索精度（边界处的内容也能被检索到）
```

#### 步骤5: 向量化 (`_embed`)

```python
def _embed(self, texts: List[str]) -> np.ndarray:
    """
    将文本列表转换为向量数组
    
    参数:
        texts: 文本列表（例如：["文本1", "文本2", ...]）
    
    返回:
        向量数组，形状 (N, 384)
        N = 文本数量
        384 = 向量维度
    
    向量化过程:
        1. SentenceTransformer模型编码
        2. 归一化向量（normalize_embeddings=True）
           - 归一化后：||vector|| = 1
           - 用于内积相似度计算
    """
    return self.model.encode(
        texts,
        show_progress_bar=False,    # 不显示进度条
        convert_to_numpy=True,      # 返回numpy数组（不是list）
        normalize_embeddings=True   # 归一化向量
    )
```

**向量化示例**：

```python
# 输入
texts = ["这是一个故事", "这是另一个故事"]

# 输出
embeddings = np.array([
    [0.1, 0.2, 0.3, ..., 0.9],  # 384个浮点数
    [0.2, 0.3, 0.4, ..., 0.8]   # 384个浮点数
], dtype=np.float32)
# 形状: (2, 384)

# 归一化后
# ||embeddings[0]|| ≈ 1.0
# ||embeddings[1]|| ≈ 1.0
```

#### 步骤6: 构建FAISS索引

```python
# 创建索引
index = faiss.IndexFlatIP(384)
# IndexFlatIP = Index Flat Inner Product（内积索引）
# 384 = 向量维度

# 添加向量
index.add(embeddings)
# embeddings形状: (N, 384)
# 索引现在包含N个向量

# 索引特点:
# - 内积索引：适合归一化向量
# - 精确搜索：返回最相似的结果（不是近似）
# - 内存索引：所有向量存储在内存中
# - 适合中小规模数据（<100万向量）
```

**为什么使用IndexFlatIP**：

1. **归一化向量的内积 = 余弦相似度**
   ```
   内积: a · b = ||a|| ||b|| cos(θ)
   归一化后: ||a|| = ||b|| = 1
   因此: a · b = cos(θ)
   ```

2. **精确搜索**
   - 不是近似搜索（如LSH）
   - 返回最相似的结果
   - 适合数据量不太大的场景（<100万向量）

3. **简单高效**
   - 无需训练
   - 添加向量即可使用
   - 内存占用小

#### 步骤7: 保存到磁盘

```python
# 保存FAISS索引
faiss.write_index(index, str(self.config.index_dir / "kb.index"))
# 保存为二进制文件，包含所有向量数据

# 保存文本块数组
np.save(self.config.index_dir / "chunks.npy", np.array(chunks, dtype=object))
# dtype=object 允许存储字符串对象
# 保存为.npy文件（numpy格式）

# 保存元数据数组
np.save(self.config.index_dir / "meta.npy", np.array(metas, dtype=object))
# metas格式: [(文件路径, 块索引), ...]
# 例如: [("data/story1.txt", 0), ("data/story1.txt", 1), ...]
```

**文件结构**：

```
index/
├── kb.index      # FAISS索引文件（二进制）
├── chunks.npy    # 文本块数组（numpy格式）
└── meta.npy      # 元数据数组（numpy格式）
```

---

## 知识库检索流程

### 完整流程图

```
故事生成请求
  │
  ├─→ StoryGeneratorMixin.on_generate()
  │   └─→ 检查是否启用RAG
  │
  ├─→ 创建检索器
  │   └─→ searcher = KnowledgeBaseSearcher(
  │           SearchConfig(
  │               index_dir=Path(self.index_dir.get()),
  │               top_k=self.top_k.get()
  │           )
  │       )
  │       │
  │       ├─→ 加载模型（SentenceTransformer）
  │       └─→ _load() 加载索引
  │           ├─→ faiss.read_index("kb.index")
  │           ├─→ np.load("chunks.npy")
  │           └─→ np.load("meta.npy")
  │
  ├─→ 执行检索
  │   └─→ results = searcher.search(query, top_k=6)
  │       │
  │       ├─→ 步骤1: 查询向量化
  │       │   └─→ emb = self.model.encode([query])
  │       │       # 形状: (1, 384)
  │       │
  │       ├─→ 步骤2: FAISS搜索
  │       │   └─→ scores, idxs = self.index.search(emb, top_k)
  │       │       # scores: 相似度分数（内积值）
  │       │       # idxs: 向量索引
  │       │
  │       └─→ 步骤3: 组装结果
  │           └─→ 返回 (文本, 分数, 元数据) 列表
  │
  └─→ 使用检索结果
      └─→ contexts = [c for c, _s, _m in results]
          └─→ 作为Prompt的一部分传递给AI模型
```

### 详细步骤说明

#### 步骤1: 查询向量化

```python
# 用户输入的查询
query = "写一个关于爱情的故事，要有反转"

# 向量化
emb = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
# 形状: (1, 384)
# 归一化后: ||emb[0]|| ≈ 1.0
```

#### 步骤2: FAISS搜索

```python
# 搜索top_k个最相似的向量
scores, idxs = self.index.search(emb, top_k=6)
# scores形状: (1, 6) - 6个相似度分数
# idxs形状: (1, 6) - 6个向量索引

# 示例结果
scores = [[0.85, 0.82, 0.78, 0.75, 0.72, 0.68]]
idxs = [[123, 456, 789, 234, 567, 890]]
# 分数越大越相似（内积值，范围通常-1到1）
```

**搜索算法**：

```python
# FAISS内部算法（简化版）
for each_vector in index:
    score = dot_product(query_vector, vector)  # 内积
    # 因为向量已归一化，内积 = 余弦相似度

# 选择top_k个最高分数的向量
# 返回分数和索引
```

#### 步骤3: 组装结果

```python
results: List[Tuple[str, float, Tuple[str, int]]] = []

for score, idx in zip(scores[0], idxs[0]):
    if int(idx) < 0:  # FAISS返回-1表示无效结果
        continue
    
    # 获取文本内容
    text = self.chunks[int(idx)]
    
    # 获取元数据
    meta = self.metas[int(idx)]  # (文件路径, 块索引)
    
    # 组装结果
    results.append((text, float(score), meta))

# 返回结果
return results
```

**结果格式**：

```python
results = [
    (
        "这是检索到的第一个文本片段...",  # 文本内容
        0.85,                              # 相似度分数
        ("data/story1.txt", 0)             # 元数据（文件路径，块索引）
    ),
    (
        "这是检索到的第二个文本片段...",
        0.82,
        ("data/story2.txt", 2)
    ),
    # ... 更多结果
]
```

---

## 文本处理详解

### 文本分块算法详解

#### 算法目标

1. **按字符数分割**：每个块不超过max_chars字符
2. **保持句子完整性**：尽量在句子边界处分割
3. **重叠处理**：相邻块重叠overlap字符

#### 算法实现

```python
def split_by_length(text: str, max_chars: int = 800, overlap: int = 120) -> List[str]:
    """
    文本分块算法详解
    """
    # 步骤1: 按句子分割
    sentences = re.split(r"(?<=[。！？!?.])\s+", text)
    # 正则表达式说明:
    # (?<=[。！？!?.]) - 正向后顾断言，匹配句号后
    # \s+ - 一个或多个空白字符
    # 结果: 将文本分割成句子列表
    
    chunks: List[str] = []
    current: List[str] = []  # 当前块的句子列表
    current_len = 0           # 当前块的总字符数
    
    # 步骤2: 逐个处理句子
    for s in sentences:
        s_len = len(s)
        
        # 情况1: 当前块加上这个句子不超过max_chars，或者当前块为空
        if current_len + s_len <= max_chars or not current:
            current.append(s)
            current_len += s_len
        
        # 情况2: 当前块已满
        else:
            # 保存当前块
            chunks.append("".join(current).strip())
            
            # 处理重叠
            if overlap > 0 and chunks[-1]:
                # 取前一个块的末尾overlap字符
                tail = chunks[-1][-overlap:]
                # 新块以重叠部分开始
                current = [tail, s]
                current_len = len(tail) + s_len
            else:
                current = [s]
                current_len = s_len
    
    # 步骤3: 保存最后一个块
    if current:
        chunks.append("".join(current).strip())
    
    # 步骤4: 过滤太小的块
    return [c for c in chunks if len(c) > 20]
```

#### 算法示例

```python
# 输入文本（假设3000字符）
text = """
第一章：相遇
这是一个关于爱情的故事。主人公叫小明，他在大学里遇到了小红。他们第一次见面是在图书馆。

第二章：相识
小明和小红开始慢慢熟悉起来。他们一起上课，一起吃饭，一起聊天。渐渐地，他们发现彼此有很多共同点。

第三章：相恋
小明终于鼓起勇气向小红表白。小红答应了，他们开始了一段美好的恋情。这段恋情持续了三年。
"""

# 分块（max_chars=200, overlap=50）
chunks = split_by_length(text, max_chars=200, overlap=50)

# 结果
[
    "第一章：相遇\n这是一个关于爱情的故事。主人公叫小明，他在大学里遇到了小红。他们第一次见面是在图书馆。\n\n第二章：相识\n小明和小红开始慢慢熟悉起来。",
    "他们开始慢慢熟悉起来。他们一起上课，一起吃饭，一起聊天。渐渐地，他们发现彼此有很多共同点。\n\n第三章：相恋\n小明终于鼓起勇气向小红表白。",
    "小明终于鼓起勇气向小红表白。小红答应了，他们开始了一段美好的恋情。这段恋情持续了三年。"
]
# 注意：每个块的开头都包含了前一个块的末尾（重叠部分）
```

---

## 向量化与索引

### Sentence Transformer模型

#### 模型选择

```python
model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
```

**为什么选择这个模型**：

1. **multilingual**: 支持多语言（中文、英文等）
   - 使用多语言BERT预训练
   - 在中文和英文数据上都有良好表现

2. **MiniLM**: 轻量级模型
   - 参数量少，速度快
   - 推理速度快（GPU: <10ms，CPU: <100ms）

3. **L12**: 12层Transformer
   - 平衡性能和速度
   - 不是最深的模型，但足够用

4. **paraphrase**: 专门优化用于语义相似度
   - 训练目标：使相似文本的向量更接近
   - 适合RAG检索任务

5. **输出384维向量**
   - 维度适中（不是太大也不是太小）
   - 适合FAISS索引

#### 向量化过程

```python
# 输入文本
text = "这是一个关于爱情的故事"

# 模型编码
vector = model.encode(text)
# 过程:
# 1. Tokenization: 将文本转换为token序列
# 2. Embedding: 将token转换为向量
# 3. Transformer编码: 通过12层Transformer编码
# 4. 池化: 将序列向量池化为单个向量（通常使用mean pooling）
# 5. 归一化: 归一化向量（normalize_embeddings=True）

# 输出
vector = np.array([0.1, 0.2, 0.3, ..., 0.9], dtype=np.float32)
# 形状: (384,)
# 归一化后: ||vector|| ≈ 1.0
```

### FAISS索引

#### IndexFlatIP（内积索引）

```python
# 创建索引
index = faiss.IndexFlatIP(384)
# IndexFlatIP = Index Flat Inner Product
# 384 = 向量维度

# 特点:
# 1. 精确搜索：不是近似搜索
# 2. 内积相似度：适合归一化向量
# 3. 内存索引：所有向量存储在内存中
# 4. 适合中小规模数据（<100万向量）
```

#### 搜索算法

```python
def search(query_vector, top_k):
    """
    FAISS搜索算法（简化版）
    """
    scores = []
    
    # 遍历所有向量
    for i, vector in enumerate(index):
        # 计算内积（相似度）
        score = dot_product(query_vector, vector)
        scores.append((score, i))
    
    # 排序并选择top_k
    scores.sort(reverse=True)
    return scores[:top_k]
```

**时间复杂度**：

- **O(N)**：需要遍历所有向量
- **N = 向量数量**
- 对于中小规模数据（<100万向量），这是可以接受的

**优化选项**（如果需要）：

```python
# 如果数据量很大（>100万向量），可以使用近似搜索
index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
# IVFFlat = Inverted File Index Flat
# 特点:
# - 需要训练
# - 近似搜索（更快但不完全精确）
# - 适合大规模数据
```

---

## 项目故事库

### 功能说明

项目故事库是从`projects/`目录下的所有`story.txt`文件中提取故事，构建专门的知识库。

### 构建流程

```python
def on_build_project_stories_kb(self):
    """构建项目故事知识库"""
    
    # 步骤1: 查找所有story.txt文件
    projects_dir = Path("projects")
    story_files = list(projects_dir.rglob("story.txt"))
    # 排除备份文件
    story_files = [f for f in story_files if not f.name.endswith(".bak")]
    
    # 步骤2: 创建临时目录
    temp_stories_dir = Path(tempfile.mkdtemp(prefix="project_stories_"))
    
    # 步骤3: 复制故事文件到临时目录
    for story_file in story_files:
        project_name = story_file.parent.name
        target_file = temp_stories_dir / f"{project_name}_story.txt"
        shutil.copy2(story_file, target_file)
    
    # 步骤4: 构建索引
    index_dir = Path("index") / "project_stories"
    cfg = IngestConfig(
        data_root=temp_stories_dir,
        index_dir=index_dir
    )
    ingestor = KnowledgeBaseIngestor(cfg)
    ingestor.build()
    
    # 步骤5: 清理临时目录
    shutil.rmtree(temp_stories_dir)
```

### 使用场景

1. **从过往优秀故事中学习**
   - 检索相似的故事片段
   - 学习叙事技巧、语言风格

2. **保持风格一致性**
   - 参考自己之前写的故事
   - 保持创作风格的一致性

3. **提高创作质量**
   - RAG增强生成
   - 借鉴优秀片段

---

## UI交互流程

### 构建索引流程

```
用户操作
  │
  ├─→ 点击"构建索引"按钮
  │   └─→ KbMixin.on_ingest()
  │       │
  │       ├─→ 检查数据目录是否存在
  │       ├─→ 检查是否有文本文件
  │       └─→ 确认构建（弹窗）
  │
  ├─→ 用户确认
  │   └─→ 启动后台线程
  │
  ├─→ 后台任务执行
  │   ├─→ 更新UI状态: "正在构建知识库索引..."
  │   ├─→ 延迟导入知识库模块
  │   ├─→ 创建配置和构建器
  │   ├─→ 执行构建
  │   └─→ 更新UI状态: "✅ 索引构建完成"
  │
  └─→ 显示成功消息
      └─→ messagebox.showinfo("成功", "知识库索引构建完成！")
```

### 检索流程

```
故事生成请求
  │
  ├─→ StoryGeneratorMixin.on_generate()
  │   └─→ 检查是否启用RAG
  │
  ├─→ 创建检索器（如果索引不存在，提示构建）
  │   └─→ KnowledgeBaseSearcher(...)
  │
  ├─→ 执行检索
  │   └─→ searcher.search(query, top_k=6)
  │
  └─→ 使用检索结果
      └─→ 作为Prompt的一部分传递给AI模型
```

---

## 总结

知识库模块是RAG系统的核心，提供了：

1. **文本处理**：文件扫描、文本清理、智能分块
2. **向量化**：使用Sentence Transformer将文本转换为向量
3. **索引构建**：使用FAISS构建高效的向量索引
4. **相似度检索**：根据查询检索最相关的文本片段

通过这些功能，系统能够从已有的优秀故事中学习，提高生成质量。

