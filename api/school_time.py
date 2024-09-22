import json
import datetime
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import os

hashes_symbols = f'\n{"-" * 10}\n{" " * 3}'
show_logs = True


async def get_pastebin(paste_key: str):
    url = f'https://pastebin.com/raw/{paste_key}'
    answer = ""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                answer = await response.text()
                if show_logs:
                    print(f"{hashes_symbols}pastekey: {paste_key} is worked!{hashes_symbols}")
            else:
                print(f'{hashes_symbols}Failed to retrieve the raw paste.{hashes_symbols}')
                answer = "error"
    return answer


class Calendar:
    month: int = 0
    day: int = 0
    week: int = 0
    weekday = datetime.datetime.today().weekday()
    is_odd_week_state: bool = False
    current_date = datetime.date.today()  # Храним текущую дату
    
    def __init__(self):
        self.month, self.day = int(str(self.current_date)[5:7]), int(str(self.current_date)[8:10])
    
    async def is_odd_week(self, date=None):
        if not date:
            date = self.current_date  # Используем current_date
        current_week = date.isocalendar()[1]  # Получаем номер недели
        print("date:", date)
        return current_week % 2 != 0  # Возвращаем True, если неделя нечётная
    
    async def update_week_state(self, date=None):
        if not date:
            date = self.current_date  # Используем current_date
        self.is_odd_week_state = await self.is_odd_week(date)
        print("updated is", "odd" if self.is_odd_week_state else "even")
    
    async def set_day_offset(self, day_offset):
        # Рассчитываем новую дату на основе смещения от сегодняшнего дня
        self.current_date = datetime.date.today() + datetime.timedelta(days=day_offset)
        self.weekday = self.current_date.weekday()  # Обновляем текущий день недели
        await self.update_week_state(self.current_date)  # Проверяем состояние недели для новой даты
    
    async def rus_weekday(self):
        return ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"][self.weekday] if -1 < self.weekday < 7 else -1
    
    async def date(self):
        return self.current_date  # Возвращаем current_date




class College:
    subject_data_dict = {}
    group_num = None
    lections_time_list = [
        "9:00 - 10:30", "10:40 - 12:10",
        "12:50 - 14:20", "14:30 - 16:00",
        "16:10 - 17:40", "17:50 - 19:20"
    ]

    # В College заменяем синхронный вызов get_subject_data_dict на асинхронный
    
    def __init__(self, group_num: int = 1):
        self.group_num = group_num
        self.subject_data_dict = asyncio.run( self.get_subject_data_dict() )  # Используем await вместо asyncio.run
    
    async def get_subject_data_dict(self) -> dict:
        return eval(str(await get_pastebin("qcTPMBZb")))
    
    def get_subject(self, id: int, index: int = 0):
        subject, cabinet = self.subject_data_dict[id]
        index_list = [-1]
        result = []
        [index_list.append(i) if symbol in ["-", "&"] else ... for i, symbol in enumerate(cabinet)]
        index_list.append(len(cabinet))

        [result.append(cabinet[index_list[i] + 1:index_list[i + 1]]) for i in range(len(index_list) - 1)]

        if index != -1 and index + 1 > len(result):
            index = 0
        return (subject, result[index]) if index != -1 else (subject, result)


class Schedule:
    schedule_dict = {}
    whole_dict: dict
    raw_schedule_from_pastebin:str
    
    def __init__(self):
        self.raw_schedule_from_pastebin = asyncio.run(get_pastebin("7bTcEdX0"))
        asyncio.run(self.generate_raw_schedule())
    
    async def generate_raw_schedule(self):
        self.whole_dict = eval(
            str(self.raw_schedule_from_pastebin)
            .replace("sub", "rtu.get_subject")
            .replace("ind_", f"index={rtu.group_num - 1}")
        )
    
    async def create_schedule(self):
        #print("создаём расписание для группы",rtu.group_num, "день =", calendar.weekday)
        odd_week = 1 if calendar.is_odd_week_state else 0
        week_list = self.whole_dict[calendar.weekday+1][odd_week] if calendar.weekday < 6 else None
        if not week_list or week_list == [None]:
            print("Сегодня нету уроков!")
            return "N"
        self.schedule_dict = {i+1: week_list[i] for i in range(len(week_list))}
        return self.schedule_dict



# Инициализация:
rtu = College(group_num=1)
calendar = Calendar()
schedule = Schedule()

async def create_and_return_for_bot(day_offset=0):
    # Устанавливаем дату на основе переданного смещения от сегодняшнего дня
    await calendar.set_day_offset(day_offset)
    
    res = await schedule.create_schedule()
    print(await calendar.date())
    if show_logs:
        print(await calendar.rus_weekday())
    return res



async def test():
    offset_in_days = 0
    user_group = rtu.group_num
    schedule_array = await create_and_return_for_bot(offset_in_days)
    subject_order_list = f";|n- ".join(
        [
            ", ".join(
                schedule_array[i] if schedule_array[i] != () else "^") for i in range(
                    1, len(schedule_array)+1 
                )
            ]
        )
    print("schedule len =", len(schedule_array))
    # Формируем ответное сообщение для расписания
    message_back = f"""{f"Будующее на {offset_in_days} шаг(а)" if offset_in_days > 0 else "Сегодня" if offset_in_days == 0 else f"Прошлое на {offset_in_days} шаг(а)"}: {await calendar.date()}, {"нечётная (жёлтая)" if calendar.is_odd_week_state else "чётная (белая)"} неделя.
|nРасписание для {user_group}-ой группы:|n- { subject_order_list };""".replace("\n","").replace("|n", "\n").replace("^", "Нету пары")
    print(schedule_array, subject_order_list, "\n" ,message_back)

    #lp.print_stats()

if __name__ == "__main__":
    asyncio.run(test())

