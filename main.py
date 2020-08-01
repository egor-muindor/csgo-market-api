import asyncio
import logging

import requests

from config import API_KEY, ITEMS_PURCHASE, DEBUG

if DEBUG:
    # logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
else:
    logging.basicConfig(filename='app.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.INFO)


class CSGOMarketAPI:
    def __init__(self):
        self.MAX_REQUESTS = 4
        self.API_KEY = API_KEY
        self.ITEMS_PURCHASE = []
        self.balance = -1
        self.request_counter = 0

    def set_api_key(self, api_key: str):
        self.API_KEY = api_key

    def add_items_purchase(self, items: list):
        self.ITEMS_PURCHASE += items

    async def refresh_request_counter_loop(self):
        while True:
            self.request_counter = 0
            await asyncio.sleep(1)

    def request_possibility(self) -> bool:
        if self.request_counter < self.MAX_REQUESTS:
            self.request_counter += 1
            return True
        else:
            return False

    async def get_money(self) -> int:
        """
        Обновляет баланс аккаунта

        :return: Текущий баланс в копейках
        """
        while not self.request_possibility():
            await asyncio.sleep(0.3)

        logging.debug('get_money()')
        url = f'https://market.csgo.com/api/GetMoney/?key={API_KEY}'
        r = requests.get(url)

        if r.status_code == 200 and 'application/json' in r.headers['content-type']:
            data = r.json()
            if 'error' in data:
                logging.error(data['error'])
                raise requests.HTTPError(data['error'])
            logging.debug(data)
            if 'money' in data:
                self.balance = int(data['money'])
                return data['money']
        logging.error(r.text)
        raise requests.HTTPError('Wrong response')

    async def insert_order(self, class_id: str, instance_id: str, price: str, hash='', **kwargs) -> bool:
        """
        Вставляет новый ордер на покупку предмета.

        :param class_id: ClassID предмета в Steam
        :param instance_id: InstanceID предмета в Steam
        :param price: цена предмета в копейках
        :param hash: md5 от описания предмета. Вы можете найти его в ответе метода ItemInfo
        :param kwargs: неиспользуется

        :return Результат выполнения
        """
        while not self.request_possibility():
            await asyncio.sleep(0.3)

        if await self.get_money() < int(price):
            logging.error('Недостаточно средств на балансе')
            raise AttributeError('Недостаточно средств на балансе')

        logging.debug(f'insert_order(class_id=\'{class_id}\', '
                      f'instance_id=\'{instance_id}\', '
                      f'price=\'{price}\', '
                      f'hash=\'{hash}\')')
        url = f'https://market.csgo.com/api/InsertOrder/{class_id}/{instance_id}/{price}/{hash}/?key={self.API_KEY}'
        r = requests.get(url)
        if r.status_code == 200 and 'application/json' in r.headers['content-type']:
            data = r.json()
            if 'error' in data:
                logging.error(data['error'])
                raise requests.HTTPError(data['error'])
            logging.debug(data)
            if 'success' in data:
                return data['success']
        logging.error(r.text)
        raise requests.HTTPError('Wrong response')

    async def get_orders(self) -> dict:
        while not self.request_possibility():
            await asyncio.sleep(0.3)

        logging.debug('get_orders()')
        url = f'https://market.csgo.com/api/GetOrders/?key={self.API_KEY}'
        r = requests.get(url)
        if r.status_code == 200 and 'application/json' in r.headers['content-type']:
            data = r.json()
            if 'error' in data:
                logging.error(data['error'])
                raise requests.HTTPError(data['error'])
            logging.debug(data)
            return data
        logging.error(r.text)
        raise requests.HTTPError('Wrong response')


async def main_loop(bot):
    exit_ = False
    if bot.balance < 0:
        await bot.get_money()
    logging.info(f'Баланс: {bot.balance}')
    while True:
        await asyncio.sleep(5)
        if exit_:
            break
        orders = await bot.get_orders()
        orders = orders['Orders']
        logging.debug('Orders:', orders)
        for item in ITEMS_PURCHASE:
            matches = [
                i for i in orders if i["i_classid"] == item['class_id'] and i['i_instanceid'] == item['instance_id']]
            if not matches:
                logging.info(f'Предмет "{item["market_name"]}" был куплен. Выставление нового лота.')
                logging.info(f'Текущий баланс: {bot.balance} ₽')
                await bot.insert_order(**item)


async def main():
    logging.info('Init')
    bot = CSGOMarketAPI()
    t1 = asyncio.create_task(main_loop(bot))
    t2 = asyncio.create_task(bot.refresh_request_counter_loop())

    await t1
    await t2

    return


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    asyncio.run(main())
