import logging
import time
import json
import requests
from lxml import etree
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


class BaseScraper:
    use_debug = True
    max_retry_cnt = 3

    def __init__(self):
        try:
            self.config_log()
        except Exception as e:
            self.print_out(f"init: {e}")

    def get_driver(self):
        service = Service(executable_path='./chromedriver.exe')
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-gpu")
        # options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        return webdriver.Chrome(service=service, options=options)

    def get_cookies(self):
        cookies = []
        for cookie in self.driver.get_cookies():
            try:
                cookies.append(f"{cookie['name']}={cookie['value']}")
            except:
                pass
        return "; ".join(cookies)

    def validate(self, item):
        try:
            if item == None:
                item = ''
            if type(item) == list:
                item = ' '.join(item)
            item = str(item).strip()
            return item
        except:
            return ""

    def eliminate_space(self, items):
        values = []
        for item in items:
            item = self.validate(item)
            if item.lower() not in ['', ',']:
                values.append(item)
        return values

    def config_log(self):
        logging.basicConfig(
            filename=f"history.log",
            format='%(asctime)s %(levelname)-s %(message)s',
            level=logging.INFO,
            datefmt='%Y-%m-%d %H:%M:%S')

    def print_out(self, value):
        if self.use_debug:
            print(value)
        else:
            logging.info(value)


class BreachforumsScraper(BaseScraper):
    name = "output"
    base_url = "https://breachforums.st"
    captcha_api_key = ""
    timeout = 2
    history = []
    json_data = []

    def run(self):
        try:
            self.print_out("\nStarting...")
            self.driver = self.get_driver()
            self.cookies = self.get_cookies()
            self.parse_login(f"{self.base_url}/member?action=login")
            self.driver.get(f"{self.base_url}/index.php")
            time.sleep(self.timeout)
            tree = etree.HTML(self.driver.page_source)
            for forum in self.eliminate_space(
                tree.xpath(".//a[@class='forums__forum-name']/@href")
            ):
                if forum in self.history:
                    continue
                self.parse_forum(forum)

            self.print_out("\nCompleted")
        except Exception as e:
            self.print_out(f"error in  run: {e}")
    
    def parse_login(self, url):
        try:
            self.driver.get(url)
            username = self.driver.find_element(By.XPATH, "//input[@name='username']")
            username.clear()
            username.send_keys("onetxguy")

            password = self.driver.find_element(By.XPATH, "//input[@name='password']")
            password.clear()
            password.send_keys("LtPBQ5yRFpoT5jKsbGaBTbq")

            username.clear()
            username.send_keys("onetxguy")

            site_key = "09efe116-0a83-4eee-8af7-3df251064617"

            captcha_id_response = requests.post(
                "http://2captcha.com/in.php",
                data={
                    'key': self.captcha_api_key,
                    'method': 'hcaptcha',
                    'sitekey': site_key,
                    'pageurl': url,
                    'json': 1
                }
            )
            self.print_out(f"captcha_id_response: {captcha_id_response.json()}")
            captcha_id = captcha_id_response.json().get("request")
            captcha_result = None
            while True:
                time.sleep(self.timeout * 2)
                result_response = requests.get(
                    f"http://2captcha.com/res.php?key={self.captcha_api_key}\
                        &action=get&id={captcha_id}&json=1"
                )
                result_json = result_response.json()
                if result_json.get("status") == 1:
                    captcha_result = result_json.get("request")
                    break
                elif result_json.get("status") == 0:
                    self.print_out(f"captcha retrying...")

            captcha_input = self.driver.execute_script(
                "return document.querySelector('textarea[name=\"h-captcha-response\"]')"
            )
            self.print_out(f"captcha_result: {captcha_result}")
            self.driver.execute_script(
                f"arguments[0].value = '{captcha_result}';",
                captcha_input
            )
            self.driver.find_element(By.XPATH, "//input[@name='submit']").click()

            time.sleep(self.timeout)
            self.print_out(f"login successfully")
        except Exception as e:
            self.print_out(f"error in parse_login: {e}")

    def parse_forum(self, forum):
        try:
            self.history.append(forum)
            forum_url = f"{self.base_url}/{forum}"
            while True:
                self.driver.get(forum_url)
                self.print_out(f"forum: {forum_url}")
                time.sleep(self.timeout)
                try:
                    self.driver.find_element(
                        By.XPATH,
                        "//div[@class='forums__forum-description']//a[1]"
                    ).click()
                    time.sleep(self.timeout)
                except:
                    pass
                tree = etree.HTML(self.driver.page_source)
                threads = self.eliminate_space(
                    tree.xpath("//span[contains(@class, ' subject_')]//a/@href")
                )
                for thread in threads:
                    self.parse_thread(thread)

                next_pages = self.eliminate_space(
                    tree.xpath(".//a[@class='pagination_next']/@href")
                )
                if len(next_pages) > 0:
                    forum_url = f"{self.base_url}/{next_pages[0]}"
                else:
                    break
            
            with open(f"{forum}.json", "w") as f:
                json.dump(self.json_data, f, indent=4)
            self.json_data = []
        except Exception as e:
            self.print_out(f"error in parse_forum: {e}")

    def parse_thread(self, thread):
        try:
            thread_url = f"{self.base_url}/{thread}"
            while True:
                self.driver.get(thread_url)
                self.print_out(f"thread: {thread_url}")
                time.sleep(self.timeout)
                tree = etree.HTML(self.driver.page_source)
                posts = tree.xpath("//div[@class='post ']")
                post_title = self.validate(
                    tree.xpath("//span[@class='thread-info__name rounded']//text()")
                )
                for post in posts:
                    poster_info = {
                        "role": self.validate(
                            post.xpath(".//div[@class='post__user-badge']//img/@title")
                        )
                    }
                    for p_info in tree.xpath(
                        ".//div[@class='post__author-stats']//div[@class='post__stats-bit group']"
                    ):
                        p_info_label = self.validate(
                            p_info.xpath(".//span[@class='float_left']//text()")
                        ).lower()
                        p_info_value = self.validate(
                            p_info.xpath(".//span[@class='float_right']//text()")
                        )
                        poster_info[p_info_label] = p_info_value

                    self.json_data.append({
                        "title": post_title,
                        "poster": self.validate(
                            post.xpath(".//div[@class='post__user-profile largetext']//text()")
                        ),
                        "date": self.validate(
                            post.xpath(".//span[@class='post_date']//text()")
                        ),
                        "poster_info": poster_info,
                        "post_url": thread_url,
                        "post_content": self.validate(
                            post.xpath(".//div[@class='post_body scaleimages']/text()")
                        )
                    })

                next_pages = self.eliminate_space(
                    tree.xpath(".//a[@class='pagination_next']/@href")
                )
                if len(next_pages) > 0:
                    thread_url = f"{self.base_url}/{next_pages[0]}"
                else:
                    break
        except Exception as e:
            self.print_out(f"error in parse_forum: {e}")


if __name__ == '__main__':
    BreachforumsScraper().run()
