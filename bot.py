# run tickets.py first to create DB and tickets in it

import logging
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import random
import handlers
from tickets import Dispatcher

try:
    from settings import TOKEN, GROUP_ID # actual token required in settings.py.
    from settings import SCENARIOS, INTENTS, DEFAULT_ANSWER

except ImportError:
    print(f'Ошибка импорта. Нужен файл settings.py с токеном и id группы в vk')
    exit(1)

MAIN_TOKEN = SCENARIOS['ticket']['main_token']
HELP_TOKEN = SCENARIOS['ticket']['help_token']
QUIT_TOKEN = SCENARIOS['ticket']['quit_token']


class UserState:
    '''Состояние пользователя в сценарии'''

    def __init__(self, scenario, step, context=None):
        self.scenario = scenario
        self.step = step
        self.context = context or {}


class Bot:
    """ Эхо бот для работы с vk api """

    def __init__(self, token, group_id):
        self.token = token
        self.group_id = group_id

        self.vk = vk_api.VkApi(token=self.token)
        self.poller = VkBotLongPoll(self.vk, self.group_id)
        self.api = self.vk.get_api()

        self.tickets_api = Dispatcher()
        self.departures = self.tickets_api.get_departure_locations()
        self.arrivals = self.tickets_api.get_arrival_locations()

        self.user_states = {}
        self._setup_logging()

    def _setup_logging(self):
        """ Настройка логирования """

        logger = logging.getLogger('bot_logger')
        logger.setLevel(logging.DEBUG)
        time_format = '%d-%m-%Y %H:%M'
        formatter = logging.Formatter('{asctime} - {name} - {levelname} - {message}', datefmt=time_format, style='{')

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)

        file_handler = logging.FileHandler('bot.log', 'a', 'utf8', True)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)

        self.logger = logger

    @classmethod
    def get_help_message(cls):
        for intent in INTENTS:
            if intent['name'] == 'помощь':
                return intent['answer']

    def start_scenario(self, scenario_name, user_id):
        scenario = SCENARIOS.get(scenario_name)
        first_step = scenario['steps'].get(1)
        text_to_send = first_step['text']
        self.user_states[user_id] = UserState(scenario_name, first_step)
        return text_to_send

    def continue_scenario(self, user_id, text):
        state = self.user_states[user_id]
        context = state.context
        steps = SCENARIOS[state.scenario]['steps']
        step = state.step
        handler = getattr(handlers, step['handler'])

        if handler(self, user_id, text):

            # обработать переход на следующий шаг
            next_step_number = state.step['step_number'] + 1
            next_step = steps[next_step_number]
            text_to_send = next_step['text'].format(**state.context)
            state.step = next_step

            # это последний шаг в сценарии
            if next_step_number == len(steps):
                summary = state.context['summary']
                self.logger.info(
                    f'{">>>>> оформлен новый заказ от пользователя".upper()} (ID: {user_id}):\n{summary}\n')
                self.quit_scenario(user_id)

        # завершаем сценарий по сигналу от handler
        elif context.get('quit_message') is not None:
            text_to_send = context.get('quit_message')
            self.quit_scenario(user_id)
            # нужно начать новый заказ для пользователя
            if context.get('start_over') is True:
                start_over_message = self.start_scenario('ticket', user_id)
                text_to_send = f'{text_to_send}\n\n{start_over_message}'

        else:
            text_to_send = step['failure_text'].format(**state.context)

        return text_to_send

    def quit_scenario(self, user_id):
        self.user_states.pop(user_id)

    def on_event(self, event):

        """ Обработка событий """

        if event.type != VkBotEventType.MESSAGE_NEW:
            self.logger.debug(f'Пришло неизвестное событие с типом: {event.type}')
            self.logger.debug(f'Текст сообщения неизвестного события: {event.obj.text}')
            return

        user_id = event.obj.message['peer_id']
        user_text = event.object.message['text'].strip().lower()

        if user_id in self.user_states:

            if user_text == MAIN_TOKEN:
                self.quit_scenario(user_id)
                text_to_send = self.start_scenario('ticket', user_id)

            elif user_text == HELP_TOKEN:
                self.quit_scenario(user_id)
                text_to_send = Bot.get_help_message()

            elif user_text == QUIT_TOKEN:
                self.quit_scenario(user_id)
                text_to_send = 'Вы выбрали завершить оформление билета. Всего Вам хорошего!'

            # продолжить по сценарию
            else:
                text_to_send = self.continue_scenario(user_id, user_text)

        else:
            # искать интент
            for intent in INTENTS:
                if any(token in user_text for token in intent['tokens']):
                    # запустить новый интент
                    if intent['answer']:
                        text_to_send = intent['answer']
                    else:
                        text_to_send = self.start_scenario('ticket', user_id)
                    break

            else:
                text_to_send = DEFAULT_ANSWER

        # # отправим наше сообщение в ответ
        random_id = random.randint(3 ** 20, 9 ** 20)
        self.api.messages.send(peer_id=user_id,
                               random_id=random_id,
                               message=text_to_send
                               )

    def run(self):

        """ Запуск бота на исполнение """

        for event in self.poller.listen():
            try:
                self.on_event(event)
            except BaseException as exc:
                self.logger.exception(f'Произошла ошибка (исключение): {exc.__class__.__name__, exc.args}')


def main():
    bot = Bot(TOKEN, GROUP_ID)
    bot.run()


if __name__ == '__main__':
    main()
