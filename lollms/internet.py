from ascii_colors import ASCIIColors, trace_exception
from lollms.utilities import PackageManager
import time
import re

def get_favicon_url(url):
    import requests
    from bs4 import BeautifulSoup
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        favicon_link = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
        
        if favicon_link:
            favicon_url = favicon_link['href']
            if not favicon_url.startswith('http'):
                favicon_url = url + favicon_url
            return favicon_url
    except:
        ASCIIColors.warning(f"Couldn't get fav icon from {url}")
    return None


def get_root_url(url):
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    root_url = parsed_url.scheme + "://" + parsed_url.netloc
    return root_url


def format_url_parameter(value:str):
    encoded_value = value.strip().replace("\"","").replace(" ","+")
    return encoded_value


def wait_for_page(driver, step_delay=1):
    # Get the initial page height
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        # Scroll to the bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait for the page to load new content
        time.sleep(step_delay)
        
        # Get the new page height
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        # If the page height hasn't changed, exit the loop
        if new_height == last_height:
            break
        
        last_height = new_height


def prepare_chrome_driver(chromedriver_path = None):
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    # Create a new instance of the Chrome driver
    chrome_options = webdriver.ChromeOptions()
    #chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode
    # chrome_options.add_argument('--ignore-certificate-errors')
    # chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument("--enable-third-party-cookies")

    # Set path to chromedriver executable (replace with your own path)
    if chromedriver_path is None: 
        chromedriver_path = ""#"/snap/bin/chromium.chromedriver"    

    # Create a new Chrome webdriver instance
    try:
        driver = webdriver.Chrome(executable_path=chromedriver_path, options=chrome_options)
    except:
        driver = webdriver.Chrome(options=chrome_options)    
    return driver

def press_buttons(driver, buttons_to_press=['accept']):
    from selenium.webdriver.common.by import By
    from bs4 import BeautifulSoup

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find the button that contains the text "accept" (case-insensitive)
    for button_to_press in buttons_to_press.split(",") if isinstance(buttons_to_press, str) else buttons_to_press:
        try:
            button_to_press = button_to_press.strip()
            button = soup.find('button', text=lambda t: button_to_press in t.lower())

            if button:
                # Click the button using Selenium
                button_element = driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]")
                button_element.click()
                print(f"Button {button_to_press} clicked!")
            else:
                print(f"Button {button_to_press} not found in page.")
        except:
            ASCIIColors.warning(f"Couldn't press button {button_to_press} in this page.")

def scrape_and_save(url, file_path=None, lollms_com=None, chromedriver_path=None, wait_step_delay=1, buttons_to_press=['accept'], max_size=None):
    if not PackageManager.check_package_installed("selenium"):
        PackageManager.install_package("selenium")
    if not PackageManager.check_package_installed("bs4"):
        PackageManager.install_package("bs4")

    from bs4 import BeautifulSoup
        
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException
    
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    driver = prepare_chrome_driver(chromedriver_path)

    # Navigate to the URL
    driver.get(url)
    wait_for_page(driver, wait_step_delay)
    press_buttons(driver, buttons_to_press)

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Find all the text content in the webpage
    text_content = soup.get_text()
    text_content = re.sub(r'\n+', '\n', text_content)

    
    if file_path:
        if max_size and len(text_content)< max_size:
            # Save the text content as a text file
            with open(file_path, 'w', encoding="utf-8") as file:
                file.write(text_content)
            if lollms_com:
                lollms_com.info(f"Webpage content saved to {file_path}")
            
    # Close the driver
    driver.quit()


    return text_content


def get_relevant_text_block(
    url,
    driver,
    internet_vectorization_chunk_size,
    internet_vectorization_overlap_size,
    vectorizer,
    title=None,
    brief=None,
    wait_step_delay=0.5,
    query="",
    asses_using_llm=True,
    yes_no=None
):
    from bs4 import BeautifulSoup
    import time
    try:
        # Chargez la page web avec le driver passé en paramètre
        driver.get(url)
        # Attendez que le JavaScript s'exécute, avec un délai d'attente progressif si nécessaire
        time.sleep(wait_step_delay)
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, "html.parser")

        # Supprimez les éléments non désirés
        for script_or_style in soup(["script", "style", "header", "footer", "nav", "aside"]):
            script_or_style.decompose()

        # Ciblez l'élément contenant le texte principal
        article = soup.find('article')
        if article:
            text_block = ''
            sections = article.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li'])
            for element in sections:
                if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    if text_block:
                        text_block += '\n\n'
                    text_block += element.get_text(strip=True)
                    text_block += '\n'
                else:
                    text_block += element.get_text(strip=True) + '\n'

            document_id = {
                'url':url
            }
            document_id["title"] = title
            document_id["brief"] = brief
            text_block=text_block.strip()
            if asses_using_llm and yes_no is not None:
                if yes_no(f"Is this content relevant to the query: {query}", text_block):
                    vectorizer.add_document(document_id,text_block, internet_vectorization_chunk_size, internet_vectorization_overlap_size)
            else:
                vectorizer.add_document(document_id,text_block, internet_vectorization_chunk_size, internet_vectorization_overlap_size)
            return True
        else:
            body = soup.body
            if body:
                text_block = body.get_text(strip=True)
                document_id = {
                    'url':url
                }
                document_id["title"] = title
                document_id["brief"] = brief
                text_block=text_block.strip()

                vectorizer.add_document(document_id,text_block, internet_vectorization_chunk_size, internet_vectorization_overlap_size)
                return True
            else:
                ASCIIColors.warning("No data found in his page.")
                return False
    except Exception as ex:
        ASCIIColors.warning(f"Couldn't scrape: {url}")
        return False
        


