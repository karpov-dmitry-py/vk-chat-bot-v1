import os.path
from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy import create_engine
from sqlalchemy import and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()


class Ticket(Base):
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True)
    from_ = Column(String(100), nullable=False)
    to_ = Column(String(100), nullable=False)
    when_ = Column(DateTime, nullable=False)
    price = Column(Float, nullable=False)

    def __info(self):
        return f'ID: <{self.id}>, вылет {self.when_.strftime("%d.%m.%Y %H:%M")} ' \
               f'{self.from_} --> {self.to_}, цена: {self.price} руб.'

    def __str__(self):
        return self.__info()

    def __repr__(self):
        return self.__info()


class Dispatcher:
    # расписание для формирования рейсов в БД
    settings = {
        'num_days': 60,
        'daily_tickets': [
            {
                'from_': 'Москва',
                'to_': 'Екатеринбург',
                'when_': (9, 0),  # hour, minute
                'price': 4000.00
            },
            {
                'from_': 'Москва',
                'to_': 'Владивосток',
                'when_': (6, 40),
                'price': 24000.00
            },
            {
                'from_': 'Санкт-Петербург',
                'to_': 'Казань',
                'when_': (8, 35),
                'price': 5200.00
            },
            {
                'from_': 'Санкт-Петербург',
                'to_': 'Краснодар',
                'when_': (7, 15),
                'price': 4900.00
            }
        ],
        'tickets_on_weekdays': [
            {
                'from_': 'Москва',
                'to_': 'Бангкок',
                'weekdays': (0, 2, 4),
                'when_': (8, 40),
                'price': 35000.00
            },
            {
                'from_': 'Санкт-Петербург',
                'to_': 'Токио',
                'weekdays': (0, 2, 3, 6),
                'when_': (6, 5),
                'price': 29000.00
            }
        ],
        'tickets_on_monthdays': [
            {
                'from_': 'Бангкок',
                'to_': 'Краби',  # 900 км на юг, один час лету, классное место!
                'monthdays': [day_number for day_number in range(1, 31, 3)],
                'when_': (11, 20),
                'price': 6000.00
            },
            {
                'from_': 'Казань',
                'to_': 'Анталья',
                'monthdays': [day_number for day_number in range(1, 31, 4)],
                'when_': (21, 12),
                'price': 12800.00
            }
        ]
    }

    @classmethod
    def _create_engine(cls):

        db_dialect = 'sqlite:///'
        db_name = 'tickets_api_db.sqlite'
        db_full_path = os.path.normpath(os.path.join(os.path.dirname(__file__), db_name))
        engine = create_engine(f'{db_dialect}{db_full_path}')

        Base.metadata.create_all(engine)
        Base.metadata.bind = engine

        return engine

    @classmethod
    def _create_session(cls):
        engine = Dispatcher._create_engine()
        DBSession = sessionmaker(bind=engine)
        session = DBSession()
        return session

    def __init__(self):
        self.session = Dispatcher._create_session()

    def _get_date(self, start_date, num_days):
        result = datetime.date(year=start_date.year, month=start_date.month, day=start_date.day) + \
                 datetime.timedelta(days=num_days)
        return result

    def _get_time(self, hr_min_tuple):
        result = datetime.time(hour=hr_min_tuple[0], minute=hr_min_tuple[1])
        return result

    def _instantiate_ticket(self, cfg, date):

        time = self._get_time(cfg['when_'])
        ticket = Ticket(
            from_=cfg['from_'],
            to_=cfg['to_'],
            when_=datetime.datetime.combine(date, time),
            price=cfg['price']
        )
        return ticket

    def _create_daily_tickets(self, start_date):

        num_days = Dispatcher.settings['num_days']
        configs = Dispatcher.settings['daily_tickets']

        for cfg in configs:

            tickets = []
            for day in range(0, num_days + 1):
                curr_date = self._get_date(start_date, day)
                ticket = self._instantiate_ticket(cfg, curr_date)
                tickets.append(ticket)

            self.session.add_all(tickets)

    def _create_tickets_on_weekdays(self, start_date):

        num_days = Dispatcher.settings['num_days']
        configs = Dispatcher.settings['tickets_on_weekdays']

        for cfg in configs:

            tickets = []
            for day in range(0, num_days + 1):

                curr_date = self._get_date(start_date, day)
                weekday_num = curr_date.timetuple().tm_wday

                if not weekday_num in cfg['weekdays']:
                    continue

                ticket = self._instantiate_ticket(cfg, curr_date)
                tickets.append(ticket)

            if tickets:
                self.session.add_all(tickets)

    def _create_tickets_on_monthdays(self, start_date):

        num_days = Dispatcher.settings['num_days']
        configs = Dispatcher.settings['tickets_on_monthdays']

        for cfg in configs:
            tickets = []

            for day in range(0, num_days + 1):

                curr_date = self._get_date(start_date, day)
                monthday_num = curr_date.timetuple().tm_mday

                if not monthday_num in cfg['monthdays']:
                    continue

                ticket = self._instantiate_ticket(cfg, curr_date)
                tickets.append(ticket)

            if tickets:
                self.session.add_all(tickets)

    def _create_tickets_in_db(self):
        ''' заполняет по настройкам таблицу tickets в базе данных'''
        start_date = datetime.datetime.now()

        self._create_daily_tickets(start_date)
        self._create_tickets_on_weekdays(start_date)
        self._create_tickets_on_monthdays(start_date)

        self.session.commit()

    def _get_date_for_query(self, when_):
        return datetime.datetime.now() if when_ is None else max(datetime.datetime.now(), when_)

    def get_tickets(self, when_=None, from_=None, to_=None, limit=None):

        '''
        API получения доступных рейсов (полетов) по данным из БД.
        Параметры (все необязательные):
        :param when_: datetime.datetime - дата и время вылета - в запрос к БД подставляется текущая дата, если
        переданная дата is None или меньше текущей даты и времени.
        :param from_ : str - город вылета
        :param to_ : str - город назначения
        :param limit: int > 0 - ограничение на кол-во записей в результате.

        :return: dict - cловарь доступных билетов (с ограничением limit),
        отсортированных по возрастающей дате вылета и возрастающей цене c датой вылета сегодня и позднее.
        Ключ: ID билета - int
        Значение: словарь с полями id, from_, to_, when_, price (цена)
        '''
        when_ = self._get_date_for_query(when_)
        tickets = self.session.query(Ticket).filter(and_( \
            Ticket.from_ == from_ if from_ else True, \
            Ticket.to_ == to_ if to_ else True, \
            Ticket.when_ > when_)) \
            .order_by(Ticket.from_.asc(), Ticket.price.asc()).limit(limit)

        result = {}
        for ticket in tickets:
            result[ticket.id] = {
                'id': ticket.id,
                'from_': ticket.from_,
                'to_': ticket.to_,
                'when_': ticket.when_,
                'price': ticket.price,
            }

        return result

    def get_departure_locations(self, when_=None, limit=None):

        '''
        Параметры (все необязательные):
        API получения локаций вылета по базе авиабилетов.
        :param when_: datetime.datetime - дата и время вылета - в запрос к БД подставляется текущая дата, если
        переданная дата is None или меньше текущей даты и времени.
        :param limit: int > 0 - ограничение на кол-во записей в результате.

        :return: список (list) доступных локаций вылета (str) с сортировкой по возрастанию.
        '''

        when_ = self._get_date_for_query(when_)
        locations = self.session.query(Ticket.from_).filter(Ticket.when_ > when_). \
            group_by(Ticket.from_). \
            order_by(Ticket.from_.asc()).limit(limit)

        return [location.from_ for location in locations]

    def get_arrival_locations(self, when_=None, limit=None):

        '''
        Параметры (все необязательные):
        API получения локаций прибытия по базе авиабилетов.
        :param when_: datetime.datetime - дата и время вылета - в запрос к БД подставляется текущая дата, если
        переданная дата is None или меньше текущей даты и времени.
        :param limit: int > 0 - ограничение на кол-во записей в результате.

        :return: список (list) доступных локаций прилета (str) с сортировкой по возрастанию.
        '''

        when_ = self._get_date_for_query(when_)
        locations = self.session.query(Ticket.to_).filter(Ticket.when_ > when_). \
            group_by(Ticket.to_). \
            order_by(Ticket.to_.asc()).limit(limit)

        return [location.to_ for location in locations]

    def is_route_available(self, from_, to_, when_=None):

        '''
        Параметры (* = обязательные):
        API получения информации, выполняются ли полеты из города вылета в город прибытия по базе авиабилетов.
        :param from_ : str - * - город вылета
        :param to_ : str - * - город назначения
        :param when_: datetime.datetime - дата и время вылета - в запрос к БД подставляется текущая дата, если
        переданная дата is None или меньше текущей даты и времени.

        :return: boolean
        '''

        when_ = self._get_date_for_query(when_)
        count = self.session.query(Ticket.id).filter(and_( \
            Ticket.from_ == from_, \
            Ticket.to_ == to_, \
            Ticket.when_ > when_)) \
            .count()

        return bool(count)

    def _print_tickets(self, tickets: list):
        for ticket in tickets:
            print(ticket)


def main():
    dispatcher = Dispatcher()
    dispatcher._create_tickets_in_db()


if __name__ == '__main__':
    main()
