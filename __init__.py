"""Tax loss harvester extension for Fava.
"""
from fava.ext import FavaExtensionBase
from . import libtlh

class TaxLossHarvester(FavaExtensionBase):  # pragma: no cover
    '''Tax Loss Harvester Fava (Beancount) Plugin
    '''
    report_title = "Tax Loss Harvester"

    def query_func(self, sql):
        contents, rtypes, rrows = self.ledger.query_shell.execute_query(sql)
        return rtypes, rrows

    def build_tlh_tables(self, begin=None, end=None):
        """Build fava TLH tables using TLH library
        """

        retrow_types, to_sell, recent_purchases = libtlh.find_harvestable_lots(self.query_func, self.config)
        harvestable_table = retrow_types, to_sell
        by_commodity = libtlh.harvestable_by_commodity(*harvestable_table)
        summary = libtlh.summarize_tlh(harvestable_table, by_commodity)
        recents = libtlh.build_recents(recent_purchases)

        return harvestable_table, summary, recents, by_commodity
