import asyncio
import logging
import time
from typing import List, TypedDict

import requests


class Item:
    def __init__(self, class_id: int, instance_id: int, market_name: str, market_hash_name: str, hash: str,
                 description: list = None, tags: list = None, our_market_instance_id: int = None):
        self.class_id = class_id
        self.instance_id = instance_id
        self.market_name = market_name
        self.market_hash_name = market_hash_name
        self.hash = hash
        self.description = description
        self.tags = tags
        self.our_market_instance_id = our_market_instance_id

    @staticmethod
    def new_from_response_item_info(response: dict):
        item_data = {
            'class_id': int(response['classid']),
            'instance_id': int(response['instanceid']),
            'market_name': response['market_name'],
            'market_hash_name': response['market_hash_name'],
            'description': response['description'],
            'tags': response['tags'],
            'our_market_instance_id':
                response['our_market_instanceid'] if
                response['our_market_instanceid'] != 'null' else None,
            'hash': response['hash']
        }

        return Item(**item_data)

    @staticmethod
    def new_from_mass_info(response: dict):
        item_data = {
            'class_id': int(response['classid']),
            'instance_id': int(response['instanceid']),
            'market_name': response['info']['market_name'],
            'market_hash_name': response['info']['market_hash_name'],
            'our_market_instance_id':
                response['info']['our_market_instanceid'] if
                response['info']['our_market_instanceid'] != 'null' else None,
            'hash': response['info']['hash']
        }

        return Item(**item_data)


class CSGOMarketAPI:
    IMPORT_ITEM_TYPE = TypedDict('IMPORT_ITEM_TYPE', class_id=int, instance_id=int)
    MASS_INFO_LIST_TYPE = List[IMPORT_ITEM_TYPE]

    def __init__(self, api_key: str) -> None:
        """
        :param api_key: API key
        """
        self.MAX_REQUESTS = 4
        self.API_KEY = api_key
        self.balance = -1
        self.request_counter = 0

    def set_api_key(self, api_key: str) -> str:
        """
        Устанавливает ключ API для запросов

        :param api_key: ключ API market.csgo.com
        :return: API KEY
        """
        self.API_KEY = api_key
        return self.API_KEY

    async def refresh_request_counter_loop(self) -> None:
        """
        Loop для обновления счетчика запросов

        :return: None
        """
        while True:
            self.request_counter = 0
            await asyncio.sleep(1)

    def request_possibility_check(func):
        """Декоратор проверки возможности отправить запрос"""

        def magic(self, *args, **kwargs):
            while not self.request_possibility():
                time.sleep(0.3)
            return func(self, *args, **kwargs)

        return magic

    def balance_check(func):
        """Декоратор для проверки баланса"""

        def magic(self, *args, **kwargs):
            if 'price' not in kwargs:
                price = args[1]
            else:
                price = kwargs['price']
            if self.balance < price:
                raise InsufficientFunds()
            return func(self, *args, **kwargs)

        return magic

    def request_possibility(self) -> bool:
        """
        Проверяет возможность отправки запроса и обновляет счетчик

        :return: bool
        """
        if self.request_counter < self.MAX_REQUESTS:
            self.request_counter += 1
            return True
        else:
            return False

    @request_possibility_check
    def mass_info(self, items: MASS_INFO_LIST_TYPE) -> List[Item]:
        """Возвращает список"""
        logging.debug('get_money()')
        SELL, BUY, HISTORY, INFO = 0, 0, 0, 2
        url = f'https://market.csgo.com/api/MassInfo/{SELL}/{BUY}/{HISTORY}/{INFO}?key={self.API_KEY}'
        formatted_body = [f'{i["class_id"]}_{i["instance_id"]}' for i in items]
        r = requests.post(url, {'list': ','.join(formatted_body)})
        data = self.validate_response(r)
        if 'success' in data and data['success']:
            result = data['results']
            return [Item.new_from_mass_info(i) for i in result]
        raise UnknownError(r)

    @request_possibility_check
    def get_money(self) -> int:
        """
        Обновляет баланс аккаунта

        :return: Текущий баланс в копейках
        """
        logging.debug('get_money()')
        url = f'https://market.csgo.com/api/GetMoney/?key={self.API_KEY}'
        r = requests.get(url)
        data = self.validate_response(r)
        if 'money' in data:
            self.balance = int(data['money'])
            return int(data['money'])
        raise UnknownError(r)

    @request_possibility_check
    @balance_check
    def insert_order(self, item: Item, price: float) -> bool:
        """
        Вставляет новый ордер на покупку предмета.

        :param item: Экземпляр класса предмета.
        :param price: цена предмета в копейках
        :return: Результат выполнения
        """
        logging.debug(f'insert_order(class_id=\'{item.class_id}\', '
                      f'instance_id=\'{item.instance_id}\', '
                      f'price=\'{price}\', '
                      f'hash=\'{item.hash}\')')
        url = f'https://market.csgo.com/api/InsertOrder/{item.class_id}/{item.instance_id}' \
              f'/{price}/{item.hash}/?key={self.API_KEY}'
        r = requests.get(url)
        data = self.validate_response(r)
        if 'success' in data:
            return data['success']

        return False

    @request_possibility_check
    @balance_check
    def update_order(self, item: Item, price: float) -> bool:
        """
        Изменить/удалить запрос на автоматическую покупку предмета.

        :param item: Экземпляр класса предмета.
        :param price: Цена в копейках, целое число.
        :return: Результат выполнения
        """
        url = f'https://market.csgo.com/api/UpdateOrder/{item.class_id}/{item.instance_id}/{price}/?key={self.API_KEY}'
        r = requests.get(url)
        data = self.validate_response(r)
        if 'success' in data:
            return data['success']

        return False

    def delete_order(self, item: Item) -> bool:
        """
        Удалить запрос на автоматическую покупку предмета.

        :param item: Экземпляр класса предмета.
        :return: Результат выполнения
        """
        return self.update_order(item, 0)

    @request_possibility_check
    def get_orders(self) -> dict:
        """
        Получает список текущих ордеров на автопокупку

        :return: dict
        """
        logging.debug('get_orders()')
        url = f'https://market.csgo.com/api/GetOrders/?key={self.API_KEY}'
        r = requests.get(url)

        return self.validate_response(r)

    @staticmethod
    def validate_response(response: requests.Response) -> dict:
        """
        Проверяет ответ на наличие ошибок

        :param response: Received response
        :raises BadAPIKey: Bad api key used
        :return: JSON like dict from response
        """
        if response.status_code != 200 and 'application/json' not in response.headers['content-type']:
            raise WrongResponse(response)
        body = response.json()
        if 'error' in body:
            if body['error'] == 'Bad KEY':
                raise BadAPIKey()
            raise UnknownError(body['error'])

        return body


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class BadAPIKey(Error):
    def __init__(self):
        logging.error('Bad API key used')


class WrongResponse(Error):
    """Получен некорректный ответ от сервера"""

    def __init__(self, response: requests.Response):
        """
        :param response: Received response
        """
        logging.error('Wrong response was received')
        logging.debug(response.text)
        self.response = response


class UnknownError(Error):
    """Произошла неизвестная ошибка"""

    def __init__(self, text: str):
        """
        :param text: Error text
        """
        logging.error('Response contains unknown error')
        logging.debug(text)
        self.response = text


class InsufficientFunds(Error):
    """Недостаточно средств для совершения операции"""
    pass
