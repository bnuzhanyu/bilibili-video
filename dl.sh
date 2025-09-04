
CUR_DIR=$(cd `dirname $0`; pwd)

url=$1
download_dir=./tmp_download
#url 包含 "lists"
if [[ $url == *"/lists/"* ]]; then
    dst="${download_dir}/%(uploader,sanitize)s/%(playlist_title,sanitize)s/%(title,sanitize)s.%(ext)s"
else
    # url按'】'分割，取最后一个
    url=$(echo $url | awk -F '】' '{print $NF}')
    dst="${download_dir}/%(uploader,sanitize)s/%(title,sanitize)s.%(ext)s"
fi

cookie_file=/tmp/cookie.txt
python $CUR_DIR/site_cookie.py -s bilibili -o $cookie_file
echo "url: $url"
yt-dlp $url -o "$dst" --cookies $cookie_file