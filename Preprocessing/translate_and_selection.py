import pandas as pd
from deep_translator import GoogleTranslator
from tqdm import tqdm
import os

# 启用 tqdm 支持 pandas apply 的进度条
tqdm.pandas()


def translate_text(text: str, translator: GoogleTranslator) -> str:
    if pd.isna(text) or not isinstance(text, str) or text.strip() == "":
        return ""
    try:
        return translator.translate(text)
    except Exception as e:
        print(f"翻译失败: {text[:30]}... => {e}")
        return ""


def translate_excel(input_path='batch/tasks_setting.xlsx', output_path='batch/tasks_translated.xlsx'):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"未找到输入文件: {input_path}")

    print(f"正在读取文件: {input_path}")
    df = pd.read_excel(input_path)

    if 'title' not in df.columns or 'description' not in df.columns:
        raise ValueError("Excel 文件中必须包含 'title' 和 'description' 列")

    translator = GoogleTranslator(source='auto', target='zh-CN')

    print("正在翻译 title 列...")
    df['title_zh'] = df['title'].progress_apply(lambda x: translate_text(x, translator))

    print("正在翻译 description 列...")
    df['description_zh'] = df['description'].progress_apply(lambda x: translate_text(x, translator))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_excel(output_path, index=False)
    print(f"\n✅ 翻译完成，结果已保存至: {output_path}")

if __name__ == "__main__":
    input_path = r'Preprocessing\output_batch\tasks_setting.xlsx'
    output_path = r'Preprocessing\output_batch\tasks_translated.xlsx'
    translate_excel(input_path,output_path)
