import os
import shutil
import yaml
import requests
import random
from datetime import datetime, timedelta
from tqdm import tqdm

# 配置常量 # 主要控制变量
OUTPUT_DIR = '../Videolingo/batch/output'

COVER_SUFFIX = '.jpg'
VIDEO_SUFFIX = '.webm'
FONT_PATH = "Fonts/msyhbd.ttc"
YAML_OUTPUT_FILE = 'style/config_bili.yaml'
TAG = '时装周,Fashion Week,高级定制,T台秀,设计师品牌,奢侈品,潮流,时尚'

# API 配置
API_KEY = 'sk-2hQb4lo4JuCdWWCflcN41jddIIQzhtSi78Qeb7vWOM40XSkJ'
API_BASE_URL = 'https://api.302.ai'
API_MODEL = 'gemini-2.0-flash'

def clear_error_dir():
    """删除 output/ERROR 目录"""
    error_dir = os.path.join(OUTPUT_DIR, 'ERROR')
    if os.path.exists(error_dir):
        shutil.rmtree(error_dir)
        print(f"已删除 {error_dir}")
    else:
        print(f"{error_dir} 不存在")

def find_files_with_suffix(directory: str, suffix: str) -> list:
    """查找指定目录下特定后缀的文件"""
    return [
        os.path.join(root, file)
        for root, _, files in os.walk(directory)
        for file in files if file.endswith(suffix)
    ]

def translate_title(text: str) -> str:
    """使用 API 翻译并生成时尚标题"""
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        prompt = '''
                    
            ---

            你是一位专业的时尚内容创作专家，擅长为Z世代用户打造具有**视觉冲击力与话题引导力**的**时尚视频标题**，发布平台为**B站**，适用于Vlog/秀场/测评/解析类内容。

            ---

            ## 核心任务

            将英文品牌名和基础标题内容，优化为**B站爆款时尚标题**，具备**传播力、高级感和年轻人共鸣点**。

            ---

            ## 标题要求（更新版）

            ### 必须包含元素

            * **品牌英文名** + 关键词（视觉风格/设计亮点/系列名等）
            * **热门话题标签**：#时装周 #高定现场 #爆款预定 等，仅限1-2个
            * **情绪共鸣词**：绝美、封神、太会了、神级细节、高阶感爆棚、氛围感拉满
            * **趋势/风格标签**：如 老钱风、冷感穿搭、哥特甜妹、美拉德风 等

            ---

            ## 推荐结构模版（优化后）

            1. **沉浸式直击型**
            `[秀场直击] 品牌名 + 系列亮点 + 情感词 + 热门话题`

            2. **视觉种草型**
            `[高能种草] 品牌名 + 设计风格/关键词 + 共鸣感词 + 话题标签`

            3. **解析引导型**
            `[时尚解析] 品牌名 + 风格演化/趋势趋势 + 高级形容词 + 互动引导词`

            > 示例：Miu Miu 的“甜酷学院风”为啥成顶流？| 时尚解析

            ---
            ## 语言风格
            * 富有**画面感与情绪感**，具备B站年轻人熟悉的“高感知语言”
            * 保持**专业审美**同时注重传播效率
            * **控制在18-26字内**，不出现生硬直译
            ---

            ## 输出格式

            **只返回最终优化标题**，不提供解释、不生成备选项。如标题含数据或品牌专属词汇，务必保持准确。
            ---
            '''
        payload = {
            "model": API_MODEL,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }
        resp = requests.post(f"{API_BASE_URL}/v1/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[翻译失败] {text} => {e}")
        return text  # fallback 使用原文本

def generate_titles(video_paths: list) -> list:
    """从视频路径中提取文件夹名并翻译为标题"""
    titles = []
    for path in tqdm(video_paths, desc="生成标题"):
        folder = os.path.basename(os.path.dirname(path))
        translated = translate_title(folder)
        titles.append(translated or folder)
    return titles

def generate_publish_timestamps(video_count: int) -> list:
    """生成按天分配的 19:00/20:00/21:00 发布时间"""
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    total_days = -(-video_count // 3)  # 向上取整
    timestamps = []

    for day in range(total_days):
        base_day = start_date + timedelta(days=day)
        for hour in [19, 20, 21]:
            timestamps.append(int(base_day.replace(hour=hour).timestamp()))

    return timestamps[:video_count]

def create_yaml_config(videos, covers, titles, dtimes):
    """根据数据生成 YAML 配置文件"""
    yaml_data = {
        "limit": 1,
        "streamers": {
            video: {
                "copyright": 2,
                "source": None,
                "no_reprint": 1,
                "tid": 207,
                "cover": cover,
                "title": title,
                "desc_format_id": 0,
                "desc": "喜欢的话就狠狠地点个赞吧！也别忘了分享给志同道合的朋友～如果你也喜欢这类风格，记得收藏关注一下！家人们的支持就是我持续更新的“充电宝”，你们每一个点赞留言我都认真看！❤️",
                "dolby": 1,
                "lossless_music": 1,
                "tag": TAG,
                "dynamic": "",
                "dtime": dtime
            } for video, cover, title, dtime in zip(videos, covers, titles, dtimes)
        }
    }

    try:
        with open(YAML_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_data, f, allow_unicode=True, sort_keys=False)
        print(f"✅ YAML 配置已保存到 {YAML_OUTPUT_FILE}")
    except Exception as e:
        print(f"保存 YAML 出错: {e}")

def main():
    clear_error_dir()

    videos = find_files_with_suffix(OUTPUT_DIR, VIDEO_SUFFIX)
    covers = find_files_with_suffix(OUTPUT_DIR, COVER_SUFFIX)
    
    if not videos:
        print("❌ 未找到任何视频文件")
        return

    titles = generate_titles(videos)
    dtimes = generate_publish_timestamps(len(videos))
    create_yaml_config(videos, covers, titles, dtimes)

if __name__ == "__main__":
    main()
