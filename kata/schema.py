import logging
import os
import natsort
import subprocess
import re
import yaml

_cache = None
_database = None

def _alter_table_string(table, column_name, data_type, length, default, nullable, primary_key=False, create=False):
    data_type_string = '%s' % data_type
    if 'character' in data_type.lower():
        data_type_string += '(%s)' % length

    default_string = ''
    if default:
        default_string += 'DEFAULT %s' % default

    nullable_string = ''
    if nullable == 'NO':
        nullable += 'NOT NULL'

    primary_key_string = ''
    if primary_key:
        primary_key_string += 'PRIMARY KEY'

    if create:
        return 'ALTER TABLE %s ADD COLUMN %s %s %s %s %s ;' % (
            table,
            column_name,
            data_type_string,
            default_string,
            nullable_string,
            primary_key_string
        )

    sql = ''
    if data_type != 'bigserial':
        sql += 'ALTER TABLE %s ALTER COLUMN %s TYPE %s ; ' % (table, column_name, data_type_string)
    if default:
        sql += 'ALTER TABLE %s ALTER COLUMN %s SET DEFAULT %s ;' % (table, column_name, default_string)

    return sql

def _dump(flags='', tables=None, exclude_tables=None, path=None):
    tables = tables or []
    exclude_tables = exclude_tables or []

    flags += ' '
    flags += ' '.join(['-t %s' % e for e in tables])
    flags += ' '.join(['-T %s' % e for e in exclude_tables])
    command = 'pg_dump -U %s %s %s' % (_database['user'], flags, _database['name'])

    if path:
        command += ' > %s' % path
        return subprocess.check_call(command, shell=True)

    return subprocess.check_output(command, shell=True)

def _index_string(table, index, columns, unique):
    sql = 'CREATE '

    if unique:
        sql += 'UNIQUE '

    sql += 'INDEX %s ON %s USING btree (%s)' % (index, table, ', '.join(columns))
    return sql

def initialize(database):
    global _database
    _database = database

def apply(schema_directory, execute=False):
    def _handle(statement, execute):
        if not statement:
            return

        print(statement)
        if execute:
            kata.db.execute(statement)

    global _database
    if not _database:
        return

    # disable redundant logging
    logging.getLogger().setLevel(logging.INFO)

    import kata.db
    kata.db.initialize(_database)

    for file in os.listdir(schema_directory):
        with open(schema_directory + '/' + file, 'r') as f:
            data = yaml.load(f.read())

            # handle column creation
            for table, metadata in data.items():
                sql = '''
                    select
                        column_name,
                        data_type,
                        character_maximum_length,
                        column_default,
                        is_nullable
                    from information_schema.columns where
                        table_name = '%s';
                ''' % table

                # if table doesn't exist in schema, then it needs to be created
                schema = kata.db.query(sql)
                if len(schema) == 0:
                    _handle('CREATE TABLE %s () ;' % table, execute)

                existing_columns = set()
                metadata_columns = set()
                metadata_data = []
                for metadata_column, metadata_values in metadata['columns'].items():
                    metadata_columns.add(metadata_column)
                    metadata_data.append((metadata_column, metadata_values))

                # for convenience when using the psql CLI, add the ID column first
                for i, (metadata_column, metadata_values) in enumerate(metadata_data):
                    if metadata_column == 'id':
                        metadata_data.pop(i)
                        metadata_data.insert(0, (metadata_column, metadata_values))
                        break

                # for convenience when using the psql CLI, add the dt column second
                for i, (metadata_column, metadata_values) in enumerate(metadata_data):
                    if metadata_column.endswith('dt'):
                        metadata_data.pop(i)
                        metadata_data.insert(1, (metadata_column, metadata_values))
                        break

                # make sure column types match
                for existing_column in schema:
                    column_name, data_type, length, default, nullable = existing_column
                    existing_columns.add(column_name)

                    for metadata_column, metadata_values in metadata_data:
                        if metadata_column == column_name:
                            if data_type != metadata_values.get('type') or \
                                    length != metadata_values.get('length') or \
                                    default != metadata_values.get('default') or \
                                    (nullable and metadata_values.get('nullable') == 'NO') or \
                                    (not nullable and metadata_values.get('nullable') == 'YES'):
                                _handle(_alter_table_string(
                                    table,
                                    column_name,
                                    metadata_values.get('type'),
                                    metadata_values.get('length'),
                                    metadata_values.get('default'),
                                    'NO' if metadata_values.get('nullable') else None,
                                    metadata_values.get('primary_key')
                                ), execute)

                # drop columns that are no longer needed
                unused_columns = existing_columns - metadata_columns
                for unused_column in unused_columns:
                    _handle('ALTER TABLE %s DROP COLUMN %s ;' % (table, unused_column), execute)

                # add columns that are missing, preserving the order determined earlier
                missing_columns = metadata_columns - existing_columns
                for missing_column, _ in metadata_data:
                    if missing_column in missing_columns:
                        column_metadata = metadata['columns'][missing_column]
                        _handle(_alter_table_string(
                            table,
                            missing_column,
                            column_metadata.get('type'),
                            column_metadata.get('length'),
                            column_metadata.get('default'),
                            column_metadata.get('nullable'),
                            column_metadata.get('primary_key'),
                            create=True
                        ), execute)

                # get indexes that currently exist for table
                sql = '''
                    select
                        tablename,
                        indexname,
                        indexdef
                    from pg_indexes where
                        tablename = '%s' and
                        indexname not like '%%_pkey'
                ''' % table

                indexes_schema = kata.db.query(sql)
                existing_indexes = set()
                metadata_indexes = set()
                for metadata_index in metadata.get('indexes', {}).keys():
                    metadata_indexes.add(metadata_index)

                # make sure constraint types match
                for existing_index in indexes_schema:
                    table, index_name, definition = existing_index

                    existing_indexes.add(index_name)
                    for metadata_index, metadata_values in metadata.get('indexes', {}).items():
                        if metadata_index == index_name:
                            index_string = _index_string(
                                table,
                                index_name,
                                metadata_values.get('columns', []),
                                metadata_values.get('unique')
                            )

                            if index_string != definition:
                                _handle('DROP INDEX %s ;' % index_name, execute)
                                _handle('%s ;' % index_string, execute)

                # drop indexes that are no longer needed
                unused_indexes = existing_indexes - metadata_indexes
                for unused_index in unused_indexes:
                    _handle('DROP INDEX %s ;' % unused_index, execute)

                # add indexes that are missing
                missing_indexes = metadata_indexes - existing_indexes
                for missing_index in missing_indexes:
                    index_metadata = metadata['indexes'][missing_index]
                    _handle(_index_string(
                        table,
                        missing_index,
                        index_metadata.get('columns', []),
                        index_metadata.get('unique')
                    ), execute)

def create_database():
    os.system('createdb -U %s %s' % (_database['user'], _database['name']))

def drop_entire_database_and_lose_all_data():
    os.system('dropdb -U %s %s' % (_database['user'], _database['name']))

def export_data(tables=None, exclude_tables=None, path=None):
    return _dump('--column-inserts --data-only', tables, exclude_tables, path)

def export_schema(path=None):
    return _dump('-s', path=path)

def export_tables(tables=None, exclude_tables=None, path=None):
    return _dump('', tables, exclude_tables, path)

def reset(schema, execute=False):
    global _database
    if not _database:
        return

    drop_entire_database_and_lose_all_data()
    create_database()
    apply(schema, execute)
