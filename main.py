import asyncio
import logging

from CSGOMarketAPI import CSGOMarketAPI
from config import *

if DEBUG:
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
else:
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    # logging.basicConfig(filename='app.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s',
    #                     level=logging.INFO)


async def main_loop(bot: CSGOMarketAPI) -> None:
    """
    Главный loop

    :param bot: CSGOMarketAPI
    :return: None
    """
    exit_ = False
    if bot.balance < 0:
        bot.get_money()
    logging.info(f'Баланс: {bot.balance}')
    items_to_purchase = [{'item': item, 'price': _['price']} for item, _ in
                         zip(bot.mass_info(ITEMS_PURCHASE), ITEMS_PURCHASE)]
    while True:
        if exit_:
            break
        orders = bot.get_orders()
        orders = orders['Orders']
        logging.debug('-----orders-----')
        logging.debug(orders)
        logging.debug('----orders-END----')
        for _ in items_to_purchase:
            item, price = _['item'], _['price']
            if type(orders) == str:
                matches = False
            else:
                matches = [
                    i for i in orders if
                    int(i["i_classid"]) == item.class_id and int(i['i_instanceid']) == item.instance_id]
            if not matches:
                bot.insert_order(item, price)
                logging.info(f'Предмет "{item.market_name}". Выставление нового лота.')
                logging.info(f'Текущий баланс: {bot.balance / 100} ₽')

        await asyncio.sleep(MAIN_LOOP_DELAY / 1000)


async def main():
    logging.info('Init')
    bot = CSGOMarketAPI(API_KEY)
    t1 = asyncio.create_task(main_loop(bot))
    t2 = asyncio.create_task(bot.refresh_request_counter_loop())

    await t1
    await t2

    return


if __name__ == '__main__':
    asyncio.run(main())
