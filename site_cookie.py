import requests

# 构建请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com/',
    'Accept': 'application/json, text/plain, */*',
    'Connection': 'keep-alive',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
}

def get_bilibili_cookies(cookie_path='bilibili_cookies.txt'):
    # 创建会话
    session = requests.Session()
    
    # 尝试访问B站首页
    print("访问B站首页...")
    resp = session.get("https://www.bilibili.com/", headers=headers)
    print(f"状态码: {resp.status_code}")
    
    # 打印请求后session中的cookies
    print("\n请求后session中的cookies:")
    for cookie in session.cookies:
        print(f"{cookie.name}: {cookie.value}")
    
    # 将cookies转换为字典格式
    cookies_dict = requests.utils.dict_from_cookiejar(session.cookies)
    
    # 构建headers中的Cookie字段
    cookie_header = '; '.join([f"{name}={value}" for name, value in cookies_dict.items()])
    print("\nHeaders中的Cookie字段格式:")
    print(cookie_header)
    
    # 将Cookie保存为Netscape格式的cookies.txt文件
    with open(cookie_path, 'w') as f:
        f.write('# Netscape HTTP Cookie File\n')
        for cookie in session.cookies:
            # 构建cookies.txt的每一行
            line = f"{cookie.domain}\tTRUE\t{cookie.path}\tFALSE\t{cookie.expires}\t{cookie.name}\t{cookie.value}\n"
            f.write(line)
    print(f"Cookie已导出到 {cookie_path}")
    
    return session.cookies

def get_youtube_cookies(cookie_path='youtube_cookies.txt'):
    # 创建会话
    session = requests.Session()
    
    # 为YouTube定制的请求头
    youtube_headers = headers.copy()
    youtube_headers['Referer'] = 'https://www.youtube.com/'
    
    # 尝试访问YouTube首页
    print("访问YouTube首页...")
    resp = session.get("https://www.youtube.com/", headers=youtube_headers)
    print(f"状态码: {resp.status_code}")
    
    # 打印请求后session中的cookies
    print("\nYouTube请求后session中的cookies:")
    for cookie in session.cookies:
        print(f"{cookie.name}: {cookie.value}")
    
    # 将cookies转换为字典格式
    cookies_dict = requests.utils.dict_from_cookiejar(session.cookies)
    
    # 构建headers中的Cookie字段
    cookie_header = '; '.join([f"{name}={value}" for name, value in cookies_dict.items()])
    print("\nYouTube Headers中的Cookie字段格式:")
    print(cookie_header)
    
    # 将Cookie保存为Netscape格式的cookies.txt文件
    with open(cookie_path, 'w') as f:
        f.write('# Netscape HTTP Cookie File\n')
        for cookie in session.cookies:
            # 构建cookies.txt的每一行
            line = f"{cookie.domain}\tTRUE\t{cookie.path}\tFALSE\t{cookie.expires}\t{cookie.name}\t{cookie.value}\n"
            f.write(line)
    print(f"YouTube Cookie已导出到 {cookie_path}")
    
    return session.cookies

def get_site_cookies(site_type, cookie_path=None):
    """
    获取指定网站的cookies并保存到指定路径
    
    参数:
        site_type: 网站类型，'bilibili'或'youtube'
        cookie_path: cookies保存路径，如果为None则使用默认路径
    
    返回:
        cookies对象
    """
    if site_type.lower() == 'bilibili':
        path = cookie_path if cookie_path else 'bilibili_cookies.txt'
        return get_bilibili_cookies(path)
    elif site_type.lower() == 'youtube':
        path = cookie_path if cookie_path else 'youtube_cookies.txt'
        return get_youtube_cookies(path)
    else:
        print(f"不支持的网站类型: {site_type}")
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='获取网站cookies')
    parser.add_argument('--site', '-s', choices=['bilibili', 'youtube'], required=True, help='指定网站类型')
    parser.add_argument('--output', '-o', help='指定cookies保存路径')
    
    args = parser.parse_args()
    
    get_site_cookies(args.site, args.output)
