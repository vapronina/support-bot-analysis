# Сегментация обращений

Разделила обращения на первую линию, вторую линию и серую зону. Учитывала тему, приоритет и медианное время обработки до апреля. Затем проверила возвраты клиентов. Разметка хранится в [segments.csv](../data/segments.csv).

## Медианное время по темам

Наибольшая медиана обработки до апреля у юридических вопросов (59 минут), возвратов денег (54 минуты) и жалоб (53 минуты). Эти темы сразу отнесла ко второй линии. Рутинные вопросы о паролях и расписании оставила первой линии. Для спорных тем учитывала еще и приоритет.

```sql
with ranked as (
    select topic, handle_min,
           row_number() over (partition by topic order by handle_min) as rn,
           count(*) over (partition by topic) as n
    from clean
    where period = 'до' and handle_min is not null
)
select topic, count(*) as tickets,
       round(avg(handle_min), 1) as avg_minutes,
       avg(case when rn in ((n + 1) / 2, (n + 2) / 2) then handle_min end) as median_minutes
from ranked
group by topic
order by median_minutes desc;
```

## Время по темам и приоритетам

Предыдущая основа градации зон сохраняется и подтверждается. Выбранные топики для второй линии имеют высокие медианы на всех приоритетах и налоборот для первой линии всегда низкие медианы. А серая имеет разброс в зависимости от приоритета.

```sql
with ranked as (
    select topic, priority, handle_min,
           row_number() over (partition by topic, priority order by handle_min) as rn,
           count(*) over (partition by topic, priority) as n
    from clean
    where period = 'до' and handle_min is not null
)
select topic, priority, count(*) as tickets,
       round(avg(handle_min), 1) as avg_minutes,
       avg(case when rn in ((n + 1) / 2, (n + 2) / 2) then handle_min end) as median_minutes
from ranked
group by topic, priority
order by topic, priority;
```

## Возвраты до апреля

В глаза бросается нулевая доля возвратов по NULL и пусто, но так заложено что без указания темы came_back будет 0. Лидеры техническая проблема, жалоба, юридический вопрос. В целом порядок сохраняется за исключением лидера. Медиана оказалась обманчива, высокий процент возврата неудовлетворенных первой линией

```sql
SELECT topic, COUNT(*), SUM(reopened), SUM(came_back), ROUND(SUM(came_back) * 100.0 / COUNT(*), 1)
FROM clean
WHERE period = 'до'
GROUP BY topic
ORDER BY 5 DESC;
```

## Размер сегментов

После внедрения бота по всем каналам в первой линии 1706 обращений (48,1%), во второй - 1085 (30,6%), в серой зоне - 758 (21,4%). Все темы и приоритеты получили разметку.

```sql
SELECT 
    period, blok, COUNT(*), ROUND(COUNT(*) * 100.0 / (
        SELECT COUNT(*) 
        FROM razmetka AS r 
        WHERE r.period = razmetka.period), 1)
FROM razmetka
GROUP BY period, blok
ORDER BY period DESC, blok;
```

## Вывод

Серая зона довольно большая. Поэтому окончательный результат по второй линии нужно посчитать при двух вариантах ее отнесения.
