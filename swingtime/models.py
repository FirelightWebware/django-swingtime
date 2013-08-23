from datetime import datetime

from django.utils.translation import ugettext_lazy as _
from django.db import models

from dateutil import rrule

from . import settings as swingtime_settings
from . import utils

__all__ = (
    'AbstractEvent',
    'AbstractOccasion',
    'create_event'
)


class AbstractEvent(models.Model):

    '''
    Abstract container model for general metadata and associated
    ``Occasion`` entries.
    '''
    title = models.CharField(_('title'), max_length=32)
    description = models.CharField(_('description'), max_length=100)

    class Meta:
        abstract = True
        verbose_name = _('event')
        verbose_name_plural = _('events')
        ordering = ('title', )

    def __unicode__(self):
        return self.title

    @models.permalink
    def get_absolute_url(self):
        return ('swingtime-event', [str(self.id)])

    def add_occasions(self, start_time, end_time, **rrule_params):
        '''
        Add one or more occasions to the event using a comparable API to
        ``dateutil.rrule``.

        If ``rrule_params`` does not contain a ``freq``, one will be defaulted
        to ``rrule.DAILY``.

        Because ``rrule.rrule`` returns an iterator that can essentially be
        unbounded, we need to slightly alter the expected behavior here in
        order to enforce a finite number of occasion creation.

        If both ``count`` and ``until`` entries are missing from
        ``rrule_params``, only a single ``Occasion`` instance will be created
        using the exact ``start_time`` and ``end_time`` values.
        '''

        rrule_params.setdefault('freq', rrule.DAILY)

        if 'count' not in rrule_params and 'until' not in rrule_params:
            self.occasion_set.create(
                start_time=start_time, end_time=end_time)
        else:
            delta = end_time - start_time
            for ev in rrule.rrule(dtstart=start_time, **rrule_params):
                self.occasion_set.create(start_time=ev, end_time=ev + delta)

    def upcoming_occasions(self):
        '''
        Return all occasions that are set to start on or after the current
        time.
        '''
        return self.occasion_set.filter(start_time__gte=datetime.now())

    def next_occasion(self):
        '''
        Return the single occasion set to start on or after the current time
        if available, otherwise ``None``.
        '''
        upcoming = self.upcoming_occasions()
        return upcoming and upcoming[0] or None

    def daily_occasions(self, dt=None):
        '''
        Convenience method wrapping ``Occasion.objects.daily_occasions``.
        '''
        return utils.get_occasion_model().objects \
                    .daily_occasions(dt=dt, event=self)


class OccasionManager(models.Manager):

    use_for_related_fields = True

    def daily_occasions(self, dt=None, event=None):
        '''
        Returns a queryset of for instances that have any overlap with a
        particular day.

        * ``dt`` may be either a datetime.datetime, datetime.date object, or
          ``None``. If ``None``, default to the current day.

        * ``event`` can be an ``Event`` instance for further filtering.
        '''
        dt = dt or datetime.now()
        start = datetime(dt.year, dt.month, dt.day)
        end = start.replace(hour=23, minute=59, second=59)
        qs = self.filter(
            models.Q(
                start_time__gte=start,
                start_time__lte=end,
            ) |
            models.Q(
                end_time__gte=start,
                end_time__lte=end,
            ) |
            models.Q(
                start_time__lt=start,
                end_time__gt=end
            )
        )

        return qs.filter(event=event) if event else qs


class AbstractOccasion(models.Model):
    '''
    Represents the start end time for a specific occasion of a master
    ``Event`` object.
    '''
    start_time = models.DateTimeField(_('start time'))
    end_time = models.DateTimeField(_('end time'))
    event = models.ForeignKey(swingtime_settings.EVENT_MODEL,
                              related_name='occasions')

    objects = OccasionManager()

    class Meta:
        abstract = True
        verbose_name = _('occasion')
        verbose_name_plural = _('occasions')
        ordering = ('start_time', 'end_time')

    def __unicode__(self):
        return u'%s: %s' % (self.title, self.start_time.isoformat())

    @models.permalink
    def get_absolute_url(self):
        return ('swingtime-occasion', [str(self.event.id), str(self.id)])

    def __cmp__(self, other):
        return cmp(self.start_time, other.start_time)

    @property
    def title(self):
        return self.event.title


def create_event(
    title,
    description='',
    start_time=None,
    end_time=None,
    note=None,
    **rrule_params
):
    '''
    Convenience function to create an ``Event``, optionally create an
    associated ``Occasion``s. ``Occasion`` creation
    rules match those for ``Event.add_occasions``.

    Returns the newly created ``Event`` instance.

    Parameters

    ``start_time``
        will default to the current hour if ``None``

    ``end_time``
        will default to ``start_time`` plus
        swingtime_settings.DEFAULT_OCCASION_DURATION
        hour if ``None``

    ``freq``, ``count``, ``rrule_params``
        follow the ``dateutils`` API (see http://labix.org/python-dateutil)

    '''

    event = utils.get_event_model().objects.create(
        title=title,
        description=description
    )

    if note is not None:
        event.notes.create(note=note)

    start_time = start_time or datetime.now().replace(
        minute=0,
        second=0,
        microsecond=0
    )

    end_time = end_time or \
               start_time + swingtime_settings.DEFAULT_OCCASION_DURATION
    event.add_occasions(start_time, end_time, **rrule_params)
    return event
