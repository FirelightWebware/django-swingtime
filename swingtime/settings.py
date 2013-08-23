import datetime
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# A "strftime" string for formatting start and end time selectors in forms
TIMESLOT_TIME_FORMAT = getattr(
    settings, 'SWINGTIME_TIMESLOT_TIME_FORMAT', '%I:%M %p'
)

# Used for creating start/end time form selectors as well as time slot grids.
# Value should be datetime.timedelta value representing the incremental
# differences between temporal options
TIMESLOT_INTERVAL = getattr(
    settings, 'SWINGTIME_TIMESLOT_INTERVAL', datetime.timedelta(minutes=15)
)

# A datetime.time value indicting the starting time for time slot grids and
# form selectors
TIMESLOT_START_TIME = (
    settings, 'SWINGTIME_TIMESLOT_START_TIME', datetime.time(9)
)

# A datetime.timedelta value indicating the offset value from
# TIMESLOT_START_TIME for creating time slot grids and form selectors. The for
# using a time delta is that it possible to span dates. For instance, one could
# have a starting time of 3pm (15:00) and wish to indicate a ending value
# 1:30am (01:30), in which case a value of datetime.timedelta(hours=10.5)
# could be specified to indicate that the 1:30 represents the following date's
# time and not the current date.
TIMESLOT_END_TIME_DURATION = getattr(
    settings, 'SWINGTIME_TIMESLOT_END_TIME_DURATION',
    datetime.timedelta(hours=+8)
)

# Indicates a minimum value for the number grid columns to be shown in the time
# slot table.
TIMESLOT_MIN_COLUMNS = getattr(settings, 'SWINGTIME_TIMESLOT_MIN_COLUMNS', 4)

# Indicate the default length in time for a new occasion, specifed by using
# a datetime.timedelta object
DEFAULT_OCCASION_DURATION = getattr(
    settings, 'SWINGTIME_DEFAULT_OCCASION_DURATION',
    datetime.timedelta(hours=+1)
)

# If not None, passed to the calendar module's setfirstweekday function.
CALENDAR_FIRST_WEEKDAY = getattr(
    settings, 'SWINGTIME_CALENDAR_FIRST_WEEKDAY', 6
)

# The event model to use if you created a custom one based on AbstractEvent
try:
    EVENT_MODEL = getattr(settings, 'SWINGTIME_EVENT_MODEL')
except AttributeError:
    raise ImproperlyConfigured(
        "You must subclass swingtime.models.AbstractEvent and add the dotted"
        " path to your event model under the setting 'SWINGTIME_EVENT_MODEL'."
    )

# The occasion model to use if you created a custom one based on AbstractEvent
try:
    OCCASION_MODEL = getattr(settings, 'SWINGTIME_OCCASION_MODEL')
except AttributeError:
    raise ImproperlyConfigured(
        "You must subclass swingtime.models.AbstractOccasion and add the"
        " dotted path to your occasion model under the setting"
        " 'SWINGTIME_OCCASION_MODEL'."
    )
