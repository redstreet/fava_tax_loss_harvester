"""Portfolio list extension for Fava.

This is a simple example of Fava's extension reports system.
"""
import re

from beancount.core.data import iter_entry_dates, Open
from beancount.core.number import ZERO, Decimal

from fava.ext import FavaExtensionBase
from fava.template_filters import cost_or_value
from fava.template_filters import cost_or_value
from fava.core.tree import Tree
from fava.core.helpers import FavaAPIException


class TaxLossHarvester(FavaExtensionBase):  # pragma: no cover
    '''Tax Loss Harvester Fava (Beancount) Plugin
    '''
    report_title = "Tax Loss Harvester"

    def harvestable(self, begin=None, end=None):
        title = "Testing title"

        acct_type = ("account", str(str))
        bal_type = ("balance", str(Decimal))
        types = [acct_type, bal_type]

        rows = [{'account': "hello", 'balance': 123}, {'account': "world", 'balance': 456}]

        retval = (title, (types, rows))
        print(retval)
        return [retval]

