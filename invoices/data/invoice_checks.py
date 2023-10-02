from dataclasses import dataclass
from datetime import date
from typing import List

from invoices.events import Event
from invoices.models import Prestation


@dataclass
class PrestationEvent:
    care_date: date
    prestation: Prestation
    events: List['Event']
