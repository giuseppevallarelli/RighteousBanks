from csv import DictWriter
import math
import re
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def build_web_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    wd = webdriver.Chrome(options=chrome_options)
    return wd


def bank_details(html_element):
    url = html_element.find_element(By.TAG_NAME, 'a').get_attribute('href')
    bank_name = url.split('/')[-3]
    try:
        num_reviews_elem = html_element.find_element(By.CLASS_NAME, 'text-2xl')
    except Exception as _:
        num_reviews = None
    else:
        num_reviews = int(num_reviews_elem.text)
    return bank_name, url, num_reviews


def extract_data_reviews(web_driver, review_page):
    def category_score(html_elem, category_class):
        container = html_elem.find_element(By.CLASS_NAME, category_class)
        rating_score_raw_str = container.find_element(By.CLASS_NAME, 'full-stars').get_attribute('style')
        try:
            rating_score = int(re.search('[0-9]{1,3}', rating_score_raw_str).group())
        except Exception as _:
            raise RuntimeError(f'Failure for {category_class}')
        return rating_score

    web_driver.get(review_page)
    comments = web_driver.find_elements(By.CLASS_NAME, 'comments')
    reviews = []
    for com in comments:
        comment_rate = com.find_element(By.CLASS_NAME, 'comment_rate')
        com_data = {
            'user_name': com.find_element(By.CLASS_NAME, 'text-base').text,
            'title': com.find_element(By.CLASS_NAME, 'mb-4').text,
            'date': com.find_element(By.CLASS_NAME, 'font-muli').text,
            'review': com.find_elements(By.CLASS_NAME, 'text-base')[2].text,
            'home_banking': category_score(comment_rate, 'b0'),
            'security': category_score(comment_rate, 'b1'),
            'support':  category_score(comment_rate, 'b2'),
            'promotions': category_score(comment_rate, 'b3'),
            'services': category_score(comment_rate, 'b4'),
            'local_presence': category_score(comment_rate, 'b5')
        }
        reviews.append(com_data)
    return reviews


def bank_reviews(web_driver, company_page, num_reviews):
    company_rews = []
    reviews_per_page = 10
    if num_reviews > reviews_per_page:
        num_clicks = math.ceil(num_reviews / reviews_per_page)
        for i in range(0, num_clicks):
            company_rews += extract_data_reviews(web_driver, company_page)
            try:
                element = WebDriverWait(web_driver, 10).until(
                    EC.visibility_of_element_located((By.CLASS_NAME, 'show-more-btn')))
                element.click()
            except Exception as e:
                print(f'Failed for {company_page}: page {i}')
    else:
        company_rews = extract_data_reviews(web_driver, company_page)

    return company_rews


def retrieve_banks_reviews(web_driver, bank_boxes_details):
    revs = {}
    for name, web_page, num_revs in bank_boxes_details:
        if num_revs:
            revs[name] = bank_reviews(web_driver, web_page, num_revs)
            time.sleep(1)
    return revs


def serialize_to_csv(reviews, file_name='reviews.csv'):
    with open(f'./{file_name}', 'w') as csv_file:
        fieldnames = ['bank', 'user_name', 'title', 'date', 'review', 'home_banking', 'security', 'support',
                      'promotions', 'services', 'local_presence']
        writer = DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for company_name in reviews:
            company_reviews = reviews[company_name]
            for review in company_reviews:
                review.update({'bank': company_name})
                writer.writerow(review)


if __name__ == '__main__':
    # Target webpage
    web_page = 'https://www.sostariffe.it/banche-finanziarie/opinioni/'
    # Web Driver
    wd = build_web_driver()
    wd.get(web_page)
    # Accept privacy policy
    wd.find_element(By.CLASS_NAME, 'iubenda-cs-accept-btn').click()
    # Bank Cards
    bank_boxes = wd.find_elements(By.CLASS_NAME, 'rating-box')
    bank_boxes_details = [bank_details(box) for box in bank_boxes]
    reviews = retrieve_banks_reviews(wd, bank_boxes_details)
    # Serialize to csv
    serialize_to_csv(reviews)
