# 广告短视频语义 clip 资产管线

基于阿里云百炼 Qwen-Omni 的**广告策略结构化分析工具 + 语义 clip 资产切分工具**。

不是普通关键帧抽取工具，也不是视频摘要工具，而是：

```
完整视频输入 Qwen-Omni
↓
拆解广告策略链路
↓
切分最小可复用 semantic_clip
↓
每个 clip 输出 clip.mp4 + keyframe.jpg + clip.json
↓
final_result.json 和 clip_index.json 只做索引
↓
后续可用于广告套路聚类、视觉元素库、AIGC 参考片段
```

## 竞品广告分析模式

新增 `competitor_image_analysis` 模式，用于分析竞品广告视频：

```
竞品视频输入 Qwen-Omni
↓
全局分析竞品广告策略
↓
拆解创意模块（不是 clip）
↓
提取原始元素提及（raw_element_mentions）
↓
抽取视觉手法关键帧（不是 clip.mp4）
↓
输出可入库的结构化洞察
```

此模式不生成 clip.mp4，不切分视频，只输出结构化分析记录。

## 核心概念

**semantic_clip** 是最小可复用语义视频片段。它可以是：

- 一个广告策略节点（opening_hook、pain_point、product_reveal、offer_price）
- 一个完整视觉动作（挤出膏体、涂抹脸颊、起泡、冲洗、展示赠品）
- 一个可独立复用的 AIGC 参考片段（产品特写、价格弹窗、明星背书）

每个 semantic_clip 输出到独立文件夹，包含：
- `clip.mp4` - 视频片段
- `keyframe.jpg` - 代表帧
- `clip.json` - 完整语义信息

## 当前不做

- 关键帧质检
- t-0.2 / t / t+0.2 候选帧
- 独立 ASR
- 独立 OCR
- 向量库
- 聚类实现
- Seedance 调用
- 多模型评测
- 大段 clip 和小 clip 双份视频存储
- 单独全局 keyframes 文件夹

## taxonomy 机制

本项目使用**半开放 taxonomy**：

- 每个关键标签尽量有 `raw_description` / `normalized_tag` / `new_candidate` / `confidence`
- `normalized_tag` 用于统计和聚类
- `raw_description` 用于保留模型理解
- `new_candidate` 用于后续扩展标签库

taxonomy 参考文件：`taxonomy/ad_taxonomy_v1.json`

## 安装

```bash
pip install -r requirements.txt
```

### ffmpeg

```bash
# Windows
scoop install ffmpeg
# 或 choco install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

## 配置

```bash
cp .env.example .env
```

编辑 `.env`：
```
DASHSCOPE_API_KEY=your_key
BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
BAILIAN_MODEL=qwen3.5-omni-plus
```

## 运行

```bash
# 使用 plus 模型（默认）
python main.py analyze \
    --video-id demo_001 \
    --video-url "https://example.com/ad.mp4" \
    --video-path "./samples/ad.mp4" \
    --output-dir "./outputs/demo_001"

# 使用 flash 模型
python main.py analyze \
    --video-id demo_001 \
    --video-url "https://example.com/ad.mp4" \
    --video-path "./samples/ad.mp4" \
    --model qwen3.5-omni-flash \
    --output-dir "./outputs/demo_001_flash"

# 只分析不切 clip（不传 --video-path）
python main.py analyze \
    --video-id demo_001 \
    --video-url "https://example.com/ad.mp4" \
    --output-dir "./outputs/demo_001"

# 竞品广告分析模式
python main.py competitor_image_analysis \
    --video-id competitor_001 \
    --video-url "https://example.com/competitor_ad.mp4" \
    --video-path "./samples/competitor_ad.mp4" \
    --output-dir "./outputs/competitor_001"
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--video-id` | 是 | 视频唯一标识 |
| `--video-url` | 是 | 公网视频 URL（百炼模型用） |
| `--video-path` | 否 | 本地视频路径（ffmpeg 切 clip/keyframe 用） |
| `--output-dir` | 否 | 输出目录（默认 ./outputs） |
| `--model` | 否 | qwen3.5-omni-plus 或 qwen3.5-omni-flash |

### 重要说明

- `video_url` 是给 Qwen-Omni 分析的，必须公网可访问
- `video_path` 是给 ffmpeg 本地切 clip/keyframe 的
- 没有 `video_path` 时，只会输出 JSON，不会生成 clips
- 如果百炼无法访问 video_url，需要先把视频上传到 OSS 或公网可访问地址

## 输出结构

### analyze 模式输出

```
outputs/{video_id}/
├── analysis_raw.json          # 模型原始输出
├── analysis_normalized.json   # 规范化后的完整分析
├── final_result.json          # 最终结果（只引用路径）
├── clip_index.json            # 轻量索引
├── logs/
│   └── run.log
└── clips/
    ├── 01_opening_hook_talking_head_hook/
    │   ├── clip.mp4
    │   ├── keyframe.jpg
    │   └── clip.json
    ├── 02_product_reveal_product_packaging_closeup/
    │   ├── clip.mp4
    │   ├── keyframe.jpg
    │   └── clip.json
    └── 03_offer_price_price_popup_with_presenter/
        ├── clip.mp4
        ├── keyframe.jpg
        └── clip.json
```

### competitor_image_analysis 模式输出

```
outputs/{video_id}/
├── analysis_raw.json              # 模型原始输出
├── global_analysis.json           # 全局竞品分析结果
├── final_result.json              # 轻量汇总
├── logs/
│   ├── run.log
│   └── debug_parse_failed.txt
├── records/
│   ├── video_record.jsonl         # 视频级入库预备记录
│   ├── module_record.jsonl        # 创意模块入库预备记录
│   ├── raw_element_mention.jsonl  # 原始元素提及记录
│   ├── frame_request.jsonl        # 关键帧请求记录
│   ├── frame_record.jsonl         # 实际关键帧记录
│   └── transfer_pattern_record.jsonl  # 可迁移模式记录
└── keyframes/
    ├── m_hook/
    │   ├── frame_001.jpg
    │   └── frame_002.jpg
    ├── m_price_offer/
    │   └── frame_001.jpg
    └── ...
```

## 项目结构

```
ad-video-pipeline/
├── README.md
├── requirements.txt
├── .env.example
├── main.py
├── generate_viewer.py
├── viewer.html
├── verify_competitor_outputs.py
├── prompts/
│   ├── video_analysis_prompt.txt
│   ├── global_element_agent.md
│   └── competitor_global_image_analysis.md
├── taxonomy/
│   └── ad_taxonomy_v1.json
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── bailian_client.py
│   ├── schemas.py
│   ├── video_analyzer.py
│   ├── global_element_pipeline.py
│   ├── competitor_global_pipeline.py
│   ├── clip_extractor.py
│   ├── keyframe_extractor.py
│   ├── json_utils.py
│   ├── logging_utils.py
│   └── filename_utils.py
├── samples/
│   └── *.mp4
└── outputs/
    └── {video_id}/
```

## 常见问题

**百炼无法访问 video_url**
- URL 必须公网可访问
- 不能有访问限制

**JSON 解析失败**
- 查看 `analysis_raw.json` 原始输出
- 查看 `debug_parse_failed.txt`

**timestamp 不准**
- 模型时间戳是估算值，可能有偏差

**ffmpeg 切 clip 失败**
- 确认 ffmpeg 已安装: `ffmpeg -version`
- 确认视频路径正确

**没有 video_path**
- 只输出 JSON，不切 clip 和 keyframe
