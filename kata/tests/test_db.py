import unittest
import kata.db

kata.db.initialize({
    'name': 'test_kata',
    'user': 'test_kata',
    'password': 'test_kata',
    'host': 'localhost',
    'port': 5432,
})

class Table(kata.db.Object):
    __table__ = 'test_table'

class TestDB(unittest.TestCase):
    def setUp(self):
        kata.db.execute('drop table if exists test_table')
        kata.db.execute('''
            create table test_table (
                id bigserial primary key,
                test_integer integer not null,
                test_varchar varchar(255) not null,
                test_text text
            )
        ''')

    def test_create(self):
        data = {
            'test_integer': 1,
            'test_varchar': 'varchar',
            'test_text': 'text'
        }

        Table.create(data)

        rows = Table.get()
        self.assertEqual(len(rows), 1)
        for k, v in data.items():
            self.assertEqual(getattr(rows[0], k), v)

        del data['id']
        Table.create([data for _ in range(5)])
        rows = Table.get()
        self.assertEqual(len(rows), 6)

    def test_delete(self):
        # populate table
        kata.db.execute('''
            insert into test_table
                (test_integer, test_varchar, test_text)
            values
                (1, 'varchar', 'text'),
                (2, 'foo', 'bar'),
                (1, 'foo', 'baz')
        ''')

        # test basic delete
        Table.delete(where={'test_text': 'bar'})
        self.assertEqual(len(Table.get()), 2)

        # test delete in
        Table.delete(where_in=('test_integer', [1]))
        self.assertEqual(len(Table.get()), 0)

    def test_get(self):
        # populate table
        kata.db.execute('''
            insert into test_table
                (test_integer, test_varchar, test_text)
            values
                (1, 'varchar', 'text'),
                (2, 'foo', 'bar'),
                (1, 'foo', 'baz')
        ''')

        # test basic get
        self.assertEqual(len(Table.get()), 3)
        self.assertEqual(len(Table.get({'test_integer': 1})), 2)
        self.assertEqual(len(Table.get({'test_varchar': 'foo'})), 2)
        self.assertEqual(len(Table.get({'test_text': 'text'})), 1)

        # test get one
        row = Table.get({'test_integer': 2}, one=True)
        self.assertEqual(row.test_integer, 2)
        self.assertEqual(row.test_varchar, 'foo')
        self.assertEqual(row.test_text, 'bar')

        # test get in
        self.assertEqual(len(Table.get(where_in=('test_text', ['bar', 'baz']))), 2)
        self.assertEqual(len(Table.get(where_in=[('test_text', ['text', 'baz']), ('test_integer', [1])])), 2)
        self.assertEqual(len(Table.get(where={'test_integer': 1}, where_in=('test_text', ['bar', 'baz']))), 1)

        # test limit
        self.assertEqual(len(Table.get(limit=1)), 1)
        self.assertEqual(len(Table.get({'test_integer': 1}, limit=2)), 2)

        # test order by
        rows = Table.get(order_by='test_integer asc')
        self.assertEqual(rows[0].test_integer, 1)
        self.assertEqual(rows[2].test_integer, 2)

    def test_update(self):
        # populate table
        kata.db.execute('''
            insert into test_table
                (test_integer, test_varchar, test_text)
            values
                (1, 'varchar', 'text'),
                (2, 'foo', 'bar'),
                (1, 'foo', 'baz')
        ''')

        # test updating entire table
        Table.update({'test_text': 'qux'})
        self.assertEqual(len(Table.get({'test_text': 'qux'})), 3)

        # test updating where a where
        Table.update({'test_integer': 3}, {'test_varchar': 'foo'})
        self.assertEqual(len(Table.get({'test_integer': 3})), 2)

if __name__ == '__main__':
    unittest.main()