def extract_results(url, max_num, driver=None, wait_step_delay=0.5):
    from bs4 import BeautifulSoup    

    # Load the webpage
    driver.get(url)

    # Get the initial page height
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    wait_for_page(driver, wait_step_delay)

    # Wait for JavaScript to execute and get the final page source
    html_content = driver.page_source

    # Parse the HTML content
    soup = BeautifulSoup(html_content, "html.parser")

    # Detect that no outputs are found
    Not_found = soup.find("No results found")

    if Not_found : 
        return []    

    # Find the <ol> tag with class="react-results--main"
    ol_tag = soup.find("ol", class_="react-results--main")

    # Initialize an empty list to store the results
    results_list = []

    try:
        # Find all <li> tags within the <ol> tag
        li_tags = ol_tag.find_all("li")

        # Loop through each <li> tag, limited by max_num
        for index, li_tag in enumerate(li_tags):
            if index > max_num*3:
                break

            try:
                # Find the three <div> tags within the <article> tag
                div_tags = li_tag.find_all("div")

                # Extract the link, title, and content from the <div> tags
                links = div_tags[0].find_all("a")
                href_value = links[1].get('href')
                span = links[1].find_all("span")
                link = span[0].text.strip()

                title = div_tags[2].text.strip()
                content = div_tags[3].text.strip()

                # Add the extracted information to the list
                results_list.append({
                    "link": link,
                    "href": href_value,
                    "title": title,
                    "brief": content
                })
            except Exception:
                pass
    except:
        pass
    return results_list
    
def internet_search(query, internet_nb_search_pages, chromedriver_path=None, quick_search:bool=False, buttons_to_press=['acccept']):
    """
    """

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    search_results = []

    nb_non_empty = 0
    # Configure Chrome options
    driver = prepare_chrome_driver(chromedriver_path)

    results = extract_results(
                                f"https://duckduckgo.com/?q={format_url_parameter(query)}&t=h_&ia=web",
                                internet_nb_search_pages,
                                driver
                            )
    
    for i, result in enumerate(results):
        title = result["title"]
        brief = result["brief"]
        href = result["href"]
        if quick_search:
            search_results.append({'url':href, 'title':title, 'brief': brief, 'content':""})
        else:
            search_results.append({'url':href, 'title':title, 'brief': brief, 'content':scrape_and_save(href, chromedriver_path=chromedriver_path, buttons_to_press=buttons_to_press)})
        nb_non_empty += 1
        if nb_non_empty>=internet_nb_search_pages:
            break

    return search_results

def internet_search_with_vectorization(query, chromedriver_path=None, internet_nb_search_pages=5, internet_vectorization_chunk_size=512, internet_vectorization_overlap_size=20, internet_vectorization_nb_chunks=4, model = None, quick_search:bool=False, vectorizer = "bert", vectorize=True, asses_using_llm=True, yes_no=None):
    """
    """

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from lollmsvectordb import VectorDatabase
    from lollmsvectordb import VectorDatabase
    from lollmsvectordb.text_document_loader import TextDocumentsLoader
    from lollmsvectordb.lollms_tokenizers.tiktoken_tokenizer import TikTokenTokenizer

    if vectorizer == "bert":
        from lollmsvectordb.lollms_vectorizers.bert_vectorizer import BERTVectorizer
        v = BERTVectorizer()
    elif vectorizer == "tfidf":
        from lollmsvectordb.lollms_vectorizers.tfidf_vectorizer import TFIDFVectorizer
        v = TFIDFVectorizer()
    elif vectorizer == "word2vec":
        from lollmsvectordb.lollms_vectorizers.word2vec_vectorizer import Word2VecVectorizer
        v = Word2VecVectorizer()

    vectorizer = VectorDatabase("", v, TikTokenTokenizer())

    formatted_text = ""
    nb_non_empty = 0
    # Configure Chrome options
    driver = prepare_chrome_driver(chromedriver_path)
    qquery = format_url_parameter(query)
    url = f"https://duckduckgo.com/?q={qquery}&t=h_&ia=web"
    results = extract_results(
                                url,
                                internet_nb_search_pages,
                                driver
                            )
    
    if len(results)>0:
        for i, result in enumerate(results):
            ASCIIColors.orange(f"Processing result:{result['title']}")
            title = result["title"]
            brief = result["brief"]
            href = result["href"]
            if quick_search:
                vectorizer.add_document({'url':href, 'title':title, 'brief': brief}, brief)
            else:
                get_relevant_text_block(href, driver, internet_vectorization_chunk_size, internet_vectorization_overlap_size, vectorizer, title, brief, query=query, asses_using_llm=asses_using_llm, yes_no=yes_no)
            nb_non_empty += 1
            if nb_non_empty>=internet_nb_search_pages:
                break
        vectorizer.build_index()
        chunks = vectorizer.search(query, internet_vectorization_nb_chunks)
    else:
        chunks = []
    # Close the browser
    driver.quit()

    return chunks
