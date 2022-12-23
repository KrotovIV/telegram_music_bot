import json

import telebot
from telebot import types
from yandex_music import Client
import os
import schedule
from threading import Thread
from time import sleep

telegram_token = '5235499125:AAEIV0Xurji0IJTAnPUTWYx7u8z_sFtzb3U'

bot = telebot.TeleBot(telegram_token)

charts = []

modes = {}  # 0 - обычный, 1 - режим выбора, 2 - режим выбора из альбома по сслыке, 3 - режим выбора из чарта

users_data = {}

start_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
add_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
delete_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

start_keyboard = [['.Показать ваш плейлист'], ['.Создать ссылку на плейлист'], ['.'], ['.']]
add_keyboard = [['.Показать ваш плейлист'], ['.Создать ссылку на плейлист'], ['✅Добавить в плейлист✅'],
                ['.Показать текст']]
delete_keyboard = [['.Показать ваш плейлист'], ['.Создать ссылку на плейлист'], ['❌Удалить из плейлиста❌'],
                   ['.Показать текст']]

for button in start_keyboard:
    start_markup.add(types.KeyboardButton(button[0]))
for button in add_keyboard:
    add_markup.add(types.KeyboardButton(button[0]))
for button in delete_keyboard:
    delete_markup.add(types.KeyboardButton(button[0]))

yand_token = 'y0_AgAAAAAhzfzwAAG8XgAAAADXeV_R4rx1X9cgSH67vBdksj5B7Ev_rI8'
client = Client(yand_token).init()


class Song_List:
    def __init__(self):
        self.filename = 'data.json'

    def create_deep_link(self, chat_id):
        return f'https://t.me/krotow_bot?start=playlist_user_id_{chat_id}'

    def add_song_to_list(self, name: str, chat_id: int):
        with open(self.filename, 'r') as file:
            dict = json.load(file)
        if str(chat_id) in dict.keys():
            if name not in dict[str(chat_id)]:
                dict[str(chat_id)].append(name)
        else:
            dict[str(chat_id)] = [name]
        with open(self.filename, 'w') as file:
            json.dump(dict, file, ensure_ascii=False)

    def get_song_list(self, chat_id):
        with open(self.filename, 'r') as file:
            dict = json.load(file)
        return dict[str(chat_id)] if str(chat_id) in dict.keys() else 'Пусто'

    def delete_song(self, chat_id, name):
        with open(self.filename, 'r') as file:
            dict = json.load(file)
        del dict[str(chat_id)][dict[str(chat_id)].index(name)]
        if not dict[str(chat_id)]:
            del dict[str(chat_id)]
        with open(self.filename, 'w') as file:
            json.dump(dict, file, ensure_ascii=False)

class Search:
    def __init__(self):
        pass

    def search(self, name):
        track_id, album_id, search_result = self.get_ides(name)
        try:
            artist_name = search_result['best']['result']['artists'][0]['name']
            song_name = search_result['best']['result']['title']
            if f'{artist_name} - {song_name}.mp3' not in os.listdir(
                    'C:\\Users\\User\\PycharmProjects\\bot_proj\\tracks'):
                self.download_song(track_id, album_id, f'{artist_name} - {song_name}')
            return artist_name, song_name
        except KeyError:
            return "Такую песню я не знаю"
        except TypeError:
            return "Такую песню я не знаю"

    def download_song(self, track_id, album_id, name):
        inf = client.tracks_download_info(track_id)[0]
        tr = client.tracks(f'{track_id}:{album_id}')[0]
        tr.download(f'tracks/{name}.mp3', codec=inf['codec'],
                                                            bitrate_in_kbps=inf['bitrate_in_kbps'])



    def get_ides(self, name):
        search_result = json.loads(client.search(name).to_json())
        track_id = search_result['best']['result']['id']
        album_id = search_result['best']['result']['albums'][0]['id']
        return track_id, album_id, search_result


SONGLIST = Song_List()
SEARCH = Search()


def schedule_checker():
    while True:
        schedule.run_pending()
        sleep(1)

def print_song_list(chat_id, chat_id_albumowner=None):
    if not chat_id_albumowner: chat_id_albumowner = chat_id
    spisok = SONGLIST.get_song_list(chat_id_albumowner)
    if not spisok:
        bot.send_message(chat_id, 'Пусто', reply_markup=start_markup)
    else:
        # красивый вид списка
        spisok = list(enumerate(spisok, start=1))
        spisok = list(map(lambda x: f'{x[0]} - {x[1]}', spisok))
        spisok = '\n'.join(spisok)

        bot.send_message(chat_id, spisok, reply_markup=start_markup)

        global modes, users_data
        modes[chat_id] = 1
        if chat_id != chat_id_albumowner:
            spisok = SONGLIST.get_song_list(chat_id_albumowner)
            users_data[chat_id]['playlist_link'] = spisok


def get_name_by_num(chat_id, num, spisok=None):
    if not spisok:
        spisok = SONGLIST.get_song_list(chat_id)
    if 0 < int(num) <= len(spisok):
        return spisok[int(num) - 1]

def link(chat_id):
    link_ = SONGLIST.create_deep_link(chat_id)
    bot.send_message(chat_id, link_)


def add_song_to_songlist(chat_id, name):
    SONGLIST.add_song_to_list(name, chat_id)
    bot.send_message(chat_id, 'успешно', reply_markup=start_markup)


def delete_song_from_songlist(chat_id, name):
    SONGLIST.delete_song(chat_id, name)
    bot.send_message(chat_id, 'Успешно', reply_markup=start_markup)
    global modes, users_data
    modes[chat_id] = 0
    users_data[chat_id]['last'] = ''

