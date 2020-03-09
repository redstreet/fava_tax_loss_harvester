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
        """An account tree based on matching regex patterns."""
        if begin:
            tree = Tree(iter_entry_dates(self.ledger.entries, begin, end))
        else:
            tree = self.ledger.root_tree

        portfolios = []

        for option in self.config:
            opt_key = option[0]
            if opt_key == "account_name_pattern":
                portfolio = self._account_name_pattern(tree, end, option[1], option[2])
            elif opt_key == "account_open_metadata_pattern":
                portfolio = self._account_metadata_pattern(
                    tree, end, option[1][0], option[1][1]
                )
            else:
                raise FavaAPIException("Portfolio List: Invalid option.")
            portfolios.append(portfolio)

        return portfolios

    def _account_name_pattern(self, tree, date, pattern, include_children):
        """
        Returns portfolio info based on matching account name.

        Args:
            tree: Ledger root tree node.
            date: Date.
            pattern: Account name regex pattern.
        Return:
            Data structured for use with a querytable (types, rows).
        """
        title = "Account names matching: '" + pattern + "'"
        selected_accounts = []
        regexer = re.compile(pattern)
        for acct in tree.keys():
            if (regexer.match(acct) is not None) and (
                acct not in selected_accounts
            ):
                selected_accounts.append(acct)
                # if '$' in pattern:
                #     print("Match! {} against {}".format(acct, pattern))

        selected_nodes = [tree[x] for x in selected_accounts]
        portfolio_data = self._portfolio_data(selected_nodes, date, include_children)
        return title, portfolio_data

    def _account_metadata_pattern(self, tree, date, metadata_key, pattern):
        """
        Returns portfolio info based on matching account open metadata.

        Args:
            tree: Ledger root tree node.
            date: Date.
            metadata_key: Metadata key to match for in account open.
            pattern: Metadata value's regex pattern to match for.
        Return:
            Data structured for use with a querytable - (types, rows).
        """
        title = (
            "Accounts with '"
            + metadata_key
            + "' metadata matching: '"
            + pattern
            + "'"
        )
        selected_accounts = []
        regexer = re.compile(pattern)
        for entry in self.ledger.all_entries_by_type[Open]:
            if (metadata_key in entry.meta) and (
                regexer.match(entry.meta[metadata_key]) is not None
            ):
                selected_accounts.append(entry.account)

        selected_nodes = [tree[x] for x in selected_accounts]
        portfolio_data = self._portfolio_data(selected_nodes, date)
        return title, portfolio_data

    def _portfolio_data(self, nodes, date, include_children=''):
        """
        Turn a portfolio of tree nodes into querytable-style data.

        Args:
            nodes: Account tree nodes.
            date: Date.
        Return:
            types: Tuples of column names and types as strings.
            rows: Dictionaries of row data by column names.
        """
        operating_currency = self.ledger.options["operating_currency"][0]
        acct_type = ("account", str(str))
        bal_type = ("balance", str(Decimal))
        alloc_type = ("allocation", str(Decimal))
        types = [acct_type, bal_type, alloc_type]

        rows = []
        portfolio_total = ZERO
        for node in nodes:
            row = {}
            row["account"] = node.name
            balance = cost_or_value(node.balance_children, date) if include_children else cost_or_value(node.balance, date)
            if operating_currency in balance:
                balance_dec = balance[operating_currency]
                portfolio_total += balance_dec
                row["balance"] = balance_dec
                rows.append(row)
            # if node.name == "Assets:Investments:Taxable":
            #     import pdb; pdb.set_trace()

        for row in rows:
            if "balance" in row:
                row["allocation"] = round(
                    (row["balance"] / portfolio_total) * 100, 2
                )

        return types, rows
