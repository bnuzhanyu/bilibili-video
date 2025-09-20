from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from loguru import logger
import os
import subprocess
import json


@dataclass
class DownloadItem:
    url: str
    author: str = None  # 设为可选参数，可以通过yt-dlp获取
    title: str = None   # 设为可选参数，可以通过yt-dlp获取
    start: int = None
    end: int = None

    def site(self):
        if 'bilibili.com' in self.url:
            return 'bilibili'
        elif 'youtube.com' in self.url:
            return 'youtube'
        else:
            return 'unknown'
    
    def is_collection(self):
        if self.site() == 'bilibili':
            return '/lists/' in self.url
        elif self.site() == 'youtube':
            return '&list=' in self.url or '/playlist?' in self.url
        else:
            return False

    def download_path(self):
        # 使用yt-dlp的格式化符获取作者和标题
        # 使用sanitize选项处理特殊字符，使用空格替换选项处理空格
        if self.is_collection():
            # 对于播放列表，使用上传者/播放列表标题/视频标题的结构
            return "%(uploader,sanitize)s/%(playlist_title,sanitize)s/%(title,sanitize)s.%(ext)s"
        else:
            # 对于单个视频，使用上传者/视频标题的结构
            return "%(uploader,sanitize)s/%(title,sanitize)s.%(ext)s"


@dataclass
class DownloadConfig:
    """下载配置类，用于集中管理下载参数"""
    output_dir: str = "./tmp_download"  # 下载目录
    concurrent_fragments: int = 4      # 单个视频的并行片段下载数
    max_playlist_concurrent: int = 4   # 播放列表的并行下载数
    best_quality: bool = False         # 是否下载最高画质
    quality: str = None                # 指定视频质量，如 "720p"
    skip_existing: bool = True         # 是否跳过已存在的文件
    download_subs: bool = False        # 是否下载字幕
    sub_langs: str = None              # 字幕语言，如 "en,zh-CN"
    max_workers: int = 5               # 多线程下载时的最大线程数
    use_proxy: str = None              # 代理服务器，如 "socks5://127.0.0.1:1080"
    referer: str = None                # HTTP Referer
    user_agent: str = None             # 自定义User-Agent
    sleep_interval: int = 0            # 下载间隔时间(秒)
    geo_bypass: bool = False           # 是否绕过地理位置限制


_VALID_SITES = ['bilibili', 'youtube']

_SITE_COOKIES = {}


def make_cookies_txt():
    from site_cookie import get_site_cookies
    for site in _VALID_SITES:
        try:
            cookie_file = f'/tmp/{site}_cookies.txt'
            get_site_cookies(site, cookie_file)
            _SITE_COOKIES[site] = cookie_file
        except Exception as e:
            logger.error(f"Error making cookies for {site}: {e}")


