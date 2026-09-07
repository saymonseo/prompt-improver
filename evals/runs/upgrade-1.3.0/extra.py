import argparse
import json
from pathlib import Path
from run import ROOT, WRAPPER, call, extract, save, spec_input, write

USERS=[
 'Помоги поставить задачу для нейросети: хочу автоматизировать обработку заказов из таблицы.',
 'Нужна пока только схема процесса для обсуждения с менеджером. В учебной таблице есть номер заказа, сумма и телефон. После появления заказа нужна карточка и уведомление менеджеру. Подключений пока нет. Остальные детали неизвестны.',
 'Продолжим предложенную следующую тему.',
 'Этих сведений пока не знаю. На этом хватит, собери один копируемый промпт для нового чата. Не выбирай за меня сервис, число повторов и способ связи. Следующей модели нужен текст схемы до 300 слов, без подключения и отправки сообщений.'
]
def briefing(condition):
    folder=ROOT/('briefing' if condition=='candidate' else 'briefing-r2');history=[]
    save(folder/'users.json',USERS)
    for n,user in enumerate(USERS,1):
        history.append({'role':'user','text':user})
        transcript='\n\n'.join(x['role']+':\n'+x['text'] for x in history)
        answer=call(folder,f'turn-{n}',WRAPPER+spec_input(condition,'modular')+'\n\nСОСТОЯВШИЙСЯ РАЗГОВОР:\n'+transcript)
        history.append({'role':'assistant','text':answer});save(folder/'dialogue.json',history)
        print('briefing',n,'complete',flush=True)
    prompt,method=extract(answer);write(folder/'prompt.txt',prompt);save(folder/'extraction.json',{'method':method,'edited':False})

def execute(condition):
    wrapper='''Выполни пользовательское задание ниже. Не улучшай промпт и не используй скилл prompt-improver. Не создавай агентов и не читай локальные материалы. Все данные учебные; достаточно текстового ответа без внешних действий.\n\nЗАДАНИЕ:\n'''
    for ident in ('01-state','04-text','08-limits'):
        path=ROOT/'runs'/condition/ident/'prompt.txt'
        if not path.exists():raise RuntimeError('Prompt not ready: '+ident)
        call(ROOT/('executions' if condition=='candidate' else 'executions-r2')/ident,'answer',wrapper+path.read_text(encoding='utf-8'))
        print('execution',ident,'complete',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['briefing','execute']);p.add_argument('--condition',default='candidate');a=p.parse_args()
    briefing(a.condition) if a.mode=='briefing' else execute(a.condition)
