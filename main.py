import asyncio
import contextlib
import logging
from asyncio import shield, CancelledError

from MarketCSGO import CSGOMarketAPI
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
        await bot.get_money()
    logging.info(f'Баланс: {bot.balance}')
    items_to_purchase = [{'item': item, 'price': _['price']} for item, _ in
                         zip(await bot.mass_info(ITEMS_PURCHASE), ITEMS_PURCHASE)]
    while True:
        if exit_:
            break
        try:
            await shield(asyncio.sleep(MAIN_LOOP_DELAY / 1000))
        except CancelledError:
            return
        orders = await bot.get_orders()
        logging.debug('-----orders-----')
        logging.debug(orders)
        logging.debug('----orders-END----')
        for _ in items_to_purchase:
            item, price = _['item'], _['price']
            matches = [
                i for i in orders if
                int(i["i_classid"]) == item.class_id and int(i['i_instanceid']) == item.instance_id]
            if not matches:
                await bot.insert_order(item, price)
                logging.info(f'Предмет "{item.market_name}". Выставление нового лота.')
                logging.info(f'Текущий баланс: {bot.balance / 100} ₽')


def main():
    logging.info('----- Init -----')
    bot = CSGOMarketAPI(API_KEY)
    loop = asyncio.get_event_loop()

    tasks = asyncio.gather(
        bot.refresh_request_counter_loop(),
        bot.stay_online_loop(),
        main_loop(bot), return_exceptions=True
    )

    try:
        return loop.run_until_complete(tasks)
    except KeyboardInterrupt as e:
        logging.info("Caught keyboard interrupt. Canceling tasks...")
        tasks.add_done_callback(lambda t: loop.stop())
        tasks.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            loop.run_until_complete(tasks)
        loop.run_until_complete(loop.shutdown_asyncgens())
        logging.info('Bay!')
    finally:
        loop.close()
        exit()


if __name__ == '__main__':
    main()
