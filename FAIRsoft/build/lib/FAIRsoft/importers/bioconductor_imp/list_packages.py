from bs4 import BeautifulSoup
from bs4.dammit import EncodingDetector
import requests

session = requests.Session()
headers = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit 537.36 (KHTML, like Gecko) Chrome",
"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"}

def getHTML(url, verb=False):
    '''
    Takes and url as an input and returns the corresponding
    bs4 object
    '''
    
    try:
        re = session.get(url, headers=headers, timeout=(10, 30))
    except:
        print(r'Cannot access HTML')
        return(None)
    else:
        if re.status_code == 200:
            # dealing with encoding
            http_encoding = re.encoding if 'charset' in re.headers.get('content-type', '').lower() else None
            html_encoding = EncodingDetector.find_declared_encoding(re.content, is_html=True)
            encoding = html_encoding or http_encoding

            # generating BeautifulSoup object
            bsObj = BeautifulSoup(re.content, 'html5lib', from_encoding=encoding)

            if verb == True:
                print("The title of html is %s"%bsObj.title.getText())
            return(bsObj)
        else:
            return(None)

def get_whole_table():
    table_url = "https://bioconductor.org/packages/release/bioc/"
    packages_lst_html = getHTML(table_url) # bs4 object

    table = packages_lst_html.find("div", {"class":"do_not_rebase"})
    if len(table)>1:
        print("Warning: more than one table found")
        
    return(table)


def extract_name_url(table):
    bioc_url= 'https://bioconductor.org/packages/release/bioc/'
    all_packages = []
    for tag in table.tbody:
        a = tag.find('a')
        if a and a!=-1:
            #name = a.get_text()
            url = bioc_url + a['href']
            print(url)
            all_packages.append(url)
    
    return(all_packages)


def fetch_all_packages():
    table = get_whole_table()
    all_packages = extract_name_url(table)
    return(all_packages)

if __name__ == "__main__":
    packs = fetch_all_packages()
    with open("tmp/list_packages.txt", "w") as outfile:
        print("writing URLs to list")
        x = 1
        for p in packs:
            print("Package %d of %d"%(x, len(packs)), end='\r')
            outfile.write("%s\t%s\n"%(p, 'NA'))
            x += 1
