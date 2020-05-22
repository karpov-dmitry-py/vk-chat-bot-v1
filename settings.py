TOKEN = '' # actual token required here.
GROUP_ID = 194067238

SCENARIOS = {
    'ticket': {
        'main_token': '/ticket',
        'help_token': '/help',
        'quit_token': '/quit',

        'steps': {
            1: {
                'text': 'Начинаем оформление билета!\nПотребуется ввести необходимые данные на кириллице.\n'
                        'Укажите, пожалуйста, город вылета (мин. 4 символа):',
                'failure_text': 'Не удается определить город вылета. Доступны рейсы из указанных ниже городов:\n' \
                                '{departures}\n'
                                'Введите город вылета:',
                'handler': 'handle_departure',
                'step_number': 1,
            },
            2: {
                'text': 'Вы ввели {from_}.\nУкажите, пожалуйста, город прибытия (мин. 4 символа):',
                'failure_text': 'Не удается определить город прибытия. Доступны рейсы в указанные ниже города:\n' \
                                '{arrivals}\n'
                                'Введите город прибытия:',
                'handler': 'handle_arrival',
                'step_number': 2,
            },
            3: {
                'text': 'Вы ввели {to_}.\nУкажите, пожалуйста, плановую дату вылета в формате дд-мм-гггг, например, 31-05-2020',
                'failure_text': 'Введенная дата некорректна или уже прошла. Попробуйте снова:',
                'handler': 'handle_date',
                'step_number': 3,
            },
            4: {
                'text': 'Вы ввели {when_}.\nВот доступные рейсы по Вашим параметрам (показаны 5 рейсов):\n\n' \
                        '{flights_as_str}\n' \
                        'Введите, пожалуйста, ID нужного рейса:',
                'failure_text': 'Введен некорректный ID рейса. Попробуйте снова:',
                'handler': 'handle_flight_id',
                'step_number': 4,
            },
            5: {
                'text': 'Вы ввели ID рейса: {flight_id}.\nУкажите, пожалуйста, нужное кол-во билетов (от 1 до 5):',
                'failure_text': 'Введено не верное количество билетов. Попробуйте снова:',
                'handler': 'handle_tickets_qty',
                'step_number': 5,
            },
            6: {
                'text': 'Вы ввели кол-во билетов: {tickets_qty}.\nУкажите, пожалуйста, комментарий к Вашему заказу (например, ФИО покупателя или ' \
                        'желаемый способ оплаты билета',
                'failure_text': None,
                'handler': 'handle_comment',
                'step_number': 6,
            },
            7: {
                'text': 'Проверьте, пожалуйста, Ваши данные:\n\n'
                        '{summary}\n' \
                        'Если всё верно, введите "да". Если есть ошибки, введите "нет":',
                'failure_text': 'Неверный ввод ("да" или "нет"). Попробуйте снова:',
                'handler': 'handle_summary',
                'step_number': 7,
            },
            8: {
                'text': 'Укажите, пожалуйста, Ваш номер телефона в формате +7XXXXXXXXXX :',
                'failure_text': 'Неверный ввод телефона. Попробуйте снова:',
                'handler': 'handle_phone',
                'step_number': 8,
            },
            9: {
                'text': 'Спасибо за Ваш заказ! С Вами свяжется наш сотрудник по указанному номеру телефона ({phone}) в ближайшее '
                        'время!',
                'failure_text': None,
                'handler': None,
                'step_number': 9,
            }
        }
    },
}

TICKET_SCENARIO = SCENARIOS["ticket"]
INTENTS = [
    {
        'name': 'заказ билетов',
        'tokens': (
            TICKET_SCENARIO["main_token"], 'ticket', 'заказать', 'заказ билета', 'заказ авиабилета',
            'купить билет' 'купить авиабилет',
            'приобрести билет', 'приобрести авиабилет', 'оформить билет', 'оформить авиабилет'
        ),
        'scenario': 'ticket',
        'answer': None
    },
    {
        'name': 'помощь',
        'tokens': (TICKET_SCENARIO["help_token"], 'help', 'как', 'помогите', 'расскажите'),
        'scenario': None,
        'answer': f'Для заказа билета введите текст {TICKET_SCENARIO["main_token"]}, далее по запросу системы '
                  f'введите город вылета, город прибытия, дату, количество билетов и номер телефона.'

    }
]


DEFAULT_ANSWER = f'Давайте уточним, о чем речь.\nДля заказа авиабилета напишите {TICKET_SCENARIO["main_token"]}.\n' \
                 f'Для справки напишите {TICKET_SCENARIO["help_token"]}.\nДля выхода из процесса заказа на любом этапе ' \
                 f'напишите {TICKET_SCENARIO["quit_token"]}.'