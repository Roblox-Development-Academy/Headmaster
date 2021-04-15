from utils.map import Map
from utils.events import Event

date_selected: Event = Event()


staff_application_submitted: Event = Event()


reaction_roles: Map[str, Event] = Map({
    'staff_applicant': Event()
})
