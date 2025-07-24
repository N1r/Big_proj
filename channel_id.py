import requests

def get_channel_id(api_key: str, channel_name: str) -> str:
    """Get YouTube channel ID from channel name"""
    base_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'id',
        'q': channel_name,
        'type': 'channel',
        'key': api_key
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        if data['items']:
            return data['items'][0]['id']['channelId']
        return ""
    except Exception as e:
        print(f"Error: {e}")
        return ""

if __name__ == "__main__":
    API_KEY = "AIzaSyABmSbMC15Uf0xVn6NWzNpUG9b9l3a5yaY"  # Replace with your API key
    
    channels = [
        'dwnews',
        'BBCNews',
        'aljazeeraenglish',
        'themoverandgonkyshow']
    
    print("Fetching channel IDs...\n")
    
    for name in channels:
        channel_id = get_channel_id(API_KEY, name)
        if channel_id:
            print(f"'{name}': '{channel_id}',")
        else:
            print(f"# Failed to fetch ID for {name}")