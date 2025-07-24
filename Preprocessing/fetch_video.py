import asyncio
import aiohttp
import pandas as pd
import random
import os
import platform
import yaml
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Any
from tqdm.asyncio import tqdm


# ---------------- Config Loader ---------------- #
def load_config(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# ---------------- Data Classes ---------------- #
@dataclass
class YouTubeConfig:
    API_KEY: str
    CHANNELS: Dict[str, str]
    MAX_RESULTS: int
    VIDEO_FILTERS: Dict[str, int]
    BASE_URL: str = "https://www.googleapis.com/youtube/v3"


# ---------------- YouTube API Client ---------------- #
class YouTubeAPI:
    def __init__(self, config: YouTubeConfig):
        self.config = config
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    async def get_latest_videos(self, channel_id: str) -> List[Dict[str, Any]]:
        search_url = f"{self.config.BASE_URL}/search"
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "order": "date",
            "maxResults": self.config.MAX_RESULTS,
            "key": self.config.API_KEY,
        }

        async with self.session.get(search_url, params=params) as resp:
            data = await resp.json()
            if 'error' in data:
                print(f"[Error] {channel_id}: {data['error']['message']}")
                return []

        video_ids = [
            item["id"]["videoId"]
            for item in data.get("items", [])
            if item["id"]["kind"] == "youtube#video"
        ]

        if not video_ids:
            return []

        return await self.get_video_details(video_ids)

    async def get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        url = f"{self.config.BASE_URL}/videos"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": ",".join(video_ids),
            "key": self.config.API_KEY,
        }

        async with self.session.get(url, params=params) as resp:
            data = await resp.json()
            if 'error' in data:
                print(f"[Error] Fetching details: {data['error']['message']}")
                return []

        return [self.parse_video(item) for item in data.get("items", []) if self.parse_video(item)]

    def parse_video(self, item: Dict[str, Any]) -> Dict[str, Any] | None:
        try:
            duration = self.parse_duration(item['contentDetails'].get('duration', 'PT0S'))
            views = int(item['statistics'].get('viewCount', 0))
            comments = int(item['statistics'].get('commentCount', 0))

            filters = self.config.VIDEO_FILTERS
            if not (filters['MIN_DURATION'] <= duration <= filters['MAX_DURATION'] and
                    views >= filters['MIN_VIEWS'] and
                    comments >= filters['MIN_COMMENTS']):
                return None

            return {
                'videoId': item['id'],
                'title': item['snippet']['title'],
                'description': item['snippet']['description'].split('\n')[0],
                'publishedAt': item['snippet']['publishedAt'],
                'duration': duration,
                'viewCount': views,
                'commentCount': comments,
                'channel_name': item['snippet']['channelTitle'],
            }
        except Exception as e:
            print(f"[Parse Error] {e}")
            return None

    @staticmethod
    def parse_duration(iso_duration: str) -> int:
        import isodate
        try:
            duration = isodate.parse_duration(iso_duration)
            return int(duration.total_seconds())
        except Exception:
            return 0


# ---------------- Data Processor ---------------- #
class YouTubeDataProcessor:
    def __init__(self, videos: List[Dict[str, Any]]):
        self.df = pd.DataFrame([v for v in videos if v])

    def process(self) -> pd.DataFrame:
        if self.df.empty:
            return self.df

        self.df['Video File'] = 'https://www.youtube.com/watch?v=' + self.df['videoId']
        self.df['Source Language'] = 'en'
        self.df['Target Language'] = 'Chinese'
        self.df['Dubbing'] = 0
        self.df['Status'] = ''

        os.makedirs("batch", exist_ok=True)
        self.df.to_excel("batch/all_videos.xlsx", index=False)

        try:
            existing_df = pd.read_excel("batch/tasks_setting.xlsx")
            print(f"Found {len(existing_df)} existing entries.")
        except FileNotFoundError:
            existing_df = pd.DataFrame()
            print("No existing task file found.")

        selected_channels = random.sample(
            list(self.df['channel_name'].unique()), 
            min(5, len(self.df['channel_name'].unique()))
        )

        filtered_df = self.df[self.df['channel_name'].isin(selected_channels)]

        final_df = (
            filtered_df.sort_values(['channel_name', 'commentCount'], ascending=[True, False])
            .groupby('channel_name', group_keys=False)
            .apply(lambda x: x.sample(n=min(len(x.head(10)), random.randint(1, 5))))
            .reset_index(drop=True)
        )

        final_df.to_excel("batch/new_videos.xlsx", index=False)
        merged_df = pd.concat([existing_df, final_df], ignore_index=True).drop_duplicates(subset=['Video File'])

        return merged_df[[ 
            'Video File', 'title', 'description', 'viewCount', 'channel_name',
            'duration', 'Source Language', 'Target Language', 'Dubbing', 'Status'
        ]]


# ---------------- Main Execution ---------------- #
async def main():
    parser = argparse.ArgumentParser(description="Fetch and process YouTube channel videos.")
    parser.add_argument('--config', type=str, default='acc_config/wave_chaser.yaml', help='Path to YAML config file')
    parser.add_argument('--output', type=str, default='output_batch/tasks_setting.xlsx', help='Path to output Excel file')
    args = parser.parse_args()

    config_path = os.path.abspath(args.config)
    output_path = os.path.abspath(args.output)

    raw_config = load_config(config_path)
    config = YouTubeConfig(
        API_KEY=raw_config['API_KEY'],
        CHANNELS=raw_config['CHANNELS'],
        MAX_RESULTS=raw_config['MAX_RESULTS_PER_CHANNEL'],
        VIDEO_FILTERS=raw_config['VIDEO_FILTERS'],
    )

    print(f"Fetching data from {len(config.CHANNELS)} channels...")

    async with YouTubeAPI(config) as api:
        tasks = [api.get_latest_videos(cid) for cid in config.CHANNELS.values()]
        all_results = await asyncio.gather(*tasks)
        all_videos = [video for group in all_results for video in group]

    processor = YouTubeDataProcessor(all_videos)
    result_df = processor.process()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    result_df.to_excel(output_path, index=False)
    print(f"✅ Saved {len(result_df)} videos to: {output_path}")


if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
