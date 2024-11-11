import browserforge.headers
from scrapy.cmdline import execute
from datetime import datetime
from typing import Iterable
from scrapy import Request
import pandas as pd
import urllib.parse
import lxml.html
import random
import string
import scrapy
import json
import time
import evpn
import os
import re
from unidecode import unidecode


def header_cleaner(header_text: str) -> str:
    # pattern = r'[^\w\s]'  # Matches anything that is not a word character or whitespace
    # header = re.sub(pattern=pattern, string=header_text, repl='')
    # header = '_'.join(header.lower().split())
    header_text = header_text.strip()
    header = unidecode('_'.join(header_text.lower().split()))
    return header


def get_sanctioned_name(case_dict: dict) -> str:
    name = case_dict.get('nomeSancionado', 'N/A')
    return name if name not in ['', ' ', None] else 'N/A'


def get_cnpjcpf_sanctioned(case_dict: dict) -> str:
    cnpjcpf_sanctioned = case_dict.get('cpfCnpj', 'N/A')
    return cnpjcpf_sanctioned if cnpjcpf_sanctioned not in ['', ' ', None] else 'N/A'


def get_sanctioned_state(case_dict: dict) -> str:
    sanctioned_state = case_dict.get('ufSancionado', 'N/A')
    return sanctioned_state if sanctioned_state not in ['', ' ', None] else 'N/A'


def get_registration(case_dict: dict) -> str:
    registration = case_dict.get('cadastro', 'N/A')
    return registration if registration not in ['', ' ', None] else 'N/A'


def get_details_link(case_dict: dict) -> str:
    details_link_slug = case_dict.get('linkDetalhamento', 'N/A')
    details_link = 'https://portaldatransparencia.gov.br' + details_link_slug
    return details_link if details_link_slug not in ['', ' ', None, 'N/A'] else 'N/A'


def get_organization(case_dict: dict) -> str:
    organization = case_dict.get('orgao', 'N/A')
    return organization if organization not in ['', ' ', None] else 'N/A'


def get_sanction_categry(case_dict: dict) -> str:
    sanction_categry = case_dict.get('categoriaSancao', 'N/A')
    return sanction_categry if sanction_categry not in ['', ' ', None] else 'N/A'


def get_sanction_publication_date(case_dict: dict) -> str:
    publication_date = case_dict.get('dataPublicacao', 'N/A')  # Original date string
    if publication_date != 'Sem informação':
        date_object = datetime.strptime(publication_date, "%d/%m/%Y")  # Convert the date string to a datetime object
        publication_date = date_object.strftime("%Y-%m-%d")  # Format the date to 'YYYY-MM-DD'
    return publication_date if publication_date not in ['', ' ', None, 'Sem informação'] else 'N/A'


def get_fine_amount(case_dict: dict) -> str:
    fine_amount = case_dict.get('valorMulta', 'N/A')
    return fine_amount if fine_amount not in ['', ' ', None, 'Não se aplica'] else 'N/A'


def get_quantity(case_dict: dict) -> str:
    quantity = f"{case_dict.get('quantidade', 'N/A')}"  # Using Format string as quantity value is integer in dictionary
    return quantity if quantity not in ['', ' ', None] else 'N/A'


