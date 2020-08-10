# Заметки

#### \[10.08.2020\] Использование пакета *requests*

Главной и единственной причиной использования пакета `requests` является
ограничения API на использование параллельных запросов. Пакет `requests`
является синхронным HTTP-клиентом и блокирует выполнение программы до
получения полного ответа от сервера. Данное решение является заведомо
проигрышным, но избавляет от необходимости выстраивать очередь запросов,
так же этот пакет гарантирует отправку нового запроса, только после
получения ответа от предыдущего запроса. Но есть некоторые методы,
которые имеют исключение на ограничение параллельности, которые
необходимо обрабатывать в отдельном параллельном потоке для снижения
латентности в программе.

Список таких методов:

```
api/ItemRequest/
api/v2/trade-request-give-p2p-all

api/PingPong
api/UpdateInventory

api/Buy
api/ProcessOrder
```

Рекомендуется использовать параллельно только 2 последних.

---
