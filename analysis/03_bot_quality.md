# Эффективность бота

Сравнивала письменные обращения до и после 1 апреля 2025 года по трем сегментам. Сначала смотрела только переоткрытия, затем добавила возвраты клиентов в течение 7 дней. Закрытый тикет не всегда означает, что проблема решена: клиент мог обратиться повторно.

## Что бот закрывает самостоятельно

Бот закрывает 77% обращений первой линии, 59,7% серой зоны и 37,7% второй. На сложных темах высокий процент автоматического закрытия еще не говорит о качестве работы.

```sql
SELECT blok, ROUND(AVG(bot_result = 'закрыл') * 100.0, 1)
FROM razmetka
WHERE period = 'после' AND written = 1
GROUP BY blok;
```

## Закрытие без переоткрытия

Если смотреть только флаг переоткрытия, доли решенных обращений почти везде высокие. Но это не доказывает, что клиент получил ответ: он мог создать новый тикет вместо переоткрытия старого.

```sql
-- люди до апреля
SELECT blok, ROUND(AVG(reopened = 0) * 100.0, 1)
FROM razmetka
WHERE period = 'до' AND written = 1
GROUP BY blok;
-- после апреля (бот + люди)
SELECT blok, ROUND(AVG(reopened = 0) * 100.0, 1)
FROM razmetka
WHERE period = 'после' AND written = 1
GROUP BY blok;
-- закрытые ботом после апреля
SELECT blok, ROUND(AVG(reopened = 0) * 100.0, 1)
FROM razmetka
WHERE period = 'после' AND written = 1 AND bot_result = 'закрыл'
GROUP BY blok;
```

## Закрытие без переоткрытия и возврата

По второй линии показатель среди закрытых ботом обращений составляет 55,7%, у людей до апреля было 78,6%. Я считаю более показательным вариант с возвратами: часть клиентов вместо переоткрытия старого тикета создает новый.

```sql
-- люди до апреля
SELECT blok, ROUND(AVG(reopened = 0 AND came_back = 0) * 100.0, 1)
FROM razmetka
WHERE period = 'до' AND written = 1
GROUP BY blok;
-- после апреля (бот + люди)
SELECT blok, ROUND(AVG(reopened = 0 AND came_back = 0) * 100.0, 1)
FROM razmetka
WHERE period = 'после' AND written = 1
GROUP BY blok;
-- закрытые ботом после апреля
SELECT blok, ROUND(AVG(reopened = 0 AND came_back = 0) * 100.0, 1)
FROM razmetka
WHERE period = 'после' AND written = 1 AND bot_result = 'закрыл'
GROUP BY blok;
```

## Телефон как контроль

На телефоне, где бота нет, показатель немного снизился с 84,5% до 82,9%. Значит, не все изменения после апреля обязательно вызваны автоматизацией.

```sql
SELECT 
    period,
    ROUND(AVG(CASE WHEN reopened = 0 AND came_back = 0 THEN 1.0 ELSE 0.0 END) * 100, 2) AS phone_fcr_with_returns
FROM clean
WHERE written = 0
GROUP BY period
ORDER BY period DESC;
```

## Два сценария

Если серую зону присоединить ко второй линии, показатель среди закрытых ботом обращений будет выше. Но даже в этом случае есть разрыв с людьми до апреля.

| Куда относим серую зону | Люди до апреля | Бот закрыл, доля | Без переоткрытия и возврата среди закрытых ботом |
|---|---:|---:|---:|
| Во вторую | 80,7% | 47,2% | 72,0% |
| В первую | 78,6% | 37,7% | 55,7% |

```sql
select 'серая во второй' as scenario,
       (select round(avg(reopened = 0 and came_back = 0) * 100,1)
        from razmetka where period='до' and written=1 and blok in ('вторая','серая')) as before_fcr,
       round(avg(bot_result='закрыл') * 100,1) as bot_closed,
       round(avg(case when bot_result='закрыл' then reopened = 0 and came_back = 0 end)*100,1) as bot_fcr
from razmetka
where period='после' and written=1 and blok in ('вторая','серая')
union all
select 'серая в первой',
       (select round(avg(reopened = 0 and came_back = 0)*100,1)
        from razmetka where period='до' and written=1 and blok='вторая'),
       round(avg(bot_result='закрыл') * 100,1),
       round(avg(case when bot_result='закрыл' then reopened = 0 and came_back = 0 end)*100,1)
from razmetka
where period='после' and written=1 and blok='вторая'
```

## Возвраты после закрытия ботом

Из 289 обращений второй линии, закрытых ботом, после 83 клиент вернулся в течение недели. В 16 случаях следующий тикет бот тоже закрыл, в 28 случаях передал человеку. Это показывает риск повторного автоматического ответа на сложную тему.

```sql
select count(*) as bot_closed,
       sum(came_back = 1) as returned,
       sum(came_back = 1 and next_bot_result = 'закрыл') as closed_again,
       sum(came_back = 1 and next_bot_result = 'передал') as transferred
from razmetka
where period='после' and written=1 and blok='вторая' and bot_result='закрыл'
```

## Вывод

Моя позиция: на первой линии бот полезен, на второй сложные обращения лучше сразу передавать специалисту. Серую зону можно автоматизировать частично, но сначала нужно отдельно проверить качество решения по темам и приоритетам.
