"""Tax loss harvester extension for Fava.
"""
import collections
import locale
import re

from beancount.core.data import iter_entry_dates, Open
from beancount.core.number import ZERO, Decimal, D

from fava.ext import FavaExtensionBase

class TaxLossHarvester(FavaExtensionBase):  # pragma: no cover
    '''Tax Loss Harvester Fava (Beancount) Plugin
    '''
    report_title = "Tax Loss Harvester"

    def harvestable(self, begin=None, end=None):
        """Find tax loss harvestable lots.
        - This is intended for the US, but may be adaptable to other countries.
        - This assumes SpecID (Specific Identification of Shares) is the method used for these accounts
        """

        sql = """
        SELECT {account_field} as account,
            units(sum(position)) as units,
            cost_date as acquisition_date,
            value(sum(position)) as market_value,
            cost(sum(position)) as basis
          WHERE account_sortkey(account) ~ "^[01]" AND
            account ~ '{accounts_pattern}' AND
            date <= DATE_ADD(TODAY(), -30)
          GROUP BY {account_field}, cost_date, currency, cost_currency, cost_number, account_sortkey(account)
          ORDER BY account_sortkey(account), currency, cost_date
        """.format(account_field=self.config.get('account_field', 'LEAF(account)'),
                accounts_pattern=self.config.get('accounts_pattern', ''))
        contents, rtypes, rrows = self.ledger.query_shell.execute_query(sql)
        if not rtypes:
            return [], {}, [[]]

        # Since we GROUP BY cost_date, currency, cost_currency, cost_number, we never expect any of the
        # inventories we get to have more than a single position. Thus, we can and should use
        # get_only_position() below. We do this grouping because we are interested in seeing every lot
        # seperately, that can be sold to generate a TLH

        loss_threshold = self.config.get('loss_threshold', 1)

        # our output table is slightly different from our query table:
        retrow_types = rtypes[:-1] +  [('loss', Decimal), ('wash', str)]

        # rtypes:
        # [('account', <class 'str'>),
        #  ('units', <class 'beancount.core.inventory.Inventory'>),
        #  ('acquisition_date', <class 'datetime.date'>),
        #  ('market_value', <class 'beancount.core.inventory.Inventory'>),
        #  ('basis', <class 'beancount.core.inventory.Inventory'>)]

        RetRow = collections.namedtuple('RetRow', [i[0] for i in retrow_types])

        def val(inv):
            return inv.get_only_position().units.number

        # build our output table: calculate losses, find wash sales
        to_sell = []
        recently_bought = {}
        for row in rrows:
            if row.market_value.get_only_position() and \
             (val(row.market_value) - val(row.basis) < -loss_threshold):
                loss = D(val(row.basis) - val(row.market_value))

                # find wash sales
                ticker = row.units.get_only_position().units.currency
                recent = recently_bought.get(ticker, None)
                if not recent:
                    recent = self.query_recently_bought(ticker)
                    recently_bought[ticker] = recent
                wash = '*' if len(recent[1]) else ''

                to_sell.append(RetRow(row.account, row.units, row.acquisition_date, 
                    row.market_value, loss, wash))

        # Summary
        locale.setlocale(locale.LC_ALL, '')
        summary = {}
        summary["Total transactions"] = len(to_sell)
        unique_txns = set((r.account, r.units.get_only_position().units.currency) for r in to_sell)
        summary["Total unique transactions"] = len(unique_txns)
        summary["Total harvestable loss"] = sum(i.loss for i in to_sell)
        summary["Total sale value required"] = sum(i.market_value.get_only_position().units.number for i in to_sell)
        summary = {k:'{:n}'.format(v) for k,v in summary.items()}

        harvestable_table = retrow_types, to_sell
        recents = self.build_recents(recently_bought)
        return harvestable_table, summary, recents

    def build_recents(self, recently_bought):
        retval = []
        for t in recently_bought:
            if len(recently_bought[t][1]):
                retval.append([*recently_bought[t]])
        return retval

    def query_recently_bought(self, ticker):
        """Looking back 30 days for purchases that would cause wash sales"""

        wash_pattern = self.config.get('wash_pattern', '')
        wash_pattern_sql = 'AND account ~ "{}"'.format(wash_pattern) if wash_pattern else ''
        account_field=self.config.get('account_field', 'LEAF(account)')

        sql = '''
        SELECT
            {account_field} as account,
            units(sum(position)) as units,
            date as acquisition_date,
            cost(sum(position)) as basis
          WHERE
            date >= DATE_ADD(TODAY(), -30)
            {wash_pattern_sql}
            AND currency = "{ticker}"
          GROUP BY date,{account_field}
          ORDER BY date DESC
          '''.format(**locals())
        contents, rtypes, rrows = self.ledger.query_shell.execute_query(sql)
        return rtypes, rrows


# TODO:
#     - display main table:
#       - test cases for wash sales (can't have bought within 30 days; edge cases of 29/30/31 days)
#         - date <= DATE_ADD(TODAY(), -30): is this correct?
#       - will grouping by cost_date mean multiple lots with different costs on the same day be rendered
#         incorrectly?
#       - assert specid / "STRICT"
#     - bells and whistles:
#       - use query context (dates? future and past?)
#       - csv download

