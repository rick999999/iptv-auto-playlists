import urllib.parse
import os
import sys
import re

try:
    import requests
except ImportError:
    print("[!] 错误：未安装 'requests' 库。")
    print("[!] 请执行以下命令安装：pip install requests")
    sys.exit(1)

# ==========================================
# EASYPROXY 通用配置及目录
# ==========================================
EASYPROXY_BASE_URL = ""

OUTPUT_DIR = os.getcwd()

# ==========================================
# DADDYLIVE 参数
# ==========================================
DADDY_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "daddylive.m3u")
DADDY_DOMAIN = "https://dlive.sx"
DADDY_CHANNELS_URL = f"{DADDY_DOMAIN}/24-7-channels.php"

# ==========================================
# LIVETV 参数（GitHub）
# ==========================================
LIVETV_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "livetv_master.m3u")
LIVETV_EPG_FILE = os.path.join(OUTPUT_DIR, "livetv_epg.xml.gz")

# LIVETV 仓库 Raw 文件基础地址
LIVETV_RAW_BASE_URL = "https://raw.githubusercontent.com/leanhhu061206/LIVETV/main"

LIVETV_SOURCES = [
    "dlhd.m3u",
    "eventi_dlhd.m3u",
    "sports99.m3u",
    "sportsonline.m3u",
    "static.m3u",
    "streamed.m3u",
    "vavoo.m3u",
    "world.m3u"
]

def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        print(f"[*] 正在创建输出目录：{OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_daddylive_channels():
    print(f"\n[DADDYLIVE] 正在从以下地址获取频道列表：{DADDY_CHANNELS_URL}")
    channels = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, come Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    try:
        response = requests.get(DADDY_CHANNELS_URL, headers=headers, timeout=15)
        if response.status_code == 200:
            html_content = response.text
            clean_html = re.sub(r'<br\s*/?>', '\n', html_content)
            clean_html = re.sub(r'<[^>]+>', ' ', clean_html)
            matches = re.finditer(r'([A-Za-z0-9\s\+\-\&]+?)\s+ID:\s*(\d+)', clean_html)

            for match in matches:
                channel_name = match.group(1).strip()
                channel_id = match.group(2).strip()
                channel_name = re.sub(r'\s+', ' ', channel_name)
                if len(channel_name) > 1 and channel_name.lower() != "all" and not channel_name.isspace():
                    if not any(c['id'] == channel_id for c in channels):
                        channels.append({'id': channel_id, 'name': channel_name})
            print(f"[DADDYLIVE] 成功获取 {len(channels)} 个频道。")
            return channels
        else:
            print(f"[DADDYLIVE] 获取频道列表失败，HTTP 状态码：{response.status_code}")
            return None

    except Exception as e:
        print(f"[DADDYLIVE] 获取频道列表时发生错误：{e}")
        return None

def generate_daddylive_m3u(channels):
    if not channels:
        print("[DADDYLIVE] 没有可用的频道，跳过 M3U 文件生成。")
        return

    print(f"[DADDYLIVE] 正在生成频道列表文件：{DADDY_OUTPUT_FILE}")

    try:
        with open(DADDY_OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for channel in channels:
                ch_id = channel.get("id", "")
                ch_name = channel.get("name", "频道")

                original_url = f"{DADDY_DOMAIN}/stream/stream-{ch_id}.php"
                encoded_url = urllib.parse.quote(original_url, safe='')
                proxy_url = f"{EASYPROXY_BASE_URL}/extractor/video?d={encoded_url}&redirect_stream=true"

                f.write(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-name="{ch_name}" group-title="DaddyLive",{ch_name}\n')
                f.write(f'{proxy_url}\n')

        print(f"[DADDYLIVE] 频道列表生成完成，共 {len(channels)} 个频道。")

    except IOError as e:
        print(f"[DADDYLIVE] 写入文件失败：{e}")

def process_livetv_sources():
    print(f"\n[LIVETV] 正在处理直播源...")
    out_lines = ["#EXTM3U"]
    success_count = 0

    for source in LIVETV_SOURCES:
        raw_url = f"{LIVETV_RAW_BASE_URL}/{source}"
        try:
            response = requests.get(raw_url, timeout=15)
            if response.status_code == 200:
                for line in response.text.splitlines():
                    line = line.strip()
                    if line.startswith("#"):
                        if not line.upper().startswith("#EXTM3U"):
                            out_lines.append(line)
                    elif line.startswith("http"):
                        encoded_url = urllib.parse.quote(line, safe='')
                        proxy_url = f"{EASYPROXY_BASE_URL}/proxy/manifest.m3u8?url={encoded_url}"
                        out_lines.append(proxy_url)

                success_count += 1
                print(f"[LIVETV] 已成功处理：{source}")
            else:
                print(f"[LIVETV] 获取失败：{source}，HTTP 状态码：{response.status_code}")

        except Exception as e:
            print(f"[LIVETV] 处理文件 {source} 时发生错误：{e}")

    try:
        with open(LIVETV_OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(out_lines) + "\n")

        print(f"[LIVETV] 直播源处理完成，成功获取 {success_count}/{len(LIVETV_SOURCES)} 个文件。")
        print(f"[LIVETV] 主播放列表已保存：{LIVETV_OUTPUT_FILE}")

    except IOError as e:
        print(f"[LIVETV] 写入播放列表失败：{e}")

def download_livetv_epg():
    epg_url = f"{LIVETV_RAW_BASE_URL}/epg.xml.gz"

    print(f"\n[LIVETV] 正在下载 EPG 电子节目单...")

    try:
        response = requests.get(epg_url, stream=True, timeout=20)

        if response.status_code == 200:
            with open(LIVETV_EPG_FILE, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            print(f"[LIVETV] EPG 下载完成：{LIVETV_EPG_FILE}")
        else:
            print(f"[LIVETV] EPG 下载失败，HTTP 状态码：{response.status_code}")

    except Exception as e:
        print(f"[LIVETV] 下载 EPG 时发生错误：{e}")

def main():
    print("==========================================")
    print("       IPTV 直播源自动更新程序")
    print("==========================================")

    ensure_output_dir()

    daddy_channels = fetch_daddylive_channels()

    if daddy_channels:
        generate_daddylive_m3u(daddy_channels)

    process_livetv_sources()
    download_livetv_epg()

    print("\n==========================================")
    print("           所有任务执行完毕")
    print("==========================================")

if __name__ == "__main__":
    main()
