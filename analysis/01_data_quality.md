# Проверка качества выгрузки

В выгрузке есть дубли, разные форматы дат и неоднозначные пропуски. Перед сравнением бота с людьми эти детали важно проверить.

## Строки и дубли

В `tickets` 7033 строки и 6760 уникальных обращений. После удаления полных дублей в `clean` осталось 6760 строк. Для дальнейшего анализа беру очищенную таблицу.

```sql
SELECT COUNT(*) FROM tickets;
SELECT COUNT(DISTINCT id) FROM tickets;
SELECT COUNT(*) FROM clean;
SELECT COUNT(DISTINCT id) FROM clean;
```

## Каналы

В сырых данных `Чат` и `чат` считаются разными каналами. При подготовке таблицы `clean` я объединила эти значения и убрала полные дубли.

```sql
SELECT channel, count (*) FROM tickets group by channel;
SELECT channel, count (*) FROM clean group by channel;
```

## Пустые темы

Пропущенная тема встречается и как пустая строка, и как текст `NULL`. В подготовленной таблице исправлена пустая строка, но текст `NULL` остался. Поэтому такие темы не использовала для надежной проверки повторных обращений.

```sql
SELECT topic, count (*) FROM tickets group by topic;
SELECT topic, count (*) FROM clean group by topic;
```

## Форматы дат

Встречаются два формата дат. Без приведения к одному виду сравнение с 1 апреля дает неверный результат. После очистки в периоде `после` 3549 обращений. Диапазон дат - с 1 января по 30 июня 2025 года.

```sql
SELECT 
    COUNT(CASE WHEN created_at LIKE '__.__.____%' THEN 1 END),
    COUNT(CASE WHEN created_at NOT LIKE '__.__.____%' OR created_at IS NULL THEN 1 END)
FROM tickets;

SELECT
    (SELECT COUNT(*) FROM tickets WHERE created_at >= '2025-04-01'),
    (SELECT COUNT(*) FROM clean WHERE period = 'после');

    SELECT MIN(created), MAX(created) FROM clean;
```

## Закрытия ботом

После апреля бот самостоятельно закрыл 1667 обращений. У 1570 из них не указан сотрудник. Остальные 97 случаев нельзя автоматически трактовать как необходимость вмешательства, нужна отдельная проверка маршрута обращения.

```sql
SELECT 
    COUNT(CASE WHEN bot_result = 'закрыл' THEN 1 END),
    COUNT(CASE WHEN bot_result = 'закрыл' AND (agent_id IS NULL OR agent_id = '') THEN 1 END)
FROM clean;
```

## Нумерация обращений

Номер `id` записан текстом, поэтому вычитать строки напрямую нельзя. После выделения числовой части номера обнаружены пропуски: до апреля 32, после 155. Неясно, являются ли они удаленными или не попавшими в выгрузку обращениями.

```sql
SELECT (MAX(id) - MIN(id) + 1) - COUNT(*) FROM tickets;
SELECT (MAX(num) - MIN(num) + 1) - COUNT(*) FROM clean WHERE period = 'до';
SELECT (MAX(num) - MIN(num) + 1) - COUNT(*) FROM clean WHERE period = 'после';
```

## Письменные каналы и бот

Бот работал в письменных каналах: чате, почте и форме. Всего после апреля он закрыл 1667 обращений. Сам факт закрытия еще не показывает, решил ли клиент свой вопрос.

```sql
SELECT channel, bot_result, COUNT(*)
FROM clean
WHERE period = 'после'
GROUP BY channel, bot_result
ORDER BY channel, bot_result;
```

## Первый ответ

В письменных каналах после апреля скорость первого ответа резко выросла за счет бота. Это не означает такое же улучшение качества решения: бот может ответить мгновенно и не разобраться в проблеме.

```sql
SELECT period, written, ROUND(AVG(first_reply_min), 1)
FROM clean
GROUP BY period, written
ORDER BY period DESC, written DESC;
```

## Переоткрытия и возвраты

После апреля выросло число повторных обращений. Переоткрытие старого тикета и новое обращение по той же теме - разные события, поэтому в оценке качества учитываю оба.

```sql
SELECT period, SUM(reopened), SUM(came_back)
FROM clean
GROUP BY period
ORDER BY period DESC;
```

## Сотрудники

У 1570 обращений не указан сотрудник, в основном это случаи закрытия ботом. Для сопоставления ID сотрудника со справочником нужно убрать букву `a` в начале номера. Разницу в нагрузке нельзя оценивать без учета сложности тем.

```sql
SELECT COALESCE(agent_id, 'Без сотрудника'), COUNT(*)
FROM clean
GROUP BY 1
ORDER BY 2 DESC;

SELECT id, login
FROM agents
WHERE CAST(id AS INTEGER) NOT IN (
    SELECT CAST(substr(agent_id, 2) AS INTEGER) 
    FROM clean 
    WHERE agent_id IS NOT NULL);
```

## Вывод

Для основной метрики выбираю обращение, которое не было переоткрыто и за которым не последовало повторное обращение по той же теме в течение 7 дней. Так оценка качества ближе к опыту клиента, хотя пропущенные темы могут занижать число возвратов.
