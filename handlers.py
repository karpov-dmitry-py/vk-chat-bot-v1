''' Обработчики шагов сценария '''
import datetime
import re

LOCATION_PATTERN = re.compile(r'([a-яё-]{3,})([a-яё]+$)', re.IGNORECASE)
YES_NO_PATTERN = re.compile(r'да|нет', re.IGNORECASE)
PHONE_PATTERN = re.compile(r'\+7\d{10}$')


def get_context(bot, user_id):
    return bot.user_states[user_id].context


def get_flight_as_str(flight):
    return f'ID: <{flight.get("id")}>, вылет {flight["when_"].strftime("%d.%m.%Y %H:%M")} ' \
           f'{flight["from_"]} --> {flight["to_"]}, цена: {flight["price"]} руб.'


def get_flights_as_str(flights):
    return '\n\n'.join(map(get_flight_as_str, flights.values()))


def get_summary_as_str(context):
    flight = context['flight']
    price = flight['price']
    tickets_qty = context['tickets_qty']

    summary = {}
    summary['Город вылета'] = context['from_']
    summary['Город прибытия'] = context['to_']
    summary['Дата и время вылета'] = context['flight_when_']
    summary['Цена, руб.'] = price
    summary['Кол-во билетов'] = tickets_qty
    summary['Итого сумма, руб.'] = tickets_qty * price
    summary['Комментарий к заказу'] = context['comment']

    result = ''
    for key, value in summary.items():
        result += f'{key}: {value}\n'

    return result


def handle_location(bot, user_id, user_text, is_departure=True):
    locations = 'departures' if is_departure else 'arrivals'
    direction = 'from_' if is_departure else 'to_'

    context = get_context(bot, user_id)
    actual_locations = getattr(bot, locations)  # departures или arrivals
    match = re.search(LOCATION_PATTERN, user_text)

    if match:
        user_location = match.group(1)
        for location in actual_locations:
            if location.lower().startswith(user_location):  # 'москва' начинается с 'моск'
                context[direction] = location
                return True

    context[locations] = '\n'.join(actual_locations)
    return False


def handle_departure(bot, user_id, user_text):
    return handle_location(bot, user_id, user_text)


def handle_arrival(bot, user_id, user_text):
    result = handle_location(bot, user_id, user_text, False)
    if not result:
        return result

    context = get_context(bot, user_id)
    from_ = context['from_']
    to_ = context['to_']

    is_route_available = bot.tickets_api.is_route_available(from_=from_, to_=to_)
    if not is_route_available:
        context['quit_message'] = f'Вы ввели {to_}. Маршрут "{from_} - {to_}" не доступен. Всего Вам хорошего!'
        return False

    return True


def handle_date(bot, user_id, user_text):
    try:
        user_datetime = datetime.datetime.strptime(user_text, '%d-%m-%Y')
    except ValueError:
        return False

    now = datetime.datetime.now()
    if user_datetime < datetime.datetime(year=now.year, month=now.month, day=now.day):
        return False

    context = get_context(bot, user_id)
    context['when_'] = user_datetime

    from_ = context['from_']
    to_ = context['to_']
    flights = bot.tickets_api.get_tickets(from_=from_, to_=to_, when_=user_datetime, limit=5)
    if not flights:
        context['quit_message'] = f'Вы ввели дату вылета {user_datetime}. Маршрут "{from_} - {to_}" не доступен на ' \
                                  f'указанную дату. Всего Вам хорошего!'
        return False

    context['flights'] = flights
    context['flights_as_str'] = get_flights_as_str(flights)
    return True


def handle_flight_id(bot, user_id, user_text):
    try:
        user_flight_id = int(user_text)
    except (ValueError, TypeError):
        return False

    context = get_context(bot, user_id)
    flights = context['flights']

    if not user_flight_id in flights.keys():
        return False

    flight = flights[user_flight_id]

    context['flight_id'] = user_flight_id
    context['flight'] = flight
    context['flight_when_'] = flight['when_']
    return True


def handle_tickets_qty(bot, user_id, user_text):
    min = 1
    max = 5

    try:
        qty = int(user_text)
    except (ValueError, TypeError):
        return False

    result = min <= qty <= max

    if result:
        context = get_context(bot, user_id)
        context['tickets_qty'] = qty

    return result


def handle_comment(bot, user_id, user_text):
    context = get_context(bot, user_id)
    context['comment'] = user_text
    context['summary'] = get_summary_as_str(context)
    return True


def handle_summary(bot, user_id, user_text):
    match = re.search(YES_NO_PATTERN, user_text)
    if not match:
        return False

    user_answer = match.group()
    if user_answer == 'да':
        return True
    else:
        context = get_context(bot, user_id)
        context['quit_message'] = 'Вы выбрали завершить оформление билета. Новое оформление начнется автоматически.'
        context['start_over'] = True
        return False


def handle_phone(bot, user_id, user_text):
    match = re.search(PHONE_PATTERN, user_text)

    if not match:
        return False

    context = get_context(bot, user_id)
    phone = match.group()
    context['phone'] = phone
    context['summary'] += f'Телефон: {phone}\n'
    return True
