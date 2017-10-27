# coding: utf8

import sys
import requests
import re
import json
import functools
import logging
import time

# 主页地址
BASE_URL = "http://music.163.com"

# 分类列表
CATEGORY_LIST = {
    "语种": ["华语", "欧美", "日语", "韩语", "粤语", "小语种"],
    "风格": ["流行", "摇滚", "民谣", "电子", "舞曲", "说唱",
           "轻音乐", "爵士", "乡村", "R&B/Soul", "古典", "民族",
           "英伦", "金属", "朋克", "蓝调", "雷鬼", "世界音乐",
           "拉丁", "另类/独立", "New Age", "古风", "后摇", "Bossa Nova"],
    "场景": ["清晨", "夜晚", "学习", "工作", "午休", "下午茶",
           "地铁", "驾车", "运动", "旅行", "散步", "酒吧"],
    "情感": ["怀旧", "清新", "浪漫", "性感", "伤感", "治愈",
           "放松", "孤独", "感动", "兴奋", "快乐", "安静", "思念"],
    "主题": ["影视原声", "ACG", "校园", "游戏", "70后", "80后",
           "90后", "网络歌曲", "KTV", "经典", "翻唱", "吉他",
           "钢琴", "器乐", "儿童", "榜单", "00后"]
}

# 抓取的分类
CATEGORY = "古风"

# 该分类下抓取几页，一页下默认取35个歌单
PAGES = 1
LIMIT = 10


# 一首歌曲的相关信息
class SongInfo:
    def __init__(self, song_id, song_name, comment_count):
        self._song_id       = song_id
        self._song_name     = song_name
        self._comment_count = comment_count

    def __str__(self):
        song_addr = BASE_URL + "/song?id=" + self._song_id
        return "[" + str(self._comment_count) + "]" \
               + "[" + self._song_name + "]" \
               + "[ " + song_addr + " ]"

    def get_song_id(self):
        return self._song_id

    def get_song_name(self):
        return self._song_name

    def get_comment_count(self):
        return self._comment_count

    def set_comment_count(self, count):
        self._comment_count = count


# 用于按照歌曲评论数排序的比较方法
def my_cmp(s1, s2):
    return s1.get_comment_count() - s2.get_comment_count()


# 从一个指定字符串中搜寻所有指定的正则串
def get_list_from_str(search_str, pattern):
    # 返回所有能匹配的串
    match = pattern.findall(search_str)

    # 将list去重
    match = list(set(match))

    result = []
    if match:
        for one_str in match:
            result.append(one_str)
    else:
        print("nothing matched!")

    return result


# 从json串里解析歌曲详细信息
def parse_song_list(song_json_str):
    song_info = json.loads(song_json_str)
    result = []
    for item in song_info:
        # 暂时只取id和name，json串里还有很多信息待获取
        one_song = SongInfo(str(item['id']), item['name'], 0)
        result.append(one_song)

    return result


# 获取歌单列表
def get_playlist_list(page, limit):
    if page < 1:
        page = 1

    if limit < 1:
        limit = 10
    offset = limit * (page - 1)

    # 获取歌单列表的页面
    addr = BASE_URL\
           + "/discover/playlist/?order=hot"\
           + "&cat=" + CATEGORY \
           + "&limit=" + str(limit)\
           + "&offset=" + str(offset)
    rsp = requests.get(addr)

    # 歌单列表页面get到的响应结果里，歌单地址的正则表达式如下
    # href="(/playlist\?id=[0-9]+)"，例如href="/playlist?id=771087552"
    pattern = re.compile(r'href="(/playlist\?id=[0-9]+)"', re.IGNORECASE)

    return get_list_from_str(str(rsp.content), pattern)