class PortaltranspGovBrSpider(scrapy.Spider):
    name = "portaltransp_gov_br"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print('Connecting to VPN (BRAZIL)')
        self.api = evpn.ExpressVpnApi()  # Connecting to VPN (BRAZIL)
        self.api.connect(country_id='163')  # brazil country code
        time.sleep(5)  # keep some time delay before starting scraping because connecting
        if self.api.is_connected:
            print('VPN Connected!')
        else:
            print('VPN Not Connected!')

        # Initialize page counter
        self.page_number = 1

        self.final_data_list = list()
        self.delivery_date = datetime.now().strftime('%Y%m%d')

        # Path to store the Excel file can be customized by the user
        self.excel_path = r"../Excel_Files"  # Client can customize their Excel file path here (default: govtsites > govtsites > Excel_Files)
        os.makedirs(self.excel_path, exist_ok=True)  # Create Folder if not exists
        self.filename = fr"{self.excel_path}/{self.name}_{self.delivery_date}.xlsx"  # Filename with Scrape Date

        self.cookies = {
            'lgpd-cookie': '{"essenciais":true,"desempenho":false}',
            '_hjSessionUser_3454957': 'eyJpZCI6Ijk3YzQ5YWUwLTdlOGQtNTExYi1iNjI1LTU0YWQyOGRiYTI5ZiIsImNyZWF0ZWQiOjE3Mjk0OTk3ODQwNTUsImV4aXN0aW5nIjp0cnVlfQ==',
            'aws-waf-token': 'a9602ccf-0f55-4cc6-a174-ed0873e4c243:EAoAYOl8a58qBAAA:DSLMn4/MgaUjuQ8UYtlki2pTc8yyW861H2EkpEfzGBAFwA/IHGXbqPi+VaBxNxJEn1nsLthqZoiGSD0oTq4VZRlUJv2eGfKjPJL8zY0w8oTAX/JND57baAaQIaHqQfrslqbk2Vj0R8AxUkvacjDBuQm/Bcm4zNOJ6cm6b2dE5K6fy+OIU+HTf+lXMPrEwWFUdOSfVUrh5wHqJ9bh5n8rW5LMsjeO5rASsn0lVsBcAdXnzjOmnCabbazlQ96D5ZojJj9w+FhkaN4WwLT5svRV8cJAfA==',
            'SESSION': 'MzAzMjAzNjEtYmE5ZS00N2U0LWE2NjAtMzZhZGMwZjE4NDAz',
            '_hjSession_3454957': 'eyJpZCI6ImJlNjc5YzllLWY0YWQtNDMzMy05MWMzLTJlZTg4Y2FmYjUzNSIsImMiOjE3Mjk4MzcyNTY2MTIsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowLCJzcCI6MX0=',
        }

        self.headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'en-US,en;q=0.9',
            'priority': 'u=1, i',
            'referer': 'https://portaldatransparencia.gov.br/sancoes/consulta?cadastro=1&ordenarPor=nomeSancionado&direcao=asc',
            'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }

        self.cookies_details = {
            'lgpd-cookie': '{"essenciais":true,"desempenho":false}',
            '_hjSessionUser_3454957': 'eyJpZCI6IjkzYjA1ZjhjLTRmMGMtNTY4Ny04NTUyLWYwZDQ0NDU2OWYwZCIsImNyZWF0ZWQiOjE3MzAwOTIxMDU2MzIsImV4aXN0aW5nIjp0cnVlfQ==',
            'SESSION': 'M2RmMjhiMDctZmI2MC00M2VhLTg5YTctNDg1YWQzMGFhMWNj',
            '_hjSession_3454957': 'eyJpZCI6IjE2ZjgyMDJhLThkNDEtNDhiZi1hYWNhLWU0ZjY4ZmNkOTdmMiIsImMiOjE3MzAxMDQ3OTcwNzMsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowLCJzcCI6MX0=',
        }

        self.headers_details = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9,id;q=0.8',
            'priority': 'u=0, i',
            'referer': 'https://portaldatransparencia.gov.br/sancoes/consulta?paginacaoSimples=true&tamanhoPagina=&offset=&direcaoOrdenacao=asc',
            'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        }

        # Headers changes at some interval, hence using HeaderGenerator to generate headers
        # self.headers = browserforge.headers.HeaderGenerator().generate()
        self.params = {
            'paginacaoSimples': 'false',
            'tamanhoPagina': '15',
            'offset': '0',
            'direcaoOrdenacao': 'asc',
            'colunaOrdenacao': 'nomeSancionado',
            'cadastro': '1',
            'colunasSelecionadas': 'linkDetalhamento,cadastro,cpfCnpj,nomeSancionado,ufSancionado,orgao,categoriaSancao,dataPublicacao,valorMulta,quantidade',
            '_': '1729840466319',
        }

        self.browsers = ["chrome110", "edge99", "safari15_5"]
        self.url = 'https://portaldatransparencia.gov.br/sancoes/consulta/resultado?'

    def start_requests(self) -> Iterable[Request]:
        url = self.url + urllib.parse.urlencode(self.params)
        yield scrapy.Request(url=url, cookies=self.cookies, headers=self.headers, method='GET', meta={'impersonate': random.choice(self.browsers)},
                             callback=self.parse, dont_filter=True, cb_kwargs={'params': self.params})

    def parse(self, response, **kwargs):
        json_dict = json.loads(response.text)
        cases_list: list = json_dict.get('data', [])
        if cases_list:
            for case_dict in cases_list:
                data_dict: dict = {
                    'url': 'https://portaldatransparencia.gov.br/sancoes/consulta?cadastro=1&ordenarPor=nomeSancionado&direcao=asc',  # Site URL
                    'nome_sancionado': get_sanctioned_name(case_dict=case_dict),  # Sanctioned Name
                    'cadastro': get_registration(case_dict=case_dict),  # Registration
                    'cnpjcpf_sancionado': get_cnpjcpf_sanctioned(case_dict=case_dict),  # Sanctioned CNPJ/CPF
                    'uf_sancionado': get_sanctioned_state(case_dict=case_dict),  # Sanctioned State
                    'details_link': get_details_link(case_dict=case_dict),  # Details Link
                    'orgao/entidade_sancionadora': get_organization(case_dict=case_dict),  # Sanctioning body/entity
                    'categoria_sancao': get_sanction_categry(case_dict=case_dict),  # Sanction Category
                    'data_de_publicacao_da_sancao': get_sanction_publication_date(case_dict=case_dict),  # Sanction publication date
                    'valor_da_multa': get_fine_amount(case_dict=case_dict),  # Fine amount
                    'quantidade': get_quantity(case_dict=case_dict),  # Quantity
                }
                # Sending Request on Details page of current case
                yield scrapy.Request(url=data_dict['details_link'], cookies=self.cookies_details, headers=browserforge.headers.HeaderGenerator().generate(), callback=self.parse_details_page, dont_filter=True, cb_kwargs={'data_dict': data_dict})
            print('-' * 50)

            # # Pagination Request
            # # Increase the offset for the next page (assuming the current offset is already in params)
            # print(f"Currently on page: {self.page_number}")  # Print the current page number
            # print('Performing Pagination...')
            # # Increment page counter
            # self.page_number += 1
            # params = kwargs['params'].copy()  # Copy the params from the current request
            # current_offset = int(params['offset'])  # Get the current offset
            # next_offset = current_offset + 15  # Increment the offset by 15
            # params['offset'] = str(next_offset)  # Update the offset in params
            #
            # # Check if there are more results by evaluating if the cases list is non-empty
            # next_page_url = self.url + urllib.parse.urlencode(params)  # Generate the next page URL
            # print(f"Requesting next page with offset: {next_offset}")
            # yield scrapy.Request(url=next_page_url, cookies=self.cookies, headers=self.headers, method='GET', meta={'impersonate': random.choice(self.browsers)},
            #                      callback=self.parse, dont_filter=True, cb_kwargs={'params': params})
        else:
            print(f'Data and Next Page not Found! on page number {self.page_number}')

    def parse_details_page(self, response, **kwargs):
        data_dict = kwargs['data_dict']
        selector = lxml.html.fromstring(response.text)

        # Sanctioned company or person
        # Sanction Details
        xpath_section = '//div[@class="container"]/section[@class="dados-tabelados"]/div'
        div_tags = selector.xpath(xpath_section)

        for div_tag in div_tags:
            # Extract all headers within the div
            headers = div_tag.xpath('.//strong/text()')
            # Extract the corresponding values next to the headers
            values = []
            for header in headers:
                value_xpath = f'.//strong[text()="{header}"]/following-sibling::span[1]//text()'
                value = div_tag.xpath(value_xpath)
                value = ' '.join(value).strip() if value else 'N/A'
                values.append(value)

            # You can store the header-value pairs in data_dict
            for _header, value in zip(headers, values):
                header = header_cleaner(_header)
                data_dict[header] = value

        # xpath_attention = "//div[@class='col-xs-12 col-sm-12']/p/text()"
        xpath_attention = "//div/p[contains(text(), 'ATENÇÃO')]/text()"
        attention_div = selector.xpath(xpath_attention)
        header_text = attention_div[0]
        header = header_cleaner(header_text)
        data_dict[header] = attention_div[1]

        # Extract the detail page link and send a request to it
        more_details_page_link_xpath = "//a[small[contains(text(),'Clique aqui para saber mais sobre essa empresa')]]/@href"
        more_details_page_link = selector.xpath(more_details_page_link_xpath)

        if more_details_page_link:
            more_details_page_link = 'https://portaldatransparencia.gov.br' + more_details_page_link[0]  # Convert to absolute URL
            data_dict['more_details_page_link'] = more_details_page_link
            print('more_details_page_link:', more_details_page_link)

            # Make a request to the detail page
            yield scrapy.Request(url=more_details_page_link, cookies=self.cookies_details, headers=browserforge.headers.HeaderGenerator().generate(), callback=self.parse_more_details_page, dont_filter=True, cb_kwargs={'data_dict': data_dict})  # Pass the current data_dict to the next request
        else:
            print('more_details_page_link not Found, appending data_dict...')
            self.final_data_list.append(data_dict)

    def parse_more_details_page(self, response, **kwargs):
        print('in more details page...')
        data_dict = kwargs['data_dict']
        selector = lxml.html.fromstring(response.text)

        # XPath to find all div sections that contain the headers and their values
        xpath_section = "//div[@class='container']/section[@class='dados-tabelados']//div[contains(@class, 'col-xs-12')]"
        div_tags = selector.xpath(xpath_section)

        for div_tag in div_tags:
            # Extract all headers within the div
            headers = div_tag.xpath('.//strong/text()')
            # Extract the corresponding values next to the headers
            values = []
            for header in headers:
                value_xpath = f'.//strong[text()="{header}"]/following-sibling::span[1]//text()'
                value = div_tag.xpath(value_xpath)
                value = ' '.join(value).strip() if value else 'N/A'
                values.append(value)

            # Store the header-value pairs in data_dict
            for _header, value in zip(headers, values):
                header = header_cleaner(_header)  # Optionally clean the header
                data_dict[header] = value

        print(json.dumps(data_dict))

    def close(self, reason):
        print('closing spider...')
        # print("Converting List of Dictionaries into DataFrame, then into Excel file...")
        # try:
        #     print("Creating Native sheet...")
        #     data_df = pd.DataFrame(self.final_data_list)
        #     # data_df = df_cleaner(data_frame=data_df)  # Apply the function to all columns for Cleaning
        #     data_df.drop_duplicates(inplace=True)  # Remove duplicate data from DataFrame
        #     with pd.ExcelWriter(path=self.filename, engine='xlsxwriter') as writer:
        #         data_df.to_excel(excel_writer=writer, index=False)
        #     print("Native Excel file Successfully created.")
        # except Exception as e:
        #     print('Error while Generating Native Excel file:', e)
        if self.api.is_connected:  # Disconnecting VPN if it's still connected
            self.api.disconnect()


if __name__ == '__main__':
    execute(f'scrapy crawl {PortaltranspGovBrSpider.name}'.split())