def play_song(chat_id, name, spisok=None):
    artist_name, song_name = SEARCH.search(name)
    name = f"{artist_name} - {song_name}"
    with open(f'tracks/{name}.mp3', 'rb') as r:
        if not spisok:
            spisok = SONGLIST.get_song_list(chat_id)
        if name not in spisok:
            bot.send_message(chat_id, name, reply_markup=add_markup)
        elif spisok != 'Пусто' and name in spisok:
            bot.send_message(chat_id, name, reply_markup=delete_markup)
        bot.send_audio(chat_id, r)
    global users_data
    users_data[chat_id]['last'] = name

def get_text(trackid):
    return client.track_supplement(trackid)['lyrics']['full_lyrics']


@bot.message_handler(commands=['start'])
def start_message(message):
    with open('users.json', 'r') as file:
        dict = json.load(file)
    if str(message.chat.id) not in dict['users']:
        dict['users'].append(str(message.chat.id))
        with open('users.json', 'w') as file:
            json.dump(dict, file, ensure_ascii=False)

    global modes, users_data

    modes[message.chat.id] = 0  # обычный
    users_data[message.chat.id] = {'last': '', 'playlist': 'self'}
    # запуск с аргументами
    if len(message.text.split(maxsplit=1)) > 1:
        chat_id_ = message.text.split(maxsplit=1)[1].split('playlist_user_id_')[1]
        print_song_list(message.chat.id, chat_id_)
        users_data[message.chat.id]['playlist'] = 'link'
        modes[message.chat.id] = 2
    # запуск без аргументов
    else:
        bot.send_message(message.chat.id, 'Привет! Я музыкальный бот. Любишь слушать музыку? Тогда пиши название песни, и я найду ее для тебя!', reply_markup=start_markup)

@bot.message_handler(commands=['top10'])
def top10(message):
    print('top 10')
    global charts, modes
    with open('users.json', 'r') as file:
        chat_ids = json.load(file)['users']

    spisok = list(map(lambda x: f"{x['track']['artists'][0]['name']}  -  {x['track']['title']}",
                      client.chart()['chart']['tracks'][:10]))
    charts = spisok.copy()
    spisok = list(map(lambda x: f"{x[0] + 1} - {x[1]}", list(enumerate(spisok))))
    spisok.insert(0, f'🔥 TOP 🔟 🔥')
    spisok = '\n'.join(spisok)
    for elem in chat_ids:
        bot.send_message(elem, spisok)
        modes[int(elem)] = 3

@bot.message_handler(commands=['add'])
def test_add(message):
    print(message.chat.id)
    if len(message.text.split(maxsplit=1)) > 1:
        name = message.text.split(maxsplit=1)[1]
        add_song_to_songlist(message.chat.id, name)

@bot.message_handler(content_types=['text'])
def echo(message):
    print(message.text)
    chat_id = message.chat.id
    global modes, users_data
    if message.text == '.Показать ваш плейлист':
        print_song_list(chat_id)
    elif message.text == '✅Добавить в плейлист✅':
        name = users_data[chat_id]['last']
        add_song_to_songlist(chat_id, name)
    elif message.text == '❌Удалить из плейлиста❌':
        name = users_data[chat_id]['last']
        delete_song_from_songlist(chat_id, name)
    elif message.text == '.Создать ссылку на плейлист':
        link(chat_id)
    elif message.text == '.Показать текст':
        name = users_data[chat_id]['last']
        response = SEARCH.get_ides(name)
        track_id, album_id = response[0], response[1]
        lyrics = get_text(track_id)
        bot.send_message(chat_id, lyrics)
    else:
        if chat_id not in modes.keys():
            modes[chat_id] = 0
            users_data[chat_id] = {'last': '', 'playlist': 'self'}
        #просто поиск
        if modes[chat_id] == 0:
            if not message.text[0] == '/':
                play_song(chat_id, message.text)
        # плейлист
        elif modes[chat_id] == 1:
            if message.text.isnumeric():
                name = get_name_by_num(chat_id, message.text)
                if name:
                    play_song(chat_id, name)
                else:
                    bot.send_message(chat_id, "Неправильный номер")
            else:
                modes[chat_id] = 0
                play_song(chat_id, message.text)
        # плейлист по ссылке
        elif modes[chat_id] == 2:
            if message.text.isnumeric():
                if 'playlist_link' in users_data[chat_id].keys():
                    spisok = users_data[chat_id]['playlist_link']
                    name = get_name_by_num(chat_id, message.text, spisok)
                    if name:
                        play_song(chat_id, name, spisok)
                    else:
                        bot.send_message(chat_id, "Неправильный номер")
            else:
                modes[chat_id] = 0
                play_song(chat_id, message.text)
        # чарты
        elif modes[chat_id] == 3:
            if message.text.isnumeric():
                global charts
                name = get_name_by_num(chat_id, message.text, charts)
                if name:
                    play_song(chat_id, name, charts)
                else:
                    bot.send_message(chat_id, "Неправильный номер")
            else:
                modes[chat_id] = 0
                play_song(chat_id, message.text)

def main():
    with open('users.json', 'r') as file:
        users_ids = json.load(file)['users']
    for id in users_ids:
        modes[int(id)] = 0
        users_data[int(id)] = {'last': '', 'playlist': 'self'}

    schedule.every().saturday.at("10:30").do(top10, 'message')
    Thread(target=schedule_checker).start()
    bot.infinity_polling()





if __name__ == '__main__':
    main()

