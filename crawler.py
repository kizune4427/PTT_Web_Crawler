import urllib.request as req
from urllib.parse import urljoin
import json
import bs4
import csv
import re

main_url = "https://www.ptt.cc/bbs/C_Chat/index.html"

# build a request object with headers information
request = req.Request(main_url, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36"
})

print("request successfully")

with req.urlopen(request) as response:
    mainPage = response.read().decode("utf-8")

# get the title url list with mainPage
root = bs4.BeautifulSoup(mainPage, "html.parser")


def is_chinese(uchar, punctuation=True):
    punc_list = [u"\uff0c", u"\u3002", u"\uff1f", u"\uff01",
                 u"\u002c", u"\u002e", u"\u003f", u"\u0021"]  # ，。？！, . ?!
    if punctuation:
        return uchar in punc_list or (uchar >= u"\u4e00" and uchar <= u"\u9fa5")
    return (uchar >= u"\u4e00" and uchar <= u"\u9fa5")


def between(current, end):
    """Extract content between tags."""
    text_list = []

    while current and current != end:
        if isinstance(current, bs4.NavigableString):
            text = current.strip()
            if text:
                texts = text.split("\n")
                for text in texts:
                    content_str = ''
                    for c in text:
                        if is_chinese(c):
                            content_str += c
                    text_list.append(content_str)

        current = current.next_element
    return text_list


# locate the current page number
target_div = root.find('div', id="main-container").find('div', id="action-bar-container").find(
    'div', class_="action-bar").find('div', class_="btn-group btn-group-paging")
page_url = target_div.find('a', text=re.compile("上頁")).get('href')
page_num = 1 + int(re.compile(r"\d+").search(page_url).group(0))

# Store info of every existing post
pttDict = {}


def get_pages(n_pages=1, all=False):
    global page_num
    """get contents of the requested pages"""
    if all:
        target_page = 0
    else:
        target_page = page_num - n_pages

    while(page_num > target_page):
        tail_url = "index" + str(page_num) + ".html"
        current_url = urljoin(main_url, tail_url)

        request = req.Request(current_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.116 Safari/537.36"})

        with req.urlopen(request) as response:
            currentPage = response.read().decode("utf-8")

        # get the title url list with mainPage
        root = bs4.BeautifulSoup(currentPage, "html.parser")

        # find the div where title url sits in
        divs = root.find_all("div", class_="title")
        post_url_list = []
        for div in divs:
            if div.a:
                post_url_list.append(div.a.get('href'))

        # view each of the post on the page
        for post_url in post_url_list:
            request = req.Request(urljoin(main_url, post_url), headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36"
            })

            with req.urlopen(request) as response:
                post = response.read().decode("utf-8")

            root = bs4.BeautifulSoup(post, "html.parser")

            post_info = {}  # for one post

            # extract the information needed
            title = ""
            values = []  # author, date, content

            divs = root.find_all('div', class_="article-metaline")
            for div in divs:
                span = div.find('span', class_="article-meta-value")
                values.append(span.get_text())

                if div.find('span', class_="article-meta-tag", text="時間"):
                    contents = between(
                        div.next_sibling, root.find('span', class_='f2', text=re.compile("^※ 發信站")))
                    text_data = ''.join(contents)

                    values.append(text_data)

            if values:
                post_info['author'] = values[0]
                if "[公告]" in values[1] or "[板務]" in values[1]:
                    continue
                else:
                    title = values[1]

                post_info['date'] = values[2]
                post_info['content'] = values[3]

            pttDict[title] = post_info

        with open("c_chat_crawl.json", "w", encoding='utf-8') as f:
            json.dump(pttDict, f, indent=4, ensure_ascii=False)

        print("# " + str(page_num) + " finished")
        page_num -= 1

    print("Complete!")


get_pages(3)


# json to csv
with open("c_chat_crawl.json", 'r', encoding='utf-8') as jsonFile:
    data = json.load(jsonFile)


with open("c_chat_crawl.csv", 'w', encoding='utf-8') as f:
    csv_file = csv.writer(f)
    csv_file.writerow(['Date', 'Author', 'Content'])

    for item in data.values():
        csv_file.writerow(
            [item.get("date"), item.get("author"), item.get("content")])
