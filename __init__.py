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
        return libtlh.get_tables(self.query_func, self.config)
