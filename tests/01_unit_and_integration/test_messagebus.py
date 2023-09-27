import asyncio
import pytest
from adbot.domain import messagebus as mb
from adbot.domain import events


async def fake_subscriber_func(event: mb.AdBotEvent):
    pass

class FakeSubscriber:
    def __init__(self):
        self._catched_events = []

    async def handler(self, event: events.AdBotEvent):
        self._catched_events.append(str(event))


def test_mb_add_subcriber_function():
    bus = mb.MessageBus()

    assert len(bus._subscribers) == 0

    bus.subscribe(
        [events.AdBotUserDataUpdated, events.AdBotInactivityTimeout],
        fake_subscriber_func
    )

    assert len(bus._subscribers) == 1
    events_set = {
        events.AdBotUserDataUpdated(1).__class__.__name__,
        events.AdBotInactivityTimeout(1).__class__.__name__
    }
    assert bus._subscribers[fake_subscriber_func] == events_set


def test_mb_add_subcriber_method():
    bus = mb.MessageBus()

    assert len(bus._subscribers) == 0

    fake_subscr_object = FakeSubscriber()

    bus.subscribe(
        [events.AdBotUserDataUpdated, events.AdBotInactivityTimeout],
        fake_subscr_object.handler
    )

    assert len(bus._subscribers) == 1
    events_set = {
        events.AdBotUserDataUpdated(1).__class__.__name__,
        events.AdBotInactivityTimeout(1).__class__.__name__
    }
    assert bus._subscribers[list(bus._subscribers.keys())[0]] == events_set


def test_mb_add_three_subscribers():
    bus = mb.MessageBus()
    assert len(bus._subscribers) == 0

    bus.subscribe([events.AdBotInactivityTimeout], fake_subscriber_func)

    fake_subscr_object1 = FakeSubscriber()

    bus.subscribe(
        [events.AdBotUserDataUpdated, events.AdBotInactivityTimeout],
        fake_subscr_object1.handler
    )

    fake_subscr_object2 = FakeSubscriber()

    bus.subscribe([events.AdBotCriticalError], fake_subscr_object2.handler)

    assert len(bus._subscribers) == 3
    events_set1 = {events.AdBotInactivityTimeout(1).__class__.__name__}
    assert bus._subscribers[fake_subscriber_func] == events_set1
    events_set2 = {
        events.AdBotUserDataUpdated(1).__class__.__name__,
        events.AdBotInactivityTimeout(1).__class__.__name__
    }
    assert bus._subscribers[list(bus._subscribers.keys())[1]] == events_set2
    events_set3 = {events.AdBotCriticalError(1).__class__.__name__}
    assert bus._subscribers[list(bus._subscribers.keys())[2]] == events_set3


def test_mb_raises_exception_on_duplicated_handler():
    bus = mb.MessageBus()
    bus.subscribe([events.AdBotInactivityTimeout], fake_subscriber_func)
    with pytest.raises(mb.MessageBusException):
        bus.subscribe([events.AdBotCriticalError], fake_subscriber_func)


def test_mb_raises_exception_on_wrong_event_type():
    class SomeClass:
        pass

    bus = mb.MessageBus()
    
    with pytest.raises(mb.MessageBusException):
        bus.subscribe([SomeClass], fake_subscriber_func)


@pytest.mark.asyncio
async def test_post_events_function():
    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        catched_events.append(str(event))

    bus = mb.MessageBus()

    bus.subscribe([events.AdBotInactivityTimeout], fake_subscriber_func_local)

    event = events.AdBotInactivityTimeout(2)
    bus.post_event(event)

    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    assert len(catched_events) == 1
    assert catched_events[0] == str(event)


@pytest.mark.asyncio
async def test_post_events_method():
    bus = mb.MessageBus()

    fake_subscr_object1 = FakeSubscriber()

    bus.subscribe(
        [events.AdBotUserDataUpdated, events.AdBotInactivityTimeout],
        fake_subscr_object1.handler
    )

    event = events.AdBotInactivityTimeout(2)
    bus.post_event(event)

    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    assert len(fake_subscr_object1._catched_events) == 1
    assert fake_subscr_object1._catched_events[0] == str(event)


@pytest.mark.asyncio
async def test_post_events_several_subscribers_several_events():
    bus = mb.MessageBus()

    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        catched_events.append(str(event))

    fake_subscr_object1 = FakeSubscriber()

    bus.subscribe(
        [events.AdBotUserDataUpdated, events.AdBotInactivityTimeout],
        fake_subscr_object1.handler
    )
    bus.subscribe(
        [events.AdBotCriticalError, events.AdBotInactivityTimeout],
        fake_subscriber_func_local
    )

    event1 = events.AdBotInactivityTimeout(2)       # fake_subscr_object1,
                                                    #    fake_subscriber_func_local
    event2 = events.AdBotUserDataUpdated(2)         # fake_subscr_object1
    event3 = events.AdBotCriticalError('critical')  # fake_subscriber_func_local

    bus.post_event(event1)
    bus.post_event(event2)
    bus.post_event(event3)

    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    assert len(fake_subscr_object1._catched_events) == 2
    assert set(fake_subscr_object1._catched_events) == set(map(str, [event1, event2]))

    assert len(catched_events) == 2
    assert set(catched_events) == set(map(str, [event1, event3]))


@pytest.mark.asyncio
async def test_post_events_several_subscribers_with_fault_in_one_handler():
    bus = mb.MessageBus()

    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        raise Exception()

    fake_subscr_object1 = FakeSubscriber()

    bus.subscribe(
        [events.AdBotUserDataUpdated, events.AdBotInactivityTimeout],
        fake_subscr_object1.handler
    )
    bus.subscribe(
        [events.AdBotCriticalError, events.AdBotInactivityTimeout],
        fake_subscriber_func_local
    )

    event1 = events.AdBotInactivityTimeout(2)       # fake_subscr_object1,
                                                    #   fake_subscriber_func_local
    event2 = events.AdBotUserDataUpdated(2)         # fake_subscr_object1
    event3 = events.AdBotCriticalError('critical')  # fake_subscriber_func_local

    bus.post_event(event1)
    bus.post_event(event2)
    bus.post_event(event3)

    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    assert len(fake_subscr_object1._catched_events) == 2
    assert set(fake_subscr_object1._catched_events) == set(map(str, [event1, event2]))

    assert len(catched_events) == 0
    assert set(catched_events) == set()
