'''
Common features and functions for swingtime

'''
from collections import defaultdict
from datetime import datetime, date, timedelta
import itertools

from django.core.exceptions import ImproperlyConfigured
from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe

from swingtime import settings as swingtime_settings


def get_event_model():
    """
    Returns the Event model that is active in this project.
    """
    from django.db.models import get_model

    try:
        app_label, model_name = swingtime_settings.EVENT_MODEL.split('.')
    except ValueError:
        raise ImproperlyConfigured("SWINGTIME_EVENT_MODEL must be of the form"
                                   " 'app_label.model_name'")
    event_model = get_model(app_label, model_name)
    if event_model is None:
        raise ImproperlyConfigured("SWINGTIME_EVENT_MODEL refers to model '%s'"
                                   " that has not been installed"
                                   % swingtime_settings.EVENT_MODEL)
    return event_model


def get_occasion_model():
    """
    Returns the Occasion model that is active in this project.
    """
    from django.db.models import get_model

    try:
        app_label, model_name = swingtime_settings.OCCASION_MODEL.split('.')
    except ValueError:
        raise ImproperlyConfigured("SWINGTIME_OCCASION_MODEL must be of the "
                                   " form 'app_label.model_name'")
    occasion_model = get_model(app_label, model_name)
    if occasion_model is None:
        raise ImproperlyConfigured("SWINGTIME_OCCASION_MODEL refers to model "
                                   "'%s' that has not been installed"
                                   % swingtime_settings.OCCASION_MODEL)
    return occasion_model


def html_mark_safe(func):
    '''
    Decorator for functions return strings that should be treated as template
    safe.

    '''
    def decorator(*args, **kws):
        return mark_safe(func(*args, **kws))
    return decorator


def time_delta_total_seconds(time_delta):
    '''
    Calculate the total number of seconds represented by a
    ``datetime.timedelta`` object

    '''
    return time_delta.days * 3600 + time_delta.seconds


def month_boundaries(dt=None):
    '''
    Return a 2-tuple containing the datetime instances for the first and last
    dates of the current month or using ``dt`` as a reference.

    '''
    import calendar
    dt = dt or date.today()
    wkday, ndays = calendar.monthrange(dt.year, dt.month)
    start = datetime(dt.year, dt.month, 1)
    return (start, start + timedelta(ndays - 1))


def css_class_cycler():
    '''
    Return a dictionary keyed by ``EventType`` abbreviations, whose values are
    an iterable or cycle of CSS class names.
    '''
    from swingtime.models import EventType
    return defaultdict(
        lambda: itertools.cycle(('evt-even', 'evt-odd')).next,
        ((e.abbr, itertools.cycle((
             'evt-%s-even' % e.abbr,
             'evt-%s-odd' % e.abbr
             )).next) for e in EventType.objects.all()
        )
    )


class BaseOccasionProxy(object):
    '''
    A simple wrapper class for handling the presentational aspects of an
    ``Occasion`` instance.

    '''
    def __init__(self, occasion, col):
        self.column = col
        self._occasion = occasion
        self.event_class = ''

    def __getattr__(self, name):
        return getattr(self._occasion, name)

    def __unicode__(self):
        return self.title


class DefaultOccasionProxy(BaseOccasionProxy):

    CONTINUATION_STRING = '^'

    def __init__(self, *args, **kws):
        super(DefaultOccasionProxy, self).__init__(*args, **kws)
        link = '<a href="%s">%s</a>' % (
            self.get_absolute_url(),
            self.title
        )

        self._str = itertools.chain(
            (link,),
            itertools.repeat(self.CONTINUATION_STRING)
        ).next

    @html_mark_safe
    def __unicode__(self):
        return self._str()


