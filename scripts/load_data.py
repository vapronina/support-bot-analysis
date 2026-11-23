import csv
import sqlite3
from collections import defaultdict
from datetime import datetime


# Читаем CSV: для каждого столбца доступно его имя.
def read(path):
    with path.open(encoding='utf-8-sig',newline='') as file:
        return list(csv.DictReader(file))


# В CSV даты двух форматов: приводим их к одному.
def parsed(value):
    if not value:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%d.%m.%Y %H:%M'):
        try:
            return datetime.strptime(value,fmt)
        except ValueError:
            pass
    raise ValueError(f'Неизвестная дата: {value}')


# Создаем временную базу SQLite из данных об обращениях и сотрудниках.
def load_database(root):
    con=sqlite3.connect(':memory:')
    agents=read(root/'data/agents.csv')
    raw=read(root/'data/tickets.csv')
    con.execute('create table agents (id text,login text,team text,hired_at text)')
    con.executemany('insert into agents values (?,?,?,?)',
      ((r['id'],r['login'],r['team'],r['hired_at']) for r in agents))
    columns=list(raw[0])
    con.execute('create table tickets (%s)' % ','.join(f'"{name}" text' for name in columns))
    con.executemany('insert into tickets values (%s)' % ','.join('?' for _ in columns),
                    (tuple(r[k] for k in columns) for r in raw))

    # 1. Убираем строки, которые полностью дублируют друг друга.
    unique=[]
    seen=set()
    for r in raw:
        key=tuple(r[k] for k in columns)
        if key not in seen:
            unique.append(r)
            seen.add(key)
    # 2. Приводим даты, каналы и пропуски к единому виду.
    base=[]
    for r in unique:
        created=parsed(r['created_at'])
        reply=parsed(r['first_reply_at'])
        closed=parsed(r['resolved_at'])
        topic=r['topic'] if r['topic'] else 'без темы'
        base.append({
            'id':r['id'], 'num':int(r['id'][1:]),
            'created':created, 'client_id':r['client_id'],
            'channel':'чат' if r['channel']=='Чат' else r['channel'],
            'topic':topic,'priority':int(r['priority']),
            'bot_result':r['bot_result'] or 'нет',
            'agent_id':r['agent_id'] or None,
            'handle_min':int(r['handle_min']) if r['handle_min'] else None,
            'first_reply_min':round((reply-created).total_seconds()/60,1) if reply else None,
            'resolve_hours':round((closed-created).total_seconds()/3600,1) if closed else None,
            'status':r['status'],'reopened':int(r['reopened']),
            'csat':int(r['csat']) if r['csat'] else None
        })
    # 3. Собираем обращения по одному клиенту и одной теме.
    by_client=defaultdict(list)
    for item in base:
        by_client[(item['client_id'],item['topic'])].append(item)
    for key,group in by_client.items():
        group.sort(key=lambda item:item['created'])
    # 4. Проверяем, обращался ли клиент повторно
    #    по той же известной теме в течение семи дней.
    for item in base:
        item['came_back']=0
        item['next_bot_result']=None
        if item['topic'] in ('без темы','NULL'):
            continue
        follow=by_client[(item['client_id'],item['topic'])]
        # У одного клиента мало обращений, поэтому достаточно обычного цикла.
        for other in follow:
            days=(other['created']-item['created']).total_seconds()/86400
            if 0 < days <=7:
                item['came_back']=1
                item['next_bot_result']=other['bot_result']
                break
            if days>7:break

    # 5. Сохраняем обработанные обращения в таблицу clean.
    con.execute("""create table clean (
       id text,num integer,created text,period text,month text,client_id text,
       channel text,written integer,topic text,priority integer,bot_result text,
       agent_id text,handle_min real,first_reply_min real,resolve_hours real,
       status text,reopened integer,csat integer,came_back integer,next_bot_result text)""")
    base.sort(key=lambda item:item['num'])
    clean=[]
    for r in base:
        stamp=r['created'].strftime('%Y-%m-%d %H:%M:%S')
        clean.append((r['id'],r['num'],stamp,'после' if stamp>='2025-04-01' else 'до',
                      stamp[:7],r['client_id'],r['channel'],int(r['channel']!='телефон'),
                      r['topic'],r['priority'],r['bot_result'],r['agent_id'],r['handle_min'],
                      r['first_reply_min'],r['resolve_hours'],r['status'],r['reopened'],r['csat'],
                      r['came_back'],r['next_bot_result']))
    con.executemany('insert into clean values (%s)' % ','.join('?' for _ in range(20)),clean)
    # 6. Подключаем разметку: первая линия, вторая или серая зона.
    rules=read(root/'data/segments.csv')
    con.execute('create table segments (topic text,priority integer,blok text)')
    con.executemany('insert into segments values (?,?,?)',
                    ((r['topic'],int(r['priority']),r['blok']) for r in rules))
    con.execute("""create view razmetka as select c.*,
                     coalesce(s.blok,'не размечено') as blok
                     from clean c left join segments s
                     on c.topic=s.topic and c.priority=s.priority""")
    return con

