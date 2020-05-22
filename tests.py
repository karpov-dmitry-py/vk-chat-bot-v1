import datetime
import unittest
from copy import deepcopy
from unittest.mock import Mock, patch
from vk_api.bot_longpoll import VkBotMessageEvent
from bot import Bot
import settings
import handlers


class BotTester(unittest.TestCase):
    RAW_EVENT = {'type': 'message_new', 'object':
        {'message':
             {'date': 1587332208, 'from_id': 33275712, 'id': 57, 'out': 0, 'peer_id': 33275712,
              'text': 'привет бот бот', 'conversation_message_id': 56, 'fwd_messages': [], 'important': False,
              'random_id': 0, 'attachments': [], 'is_hidden': False},
         'client_info':
             {'button_actions': ['text', 'vkpay', 'open_app', 'location', 'open_link'], 'keyboard': True,
              'inline_keyboard': True, 'lang_id': 0}
         },
                 'group_id': 194067238,
                 'event_id': '542d338cd56ad36f72f1de38b0a09db1d43ba927'
                 }

    STEPS = settings.SCENARIOS['ticket']['steps']

    CONTEXT = {}
    CONTEXT['initial_user_input'] = 'Привет, хочу билет !!!'
    CONTEXT['user_input_from_'] = 'мОСкВ'
    CONTEXT['user_input_to_'] = 'екаТеРр'
    CONTEXT['from_'] = 'Москва'
    CONTEXT['to_'] = 'Екатеринбург'
    CONTEXT['when_'] = datetime.datetime(year=2020, month=7, day=1)
    CONTEXT['time'] = datetime.time(hour=9, minute=0)
    CONTEXT['datetime'] = datetime.datetime.combine(CONTEXT['when_'], CONTEXT['time'])
    CONTEXT['flight_id'] = 555
    CONTEXT['tickets_qty'] = 4
    CONTEXT['comment'] = 'просьба прислать электронный чек на телефон вместе с билетами'
    CONTEXT['answer'] = 'дА'
    CONTEXT['bad_phone'] = '+7926777885'
    CONTEXT['phone'] = '+79267778855'

    FAKE_FLIGHTS = {
        CONTEXT['flight_id']: {
            'id': CONTEXT['flight_id'],
            'from_': CONTEXT['from_'],
            'to_': CONTEXT['to_'],
            'when_': CONTEXT['datetime'],
            'price': 4000.0
        },
        777: {
            'id': 777,
            'from_': CONTEXT['from_'],
            'to_': CONTEXT['to_'],
            'when_': CONTEXT['datetime'] + datetime.timedelta(days=1),
            'price': 4500.0
        }
    }

    # дополним контекст
    CONTEXT['flights'] = FAKE_FLIGHTS
    CONTEXT['flights_as_str'] = handlers.get_flights_as_str(FAKE_FLIGHTS)
    CONTEXT['flight'] = FAKE_FLIGHTS.get(CONTEXT['flight_id'])
    CONTEXT['flight_when_'] = CONTEXT['flight']['when_']
    CONTEXT['summary'] = handlers.get_summary_as_str(CONTEXT)

    INPUTS = (
        CONTEXT['initial_user_input'],  # начало чата
        settings.SCENARIOS['ticket']['help_token'],  # Help или /help
        settings.SCENARIOS['ticket']['main_token'],  # Ticket или заказать
        CONTEXT['user_input_from_'],  # откуда
        CONTEXT['user_input_to_'],  # куда
        CONTEXT['when_'].strftime('%d-%m-%Y'),  # желаемая дата вылета
        str(CONTEXT['flight_id']),  # ID рейса
        str(CONTEXT['tickets_qty']),  # кол-во билетов
        CONTEXT['comment'],  # комментарий к заказу
        CONTEXT['answer'],  # подтверждение summary
        CONTEXT['bad_phone'],  # не верный формат номера телефона
        CONTEXT['phone']  # верный формат номера телефона
    )

    EXPECTED_OUTPUTS = [
        settings.DEFAULT_ANSWER,  # начало чата
        Bot.get_help_message(),  # помощь
        STEPS.get(1)['text'],  # введите откуда
        STEPS.get(2)['text'].format(**CONTEXT),  # введите куда
        STEPS.get(3)['text'].format(**CONTEXT),  # введите желаемую дату вылета
        STEPS.get(4)['text'].format(**CONTEXT),  # введите ID рейса
        STEPS.get(5)['text'].format(**CONTEXT),  # введите кол-во билетов
        STEPS.get(6)['text'].format(**CONTEXT),  # введите комментарий
        STEPS.get(7)['text'].format(**CONTEXT),  # подтверждение комментария
        STEPS.get(8)['text'],  # введите номер телефон
        STEPS.get(8)['failure_text'],  # вы ввели неверный формат номера телефона
        STEPS.get(9)['text'].format(**CONTEXT)  # успех! спасибо, с Вами свяжется наш сотрудник
    ]

    DEPARTURES = ['Москва', 'Нижний Новгород']
    ARRIVALS = ['Екатеринбург', 'Сочи']

    @patch('bot.vk_api.VkApi')
    def test_bot_run(self, *args, **kwargs):
        events_qty = 10
        event = {'key': 'value'}
        fake_events = [event] * events_qty
        fail_event = {'key': 'some other value'}  # для тестов
        poller = Mock()

        with patch('bot.VkBotLongPoll', return_value=poller):
            poller.listen = Mock(return_value=fake_events)
            bot = Bot('', '')
            bot.on_event = Mock()
            bot.poller = poller
            bot.run()

            bot.on_event.assert_called()
            bot.on_event.assert_called_with(event)
            self.assertEqual(bot.on_event.call_count, events_qty)

            with self.assertRaises(Exception):
                bot.on_event.assert_called_once()

            with self.assertRaises(Exception):
                bot.on_event.assert_called_with(fail_event)

    def test_bot_run_scenario(self):

        events = []
        for input_line in self.INPUTS:
            event = deepcopy(self.RAW_EVENT)
            event['object']['message']['text'] = input_line
            events.append(VkBotMessageEvent(event))

        send_mock = Mock()
        api_mock = Mock()
        api_mock.messages.send = send_mock

        long_poller_mock = Mock()
        long_poller_mock.listen = Mock(return_value=events)

        tickets_api_mock = Mock()
        tickets_api_mock.get_tickets = Mock(return_value=self.FAKE_FLIGHTS)
        tickets_api_mock.get_departure_locations = self.DEPARTURES
        tickets_api_mock.get_arrival_locations = self.ARRIVALS
        tickets_api_mock.is_route_available = Mock(return_value=True)

        with patch('bot.VkBotLongPoll', return_value=long_poller_mock):
            bot = Bot('', '')
            bot.api = api_mock
            bot.tickets_api = tickets_api_mock
            bot.departures = tickets_api_mock.get_departure_locations
            bot.arrivals = tickets_api_mock.get_arrival_locations
            bot.run()

        actual_results = []
        for call in send_mock.call_args_list:
            args, kwargs = call
            actual_results.append(kwargs['message'])

        assert actual_results == BotTester.EXPECTED_OUTPUTS
        assert send_mock.call_count == len(BotTester.EXPECTED_OUTPUTS)

        with self.assertRaises(BaseException):
            bot.send_mock.assert_not_called()

        with self.assertRaises(BaseException):
            bot.send_mock.assert_called_with('some message')


if __name__ == '__main__':
    unittest.main()
