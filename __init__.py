"""Tax loss harvester extension for Fava.
"""
import collections
import re

from beancount.core.data import iter_entry_dates, Open
from beancount.core.number import ZERO, Decimal

from fava.ext import FavaExtensionBase

class TaxLossHarvester(FavaExtensionBase):  # pragma: no cover
    '''Tax Loss Harvester Fava (Beancount) Plugin
    '''
    report_title = "Tax Loss Harvester"

    def harvestable(self, begin=None, end=None):
        sql = """
        SELECT LEAF(account) as account_leaf,
            units(sum(position)) as units,
            cost_date as acquisition_date,
            value(sum(position)) as market_value,
            cost(sum(position)) as basis
          WHERE account_sortkey(account) ~ "^[01]" AND
            account ~ '{}' AND
            date <= DATE_ADD(TODAY(), -30)
          GROUP BY LEAF(account), cost_date, currency, cost_currency, cost_number, account_sortkey(account)
          ORDER BY account_sortkey(account), currency, cost_date
        """.format(self.config.get('accounts_pattern', ''))
        contents, rtypes, rrows = self.ledger.query_shell.execute_query(sql)
        if not rtypes:
            retval = (title, ([], []))
            return [retval]

        loss_threshold = self.config.get('loss_threshold', 1)

        # our output table is slightly different from our query table:
        retrow_types = rtypes[:-1] +  [('loss', Decimal), ('wash', str)]
        RetRow = collections.namedtuple('RetRow', [i[0] for i in retrow_types])

        def val(inv):
            return inv.get_only_position().units.number

        # build our output table: calculate losses, find wash sales
        to_sell = []
        recently_bought = {}
        for row in rrows:
            if row.market_value.get_only_position() and \
             (val(row.market_value) - val(row.basis) < -loss_threshold):
                loss = int(val(row.basis) - val(row.market_value))

                # find wash sales
                ticker = row.units.get_only_position().units.currency
                recent = recently_bought.get(ticker, None)
                if not recent:
                    recent = self.query_recently_bought(ticker)
                    recently_bought[ticker] = recent
                wash = '*' if len(recent[1]) else ''

                to_sell.append(RetRow(row.account_leaf, row.units, row.acquisition_date, 
                    row.market_value, loss, wash))

        harvestable_table = retrow_types, to_sell
        recents = self.build_recents(recently_bought)
        return harvestable_table, recents

    def build_recents(self, recently_bought):
        retval = []
        for t in recently_bought:
            if len(recently_bought[t][1]):
                retval.append([*recently_bought[t]])
        return retval

    def query_recently_bought(self, ticker):
        """Looking back 30 days for purchases that would cause wash sales"""

        # TODO: move to an init function
        wash_pattern = self.config.get('wash_pattern', '')
        wash_pattern_exclude = self.config.get('wash_pattern_exclude', '')
        wash_pattern_sql = 'AND account ~ "{}"'.format(wash_pattern) if wash_pattern else ''
        wash_pattern_exclude_sql = 'AND NOT STR(account) ~ "{}"'.format(wash_pattern_exclude) \
                if wash_pattern_exclude else ''

        sql = '''
        SELECT
            LEAF(account) as account_leaf,
            units(sum(position)) as units,
            date as acquisition_date,
            cost(sum(position)) as basis
          WHERE
            date >= DATE_ADD(TODAY(), -30)
            {wash_pattern_sql}
            {wash_pattern_exclude_sql}
            AND currency = "{ticker}"
          GROUP BY date,LEAF(account)
          ORDER BY date DESC
          '''.format(**locals())
        contents, rtypes, rrows = self.ledger.query_shell.execute_query(sql)
        return rtypes, rrows


# TODO:
#     - display main table:
#       - test cases for wash sales (can't have bought within 30 days; edge cases of 29/30/31 days)
#         - date <= DATE_ADD(TODAY(), -30): is this correct?
#     - bells and whistles:
#       - use query context (dates? future and past?)
#       - accounts links
#       - csv download

