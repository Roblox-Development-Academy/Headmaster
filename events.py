from typing import Dict

from utils.events import Event

date_selected: Event = Event()
reaction_roles: Dict[str, Event] = {
    'staff_application': Event()
}
