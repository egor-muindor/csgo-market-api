import asyncio
import logging
import time
from asyncio import CancelledError, shield
from typing import List, Tuple

import requests

from .Exceptions import *
from .Item import *
from .types import *

__all__ = ['CSGOMarketAPI']


class CSGOMarketAPI:

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
        Устанавливает ключ API для запросов.

        :param api_key: ключ API market.csgo.com.
        :return: API KEY
        """
        self.API_KEY = api_key
        return self.API_KEY

    async def refresh_request_counter_loop(self) -> None:
        """Loop для обновления счетчика запросов."""

        while True:
            self.request_counter = 0
            try:
                await shield(asyncio.sleep(1))
            except CancelledError:
                return

    async def stay_online_loop(self) -> None:
        """Loop с отправкой ping_pong раз в 3 минуты"""
        while True:
            try:
                await shield(self.ping_pong())
                await shield(asyncio.sleep(3 * 60 - 5))
            except BadGatewayError:
                continue
            except CancelledError:
                while True:
                    try:
                        await self.go_offline()
                    except BadGatewayError:
                        continue
                    finally:
                        break
                return

    def request_possibility_check(func):
        """Декоратор проверки возможности отправить запрос."""

        async def magic(self, *args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                while not self.request_possibility():
                    await asyncio.sleep(0.3)
                return await func(self, *args, **kwargs)
            else:
                if not self.request_possibility():
                    # это нужно, чтобы предотвратить зависание программы
                    # есть вероятность блокировки api ключа из-за превышения лимита запросов
                    time.sleep(1)
                return func(self, *args, **kwargs)

        return magic

    def balance_check(func):
        """Декоратор для проверки баланса."""

        def magic(self, *args, **kwargs):
            if 'price' not in kwargs:
                price = args[1]
            else:
                price = kwargs['price']
            if self.balance < price:
                raise InsufficientFundsException()
            return func(self, *args, **kwargs)

        return magic

    def request_possibility(self) -> bool:
        """
        Проверяет возможность отправки запроса, и обновляет счетчик.

        :return: bool
        """
        if self.request_counter < self.MAX_REQUESTS:
            self.request_counter += 1
            return True
        else:
            return False

    @staticmethod
    async def history():
        """Список последних 50 покупок со всей торговой площадки."""

        uri = 'https://market.csgo.com/history/json/'
        response = requests.get(uri)
        data = CSGOMarketAPI.validate_response(response)
        return data

    @request_possibility_check
    async def get_itemdb_uri(self) -> Tuple[str, str]:
        """
        Gets latest URI of db all items.

        :returns: (DB URI, time)
        """
        logging.debug('get_itemdb_uri()')
        uri = f'https://market.csgo.com/itemdb/current_730.json'
        response = requests.get(uri)
        data = self.validate_response(response)
        if 'db' in data:
            return f'https://market.csgo.com/itemdb/{data["db"]}', str(data['time'])
        raise UnknownError(response.text)

    @request_possibility_check
    async def item_info(self, item: ImportItemType, language: str = 'ru') -> Item:
        """
        Returns info and offers for current item.

        :param item: item info: {class_id: int, instance_id: int}.
        :param language: possible values: ru, en.
        :return: filled class Item.
        """
        if language not in ('ru', 'en'):
            raise AttributeError('`language` value must be one of (\'ru\', \'en\')')
        uri = f'https://market.csgo.com/api/ItemInfo/{item["class_id"]}_{item["instance_id"]}/{language}/' \
              f'?key={self.API_KEY}'
        response = requests.get(uri)
        data = self.validate_response(response)
        # TODO написать в сохранение цен, стикеров и прочей информации в класс предмета
        return Item.new_from_response_item_info(data)

    @request_possibility_check
    async def mass_info(self, items: MassInfoListType, sell: int = 0, buy: int = 0,
                        history: int = 0, info: int = 2) -> List[Item]:
        """
        Возвращает список предметов.

        :param items: list[dict{class_id: int, instance_id: int}]
        :param sell: Possible values (0,1,2).
            0 - Without any info |
            1 - 50 cheapest + your own offers |
            2 - Only 1 the cheapest offer
        :param buy: Possible values (0,1,2)
            0 - Without any info |
            1 - 50 most expensive offers to buy |
            2 - Only 1 the most expensive offer
        :param history: Possible values (0,1,2)
            0 - Without any info |
            1 - Info about last 100 sales |
            2 - Info about last 10 sales
        :param info: Possible values (0,1,2,3)
            0 - Without any info |
            1 - Base information about item (name, type...) |
            2 - Base info + hash, image URI
            3 - All info (description, tags from steam)
        :return: List of items with info.
        """
        if sell not in (0, 1, 2):
            raise AttributeError('`sell` value must be one of (0, 1, 2)')
        if buy not in (0, 1, 2):
            raise AttributeError('`buy` value must be one of (0, 1, 2)')
        if history not in (0, 1, 2):
            raise AttributeError('`history` value must be one of (0, 1, 2)')
        if info not in (0, 1, 2, 3):
            raise AttributeError('`info` value must be one of (0, 1, 2, 3)')
        if len(items) > 100:
            addiction_items = await self.mass_info(items[100:], sell, buy, history, info)
        else:
            addiction_items = []
        logging.debug('mass_info()')
        url = f'https://market.csgo.com/api/MassInfo/{sell}/{buy}/{history}/{info}?key={self.API_KEY}'
        formatted_body = ','.join([f'{i["class_id"]}_{i["instance_id"]}' for i in items[:100]])
        response = requests.post(url, {'list': formatted_body})
        data = self.validate_response(response)
        if 'success' in data and data['success']:
            result = data['results']
            # TODO написать в сохранение цен, стикеров и прочей информации в класс предмета
            return [Item.new_from_mass_info(i) for i in result] + addiction_items
        raise UnknownError(response.text)

    async def _request_offers(self, item: Item or ImportItemType, method: str) -> dict:
        """
        :param item: filled Item or {class_id: int, instance_id: int}.
        :param method: method name in uri like:
         f'https://market.csgo.com/api/{method}/{item["class_id"]}_{item["instance_id"]}/?key={self.API_KEY}'.
        :return: dict with info.
        """
        if isinstance(item, Item):
            item = {'class_id': item.class_id, 'instance_id': item.instance_id}
        uri = f'https://market.csgo.com/api/{method}/{item["class_id"]}_{item["instance_id"]}/?key={self.API_KEY}'
        result, data = await self.request_with_boolean_response(uri)
        if result:
            return data
        else:
            return dict()

    async def item_history(self, item: Item or ImportItemType) -> dict:
        """
        Returns item history of changing price last 500 deals.

        :param item: filled Item or {class_id: int, instance_id: int}.
        :return: dict with info.
        """
        return await self._request_offers(item, 'ItemHistory')

    async def sell_offers(self, item: Item or ImportItemType) -> dict:
        """
        Returns sale offers of a specific item.

        :param item: filled Item or {class_id: int, instance_id: int}.
        :return: dict with info.
        """
        return await self._request_offers(item, 'SellOffers')

    async def best_sell_offer(self, item: Item or ImportItemType) -> dict:
        """
        Returns the best sale offer price.

        :param item: filled Item or {class_id: int, instance_id: int}.
        :return: dict with info.
        """
        return await self._request_offers(item, 'BestSellOffer')

    async def buy_offers(self, item: Item or ImportItemType) -> dict:
        """
        Returns buy offers of a specific item.

        :param item: filled Item or {class_id: int, instance_id: int}.
        :return: dict with info.
        """
        return await self._request_offers(item, 'BuyOffers')

    async def best_buy_offer(self, item: Item or ImportItemType) -> dict:
        """
        Returns the best buy offer price.

        :param item: filled Item or {class_id: int, instance_id: int}.
        :return: dict with info.
        """
        return await self._request_offers(item, 'BestBuyOffer')

    @request_possibility_check
    async def get_money(self) -> int:
        """
        Обновляет баланс аккаунта.

        :return: Текущий баланс в копейках.
        """
        logging.debug('get_money()')
        url = f'https://market.csgo.com/api/GetMoney/?key={self.API_KEY}'
        response = requests.get(url)
        data = self.validate_response(response)
        if 'money' in data:
            self.balance = int(data['money'])
            return int(data['money'])
        raise UnknownError(response)

    @balance_check
    async def insert_order(self, item: Item, price: float) -> bool:
        """
        Вставляет новый ордер на покупку предмета.

        :param item: Экземпляр класса предмета.
        :param price: цена предмета в копейках.
        :return: Результат выполнения.
        """
        logging.debug(f'insert_order(class_id=\'{item.class_id}\', '
                      f'instance_id=\'{item.instance_id}\', '
                      f'price=\'{price}\', '
                      f'hash=\'{item.hash}\')')
        url = f'https://market.csgo.com/api/InsertOrder/{item.class_id}/{item.instance_id}' \
              f'/{price}/{item.hash}/?key={self.API_KEY}'
        return (await self.request_with_boolean_response(url))[0]

    @balance_check
    async def update_order(self, item: Item, price: float) -> bool:
        """
        Изменить/удалить запрос на автоматическую покупку предмета.

        :param item: Экземпляр класса предмета.
        :param price: Цена в копейках, целое число.
        :return: Результат выполнения.
        """
        url = f'https://market.csgo.com/api/UpdateOrder/{item.class_id}/{item.instance_id}/{price}/?key={self.API_KEY}'
        return (await self.request_with_boolean_response(url))[0]

    async def delete_order(self, item: Item) -> bool:
        """
        Удалить запрос на автоматическую покупку предмета.

        :param item: Экземпляр класса предмета.
        :return: Результат выполнения.
        """
        return await self.update_order(item, 0)

    async def get_orders(self) -> dict:
        """
        Получает список текущих ордеров на автопокупку

        :return: Возвращает словарь с ордерами.
        """
        logging.debug('get_orders()')
        url = f'https://market.csgo.com/api/GetOrders/?key={self.API_KEY}'
        result, data = await self.request_with_boolean_response(url)
        if type(data['Orders']) != str:
            return data['Orders']

        return dict()

    async def ping_pong(self) -> bool:
        """
        Выход в онлайн, необходимо отправлять раз в 3 минуты.

        :return: Результат выполнения.
        """
        logging.debug('PING PONG')
        url = f'https://market.csgo.com/api/PingPong/?key={self.API_KEY}'
        return (await self.request_with_boolean_response(url))[0]

    def sync_go_offline(self) -> bool:
        """
        Синхронно моментально приостановить торги.

        :return: Результат выполнения.
        """
        logging.debug('Going offline (sync)')
        url = f'https://market.csgo.com/api/GoOffline/?key={self.API_KEY}'
        response = requests.get(url)
        data = self.validate_response(response)
        return data['success']

    async def go_offline(self) -> bool:
        """
        Моментально приостановить торги.

        :return: Результат выполнения.
        """
        logging.debug('Going offline')
        url = f'https://market.csgo.com/api/GoOffline/?key={self.API_KEY}'
        return (await self.request_with_boolean_response(url))[0]

    @request_possibility_check
    async def request_with_boolean_response(self, url: str) -> Tuple[bool, dict]:
        """Метод для получения и обработки ответа с полем 'success'."""
        response = requests.get(url)
        data = self.validate_response(response)
        if 'success' in data:
            return data['success'], data

        return False, data

    @staticmethod
    def validate_response(response: requests.Response) -> dict:
        """
        Проверяет ответ на наличие ошибок.

        :param response: Received response.
        :raises BadAPIKey: Bad api key used.
        :return: JSON like dict from response.
        """
        if response.status_code == 502:
            raise BadGatewayError()
        if response.status_code != 200 and 'application/json' not in response.headers['content-type']:
            raise WrongResponseException(response)
        body = response.json()
        if 'error' in body:
            if body['error'] == 'Bad KEY':
                raise BadAPIKeyException()
            raise UnknownError(body['error'])

        return body