def download_from_item(item: DownloadItem, config: DownloadConfig):
    """使用配置对象下载单个项目"""
    os.makedirs(config.output_dir, exist_ok=True)
    cookie_file = _SITE_COOKIES.get(item.site())
    
    # 构建命令，使用yt-dlp的格式化符
    base_cmd = f"yt-dlp {item.url} -o \"{config.output_dir}/{item.download_path()}\""
    
    # 添加并行下载参数
    # -N/--concurrent-fragments: 并行下载片段数
    parallel_args = f" -N {config.concurrent_fragments}"
    
    # 如果是播放列表，添加播放列表相关参数
    # 注意：--concurrent-downloads 参数在某些版本中不可用
    # 我们可以使用 -P/--playlist-items 来限制下载范围
    playlist_args = ""
    if item.is_collection():
        # 不使用 --concurrent-downloads，而是使用其他方式优化播放列表下载
        # 例如，可以使用 --playlist-random 随机化下载顺序，减少服务器负载
        playlist_args = " --no-playlist-reverse"
    
    if item.start is not None and item.end is not None:
        playlist_args += f" --playlist-items {item.start}-{item.end}"
    
    # 添加画质选择参数
    quality_args = ""
    if config.quality:
        # 指定视频质量，例如 "720p"
        if config.quality == "720p":
            # 选择720p或最接近720p的视频质量
            quality_args = " -f \"bestvideo[height<=720]+bestaudio/best[height<=720]\""
        elif config.quality == "1080p":
            # 选择1080p或最接近1080p的视频质量
            quality_args = " -f \"bestvideo[height<=1080]+bestaudio/best[height<=1080]\""
        elif config.quality == "480p":
            # 选择480p或最接近480p的视频质量
            quality_args = " -f \"bestvideo[height<=480]+bestaudio/best[height<=480]\""
        else:
            # 直接使用用户指定的格式
            quality_args = f" -f \"{config.quality}\""
    elif config.best_quality:
        # 选择最佳视频和音频质量，并自动合并
        quality_args = " -f \"bestvideo+bestaudio/best\""
    
    # 添加跳过已存在文件的参数
    skip_args = ""
    if config.skip_existing:
        # --no-overwrites: 不覆盖已存在的文件
        # --download-archive: 记录已下载的视频ID，避免重复下载
        archive_file = os.path.join(os.path.dirname(__file__), ".download_archive.txt")
        skip_args = f" --no-overwrites --download-archive \"{archive_file}\""
    
    # 添加字幕下载参数
    subtitle_args = ""
    if config.download_subs:
        if config.sub_langs:
            # 指定字幕语言
            subtitle_args = f" --write-subs --write-auto-subs --sub-langs {config.sub_langs}"
        else:
            # 下载所有可用字幕和自动生成的字幕
            subtitle_args = " --write-subs --write-auto-subs --sub-langs all"
    
    # 添加防止403错误的参数
    anti_403_args = ""
    
    # 添加代理
    if config.use_proxy:
        anti_403_args += f" --proxy {config.use_proxy}"
    
    # 添加Referer
    if config.referer:
        anti_403_args += f" --referer {config.referer}"
    elif item.site() == 'bilibili':
        anti_403_args += " --referer https://www.bilibili.com/"
    elif item.site() == 'youtube':
        anti_403_args += " --referer https://www.youtube.com/"
    
    # 添加User-Agent
    # if config.user_agent:
    #     anti_403_args += f" --user-agent \"{config.user_agent}\""
    # else:
    #     # 使用常见浏览器的User-Agent
    #     default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    #     anti_403_args += f" --user-agent \"{default_ua}\""
    
    # 添加下载间隔
    if config.sleep_interval > 0:
        anti_403_args += f" --sleep-interval {config.sleep_interval}"
    
    # 添加地理位置绕过
    if config.geo_bypass:
        anti_403_args += " --geo-bypass"
    
    # 添加额外的错误处理参数
    anti_403_args += " --extractor-retries 5 --fragment-retries 5 --retry-sleep 5"
    
    if not cookie_file:
        cmd = base_cmd + parallel_args + playlist_args + quality_args + skip_args + subtitle_args + anti_403_args
    else:
        cmd = base_cmd + f" --cookies {cookie_file}" + parallel_args + playlist_args + quality_args + skip_args + subtitle_args + anti_403_args

    print(f"执行命令: {cmd}")
    subprocess.run(cmd, shell=True)


def download_from_url(url: str, config: DownloadConfig = None):
    """直接从URL下载，不需要预先知道作者和标题"""
    if config is None:
        config = DownloadConfig()
    
    item = DownloadItem(url=url)
    download_from_item(item, config)