# 获取一个歌单下的所有歌曲
def get_song_list(short_addr):
    # 得到歌单地址
    long_addr = BASE_URL + short_addr
    # 获取歌单页面
    rsp = requests.get(long_addr)

    #歌单页面中，每首歌曲的地址的正则表达式如下
    # href="(/song\?id=[0-9]+)"，例如href="/song?id=410042089"
    # 仅匹配歌曲ID
    # pattern = re.compile(r'href="(/song\?id=[0-9]+)"', re.IGNORECASE)
    # 匹配歌曲ID和歌曲名称
    #pattern = re.compile(r'<a href="(/song\?id=[0-9]+)">([\S]+)</a>', re.IGNORECASE)

    # 上边的正则表达式可能无法匹配部分歌名含有空格的歌曲
    # 通过分析网页，尝试匹配其它的串
    # 下边的正则表达式匹配到的是json串
    pattern = re.compile(r'<textarea style="display:none;">(.*)</textarea>', re.IGNORECASE)

    song_list = get_list_from_str(str(rsp.content, encoding='utf8'), pattern)
    if song_list:
        # song_list[0]里是所有歌曲信息的json串
        return parse_song_list(song_list[0])

    return None


# 获取歌曲评论
def get_comment_of_song_list(song_list):
    for item in song_list:
        # 获取歌曲id
        song_id = item.get_song_id()

        #  拼接获取歌曲评论的url
        song_comment_url = BASE_URL + "/weapi/v1/resource/comments/R_SO_4_" + song_id + "?csrf_token="

        # 设置获取歌曲评论的http post请求的body
        # 通过浏览器F12分析使用该固定body
        body = {
           "params": "GLsSGlzNTKtU/d1tGkmyRlJ6S78e3NjofHQTfb9Wulfw4DJL0w4hEnnxhqL4lMmkWKakz2Z/ruqwcFyOzCHcKREXf7wL+/9QXMa/41rskB5JkDkLuIB7EroLjUde+CrjyXrh3rnlVEJaQyDMuJaforJqEe3aYVICuNXgMtAeKzQhimDJANE5IEAhZHEdyaE+",
           "encSecKey": "cea19266047c711c83e68f2f4c26839ca2dcf400f648b09d99d5161a8483b8d6e3985f286f8771b40cd8bcb2036dfaf257eebc8b859b6cd665ec0c3150e00aa1f78e9471668d473c3359d45b1e9d0e602e978427392089df29f739a21ae3feb2f98205282653642c789e3eb6982c0386b4a5f5e850984e0bfd07efd074329f2c"
        }

        rsp = requests.post(song_comment_url, body)
        if rsp:
            result = json.loads(str(rsp.content, encoding='utf8'))
            if result:
                item.set_comment_count(result["total"])


def run(page, limit):
    # 1. 第一步获取歌单列表页面下的每个歌单的id
    # 2. 第二步获取一个歌单页面下的每首歌曲的id和name
    # 3. 第三步获取每首歌曲的评论数

    logging.info("获取歌单列表...")
    playlist_list = get_playlist_list(page, limit)

    all_song = []
    if playlist_list:
        logging.info("已获取歌单列表，个数=" + str(len(playlist_list)))

        for one_str in playlist_list:
            # 获取歌单下的歌曲列表
            logging.info("获取歌单下的歌曲列表...[ " + BASE_URL + one_str + " ]")
            song_list = get_song_list(one_str)
            logging.info("已获取歌单下的歌曲列表，个数=" + str(len(song_list)))

            logging.info("获取歌单下所有歌曲的评论...")
            get_comment_of_song_list(song_list)
            logging.info("已获取歌单下所有歌曲的评论")

            if song_list:
                logging.info("排序一个歌单下的所有歌曲...")
                # sorted(all_song, key=functools.cmp_to_key(my_cmp))
                song_list.sort(key=functools.cmp_to_key(my_cmp), reverse=True)
                logging.info("已排序")

                #for item in song_list:
                #    logging.info(item)
                all_song.extend(song_list)

            # 抓完一个歌单后，睡1s
            logging.info("sleep 1")
            time.sleep(1)
    else:
        print("no playlist found!")

    if all_song:
        logging.info("排序所有歌曲...")
        all_song.sort(key=functools.cmp_to_key(my_cmp), reverse=True)
        logging.info("已排序")
        for item in all_song:
            logging.info(item)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s][%(filename)s:%(lineno)d][%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    for i in range(PAGES):
        # 指定访问第几页，每页几个歌单
        run(i + 1, 3)
