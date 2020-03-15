#!/usr/bin/env python3

# string = x
# format x
# write string to file
# instantiate query_func with that file

from beancount.utils import test_utils
from beancount import loader
from beancount.query import query
import functools
import libtlh
import tempfile
import datetime

def docfile_handle(function, **kwargs):
    """A decorator that write the function's docstring to a temporary file
    and calls the decorated function with the temporary file handle.  This is
    useful for writing tests.

    Args:
      function: A function to decorate.
    Returns:
      The decorated function.
    """
    @functools.wraps(function)
    def new_function(self):
        allowed = ('buffering', 'encoding', 'newline', 'dir', 'prefix', 'suffix')
        if any([key not in allowed for key in kwargs]):
            raise ValueError("Invalid kwarg to docfile_extra")
        with tempfile.NamedTemporaryFile('w', **kwargs) as file:
            return function(self, file)
    new_function.__doc__ = None
    return new_function

class TestScriptCheck(test_utils.TestCase):
    def write_file(self, f, text):
        # write to temp file and reset it so it can be read by loader.load_file
        f.write(text)
        f.flush()
        f.seek(0)
        self.f = f

    def dates(self):
        def minusdays(today, d):
            return (today - datetime.timedelta(days=d)).isoformat()
        today = datetime.datetime.now().date()
        retval = {'today': today,
                  'm1': minusdays(today, 1),
                  'm5': minusdays(today, 5),
                  'm10': minusdays(today, 10),
                  'm15': minusdays(today, 15),
                  'm20': minusdays(today, 20),
                  }
        return retval

    def query_func(self, sql):
        entries, _, options_map = loader.load_file(self.f.name)
        rtypes, rrows = query.run_query(entries, options_map, sql)
        return rtypes, rrows

    @docfile_handle
    def test_no_relevant_accounts(self, f):
        input_text = """
        2010-01-01 open Assets:Investments:Brokerage
        2010-01-01 open Assets:Bank

        {m10} * "Buy stock"
         Assets:Investments:Brokerage 1 BNCT {{200 USD}}
         Assets:Bank

        {m1} price BNCT 100 USD
        """.format(**(self.dates()))
        self.write_file(f, input_text)

        options = {'accounts_pattern': "Assets:Investments:Taxable", 'wash_pattern': "Assets:Investments"}
        retrow_types, to_sell, recent_purchases = libtlh.find_harvestable_lots(self.query_func, options)

        self.assertEqual(0, len(to_sell))
        self.assertEqual(0, len(recent_purchases))


    @docfile_handle
    def test_harvestable_basic(self, f):

        input_text = """
        2010-01-01 open Assets:Investments:Taxable:Brokerage
        2010-01-01 open Assets:Bank

        {m10} * "Buy stock"
         Assets:Investments:Taxable:Brokerage 1 BNCT {{200 USD}}
         Assets:Bank

        {m1} price BNCT 100 USD
        """.format(**(self.dates()))
        self.write_file(f, input_text)

        options = {'accounts_pattern': "Assets:Investments:Taxable", 'wash_pattern': "Assets:Investments"}
        retrow_types, to_sell, recent_purchases = libtlh.find_harvestable_lots(self.query_func, options)

        self.assertEqual(1, len(to_sell))
        self.assertEqual(1, len(recent_purchases))