def download_from_file(file: str, config: DownloadConfig = None):
    """从文件批量下载URL"""
    if config is None:
        config = DownloadConfig()
    
    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        with open(file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('http'):
                    parts = line.split()
                    url = parts[0]
                    url_parts =url.split('|')
                    url = url_parts[0]
                    start = None
                    end = None
                    if len(url_parts) > 1:
                        url = url_parts[0]
                        start = int(url_parts[1])
                        end = int(url_parts[2])
                    
                    # 如果提供了作者和标题，使用它们；否则让yt-dlp获取
                    if len(parts) >= 3:
                        author = parts[1]
                        title = parts[2]
                        item = DownloadItem(url=url, author=author, title=title, start=start, end=end)
                    else:
                        item = DownloadItem(url=url, start=start, end=end)
                    
                    # 多线程下载
                    executor.submit(download_from_item, item, config)


def list_video_info(url: str):
    """列出视频信息"""
    cmd = f"yt-dlp --dump-json {url}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    try:
        info = json.loads(result.stdout)
        print(f"标题: {info.get('title', 'N/A')}")
        print(f"上传者: {info.get('uploader', 'N/A')}")
        print(f"上传者ID: {info.get('uploader_id', 'N/A')}")
        print(f"时长: {info.get('duration_string', 'N/A')}")
        
        if info.get('playlist_title'):
            print(f"播放列表: {info.get('playlist_title', 'N/A')}")
    except json.JSONDecodeError:
        print("无法解析视频信息")
        print(result.stdout)


def list_video_formats(url: str):
    """列出视频可用的格式"""
    cmd = f"yt-dlp -F {url}"
    print(f"执行命令: {cmd}")
    subprocess.run(cmd, shell=True)


def list_available_subtitles(url: str):
    """列出视频可用的字幕"""
    cmd = f"yt-dlp --list-subs {url}"
    print(f"执行命令: {cmd}")
    subprocess.run(cmd, shell=True)


if __name__ == '__main__':
    make_cookies_txt()
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', type=str, help='视频列表文件')
    parser.add_argument('-u', '--url', type=str, help='视频URL')
    parser.add_argument('-d', '--dir', type=str, default='./tmp_download', help='下载目录')
    parser.add_argument('-i', '--info', action='store_true', help='只显示视频信息，不下载')
    parser.add_argument('-F', '--list-formats', action='store_true', help='列出可用的视频格式')
    parser.add_argument('-b', '--best', action='store_true', help='下载最高画质')
    parser.add_argument('-q', '--quality', type=str, default='720p', help='指定视频质量，如 "720p", "1080p", "480p" 或自定义格式')
    parser.add_argument('-s', '--skip-existing', action='store_true', default=True, help='跳过已存在的文件')
    parser.add_argument('-w', '--workers', type=int, default=3, help='同时下载的URL数量')
    parser.add_argument('-cf', '--concurrent-fragments', type=int, default=1, help='单个视频的并行片段下载数')
    parser.add_argument('-cp', '--concurrent-playlists', type=int, default=4, help='播放列表的并行下载数')
    parser.add_argument('--subs', action='store_true', help='下载字幕')
    parser.add_argument('--sub-langs', type=str, help='指定字幕语言，例如 "en,zh-CN"，默认下载所有语言')
    parser.add_argument('--list-subs', action='store_true', help='列出可用的字幕')
    # 添加防止403错误的参数
    parser.add_argument('--proxy', type=str, help='使用代理，例如 "socks5://127.0.0.1:1080"')
    parser.add_argument('--referer', type=str, help='设置HTTP Referer')
    parser.add_argument('--user-agent', type=str, help='设置User-Agent')
    parser.add_argument('--sleep', type=int, default=0, help='下载间隔时间(秒)')
    parser.add_argument('--geo-bypass', action='store_true', help='绕过地理位置限制')
    args = parser.parse_args()
    
    if args.info and args.url:
        list_video_info(args.url)
    elif args.list_formats and args.url:
        list_video_formats(args.url)
    elif args.list_subs and args.url:
        list_available_subtitles(args.url)
    else:
        # 创建下载配置
        config = DownloadConfig(
            output_dir=args.dir,
            concurrent_fragments=args.concurrent_fragments,
            max_playlist_concurrent=args.concurrent_playlists,
            best_quality=args.best,
            quality=args.quality,
            skip_existing=args.skip_existing,
            download_subs=args.subs,
            sub_langs=args.sub_langs,
            max_workers=args.workers,
            use_proxy=args.proxy,
            referer=args.referer,
            user_agent=args.user_agent,
            sleep_interval=args.sleep,
            geo_bypass=args.geo_bypass
        )
        
        if args.file:
            download_from_file(args.file, config)
        elif args.url:
            download_from_url(args.url, config)
        else:
            parser.print_help()