def create_timeslot_table(
    dt=None,
    items=None,
    start_time=swingtime_settings.TIMESLOT_START_TIME,
    end_time_delta=swingtime_settings.TIMESLOT_END_TIME_DURATION,
    time_delta=swingtime_settings.TIMESLOT_INTERVAL,
    min_columns=swingtime_settings.TIMESLOT_MIN_COLUMNS,
    css_class_cycles=css_class_cycler,
    proxy_class=DefaultOccasionProxy
):
    '''
    Create a grid-like object representing a sequence of times (rows) and
    columns where cells are either empty or reference a wrapper object for
    event occasions that overlap a specific time slot.

    Currently, there is an assumption that if an occasion has a ``start_time``
    that falls with the temporal scope of the grid, then that ``start_time``
    will also match an interval in the sequence of the computed row entries.

    * ``dt`` - a ``datetime.datetime`` instance or ``None`` to default to now
    * ``items`` - a queryset or sequence of ``Occasion`` instances. If
      ``None``, default to the daily occasions for ``dt``
    * ``start_time`` - a ``datetime.time`` instance
    * ``end_time_delta`` - a ``datetime.timedelta`` instance
    * ``time_delta`` - a ``datetime.timedelta`` instance
    * ``min_column`` - the minimum number of columns to show in the table
    * ``css_class_cycles`` - if not ``None``, a callable returning a dictionary
      keyed by desired ``EventType`` abbreviations with values that iterate
      over progressive CSS class names for the particular abbreviation.
    * ``proxy_class`` - a wrapper class for accessing an ``Occasion`` object.
      This class should also expose ``event_type`` and ``event_type`` attrs,
      and handle the custom output via its __unicode__ method.
    '''
    from swingtime.models import Occasion
    dt = dt or datetime.now()
    dtstart = datetime.combine(dt.date(), start_time)
    dtend = dtstart + end_time_delta

    if isinstance(items, QuerySet):
        items = items._clone()
    elif not items:
        items = Occasion.objects.daily_occasions(dt).select_related('event')

    # build a mapping of timeslot "buckets"
    timeslots = dict()
    n = dtstart
    while n <= dtend:
        timeslots[n] = {}
        n += time_delta

    # fill the timeslot buckets with occasion proxies
    for item in sorted(items):
        if item.end_time <= dtstart:
            # this item began before the start of our schedle constraints
            continue

        if item.start_time > dtstart:
            rowkey = current = item.start_time
        else:
            rowkey = current = dtstart

        timeslot = timeslots.get(rowkey, None)
        if timeslot is None:
            # TODO fix atypical interval boundry spans
            # This is rather draconian, we should probably try to find a better
            # way to indicate that this item actually occurred between 2
            # intervals and to account for the fact that this item may be
            # spanning cells  but on weird intervals
            continue

        colkey = 0
        while 1:
            # keep searching for an open column to place this occasion
            if colkey not in timeslot:
                proxy = proxy_class(item, colkey)
                timeslot[colkey] = proxy

                while current < item.end_time:
                    rowkey = current
                    row = timeslots.get(rowkey, None)
                    if row is None:
                        break

                    # we might want to put a sanity check in here to ensure
                    # that we aren't trampling some other entry, but by virtue
                    # of sorting all occasion that shouldn't happen
                    row[colkey] = proxy
                    current += time_delta
                break

            colkey += 1

    # determine the number of timeslot columns we should show
    column_lens = [len(x) for x in timeslots.itervalues()]
    column_count = max((min_columns, max(column_lens) if column_lens else 0))
    column_range = range(column_count)
    empty_columns = ['' for x in column_range]

    if css_class_cycles:
        column_classes = dict([(i, css_class_cycles()) for i in column_range])
    else:
        column_classes = None

    # create the chronological grid layout
    table = []
    for rowkey in sorted(timeslots.keys()):
        cols = empty_columns[:]
        for colkey in timeslots[rowkey]:
            proxy = timeslots[rowkey][colkey]
            cols[colkey] = proxy
            if not proxy.event_class and column_classes:
                proxy.event_class = \
                    column_classes[colkey][proxy.event_type.abbr]()

        table.append((rowkey, cols))

    return table
