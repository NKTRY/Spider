#-*- coding:utf-8 -*-
from __future__ import unicode_literals
import sys,os
reload(sys)
sys.setdefaultencoding('utf-8')
import urllib2, re
from datetime import datetime

from bs4 import BeautifulSoup


BASE_URL = "http://www.nkzx.cn"


#Split Article Content From HTML
def get_content(html):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find('div', attrs={'class':'ct'}).string
    #Check article status
    try:
        article = Article.objects.get(title=title)
        return {"available": False}
    except:
        info = soup.find('div', align='center').string.replace(u'\xa0', '').split("|")
        pub_from = info[0].split("：")[1]
        pub_date = info[1].split("：")[1].split("-")
        #Rewrite content in HTML
        content = soup.find('div', attrs={'class':'content'}).get_text()
        result = "<p>信息来源：%s</p><p>" % pub_from
        description = ""
        for line in content.splitlines():
            if line.strip():
                if len(description) < 30:
                    description += line.strip()
                result += line.strip()+"</p><p>"
        content = result[:-3]
        if "正在建设" in content:
            return {"available": False}
        #Get Images
        imgs = soup.find('div', attrs={'class': 'content'}).findAll('img')
        for img in imgs:
            if not "http://" in img.get('src'):
                url = "http://www.nkzx.cn"+img.get('src')
            else:
                url = img.get('src')
            try:
                pic = urllib2.urlopen(url)
                filename = img.get('src').split("/")[-1]
                f = open("/alidata/www/Website-django/upload/img/Article/spider-%s" % filename, "wb")
                f.write(pic.read())
                f.close()
                content += '<img src="/media/img/Article/spider-%s">' % filename
            except:
                print url
        return {"title": title, "pub_date":pub_date, "content":content, "description":description, "available":True}


#Check & Insert
def save_to_django(title, text, parent_name, pub_date, description):
    parent = SecondaryMenu.objects.get(name=parent_name)
    author = CustomUser.objects.get(nickname="Admin")
    try:
        article = Article.objects.get(title=title)
    except:
        article = Article(title=title, text=text, author=author, pub_date=datetime(int(pub_date[0]), int(pub_date[1]), int(pub_date[2])), parent=parent, cover_img="img/Article/nkzx.png", description=description)
        article.save()


if __name__ == '__main__':
    #Get Website Banners
    response = urllib2.urlopen(BASE_URL+"/")
    html = response.read()
    soup = BeautifulSoup(html, "html.parser")
    banner = soup.find(id='banner').find(id='nav').findAll('li')
    banners = []
    for item in banner:
        if item.find('ul') == None:
            banners.append(item)
    banners = banners[1:]

    #Setup Environment
    sys.path.append('/alidata/www/Website-django/') 
    os.environ['DJANGO_SETTINGS_MODULE'] = 'nktc.settings' 
    from nktc import settings
    from frontend.models import Article, SecondaryMenu
    from accounts.models import CustomUser

    #Walk Banners & Collect Articles
    for li in banners:
        prefix = li.find('a').string
        parent_name = li.parent.parent.find('a').string
        href = li.find('a').get('href')
        print href
        response = urllib2.urlopen(BASE_URL+href)
        html = response.read()
        soup = BeautifulSoup(html, "html.parser")
        #Article or List?
        sign = soup.findAll('div')[-3]
        if sign.get('id') == 'items':
            #Deal List items
            ul_list = sign.findAll('ul')
            for ul in ul_list:
                href = ul.find('li').find('a').get('href')
                response = urllib2.urlopen(BASE_URL+href)
                html = response.read()
                result = get_content(html)
                if result["available"]:
                    save_to_django("[%s]%s" % (prefix, result["title"]), result["content"], parent_name, result["pub_date"], result["description"])
        else:
            result = get_content(html)
            if result["available"]:
                save_to_django("[%s]%s" % (prefix, result["title"]), result["content"], parent_name, result["pub_date"], result["description"])

