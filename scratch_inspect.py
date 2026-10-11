import yt_dlp
import yt_dlp.extractor.youtube._base as ytb

url = 'https://youtu.be/TzLN7FaorH0?si=eG2o8D0g4sJ6HOJG'

for client in ytb.INNERTUBE_CLIENTS.keys():
    print(f"Testing client: {client}...")
    opts = {
        'format': 'bestaudio/best',
        'simulate': True,
        'quiet': True,
        'extractor_args': {
            'youtube': {
                'player_client': [client],
                'player_skip': ['webpage']
            }
        }
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"===> SUCCESS WITH {client}! Title: {info.get('title')}")
            break
    except Exception as e:
        print(f"Failed with {client}: {str(e)[:80]}")
