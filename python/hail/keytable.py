from __future__ import print_function  # Python 2 and 3 print compatibility

from hail.java import scala_package_object, handle_py4j
from hail.type import Type, TStruct
from py4j.protocol import Py4JJavaError
from pyspark.sql import DataFrame


class KeyTable(object):
    """Hail's version of a SQL table where columns can be designated as keys.

    Key tables can be imported from a text file with :py:meth:`~hail.HailContext.import_keytable` or generated from an existing
    VariantDataset with :py:meth:`~hail.VariantDataset.aggregate_by_key`, :py:meth:`~hail.VariantDataset.make_keytable`,
    :py:meth:`~hail.VariantDataset.samples_keytable`, and :py:meth:`~hail.VariantDataset.variants_keytable`.

    In the examples below, we have imported two key tables from text files (``kt1`` and ``kt2``).

    >>> kt1 = hc.import_keytable("data/kt_example1.tsv", ["ID"], config=TextTableConfig(impute=True))

    +--+---+---+-+-+----+----+----+
    |ID|HT |SEX|X|Z| C1 | C2 | C3 |
    +==+===+===+=+=+====+====+====+
    |1 |65 |M  |5|4|2	|50  |5   |
    +--+---+---+-+-+----+----+----+
    |2 |72 |M  |6|3|2	|61  |1   |
    +--+---+---+-+-+----+----+----+
    |3 |70 |F  |7|3|10	|81  |-5  |
    +--+---+---+-+-+----+----+----+
    |4 |60 |F  |8|2|11	|90  |-10 |
    +--+---+---+-+-+----+----+----+

    >>> kt2 = hc.import_keytable("data/kt_example2.tsv", ["ID"], config=TextTableConfig(impute=True))

    +---+---+------+
    |ID	|A  |B     |
    +===+===+======+
    |1	|65 |cat   |
    +---+---+------+
    |2	|72 |dog   |
    +---+---+------+
    |3	|70 |mouse |
    +---+---+------+
    |4	|60 |rabbit|
    +---+---+------+

    :ivar hc: Hail Context
    :vartype hc: :class:`.HailContext`
    """

    def __init__(self, hc, jkt):
        self.hc = hc
        self._jkt = jkt

        self._schema = None
        self._num_columns = None
        self._key_names = None
        self._column_names = None

    def __repr__(self):
        return self._jkt.toString()

    @property
    def num_columns(self):
        """Number of columns.

        >>> kt1.num_columns
        8

        :rtype: int
        """

        if self._num_columns is None:
            self._num_columns = self._jkt.nFields()
        return self._num_columns

    @property
    def schema(self):
        """KeyTable schema.

        **Example:** print the key table columns / signatures

        >>> print(kt1.schema)
        Struct {
            ID: Int,
            HT: Int,
            SEX: String,
            X: Int,
            Z: Int,
            C1: Int,
            C2: Int,
            C3: Int
        }

        :rtype: :class:`.TStruct`
        """

        if self._schema is None:
            self._schema = Type._from_java(self._jkt.signature())
            assert (isinstance(self._schema, TStruct))
        return self._schema

    @property
    def key_names(self):
        """Column names that are keys.

        >>> kt1.key_names
        [u'ID']

        :rtype: list of str
        """

        if self._key_names is None:
            self._key_names = list(self._jkt.keyNames())
        return self._key_names

    @property
    def column_names(self):
        """Names of all columns.

        >>> kt1.column_names
        [u'ID', u'HT', u'SEX', u'X', u'Z', u'C1', u'C2', u'C3']

        :rtype: list of str
        """

        if self._column_names is None:
            self._column_names = list(self._jkt.fieldNames())
        return self._column_names

    @handle_py4j
    def count_rows(self):
        """Number of rows.

        >>> kt1.count_rows()
        4L

        :rtype: long
        """

        return self._jkt.nRows()

    @handle_py4j
    def same(self, other):
        """Test whether two key tables are identical.

        **Examples**

        >>> if kt1.same(kt2):
        ...     print("KeyTables are the same!")

        :param other: key table to compare against
        :type other: :class:`.KeyTable` 

        :rtype: bool
        """

        return self._jkt.same(other._jkt)

    @handle_py4j
    def export(self, output, types_file=None):
        """Export to a TSV file.

        **Examples**

        Rename column names of KeyTable and export to file:

        >>> (kt1.rename({'HT' : 'Height'})
        ...     .export("output/kt1_renamed.tsv"))

        :param str output: Output file path.

        :param str types_file: Output path of types file.
        """

        self._jkt.export(self.hc._jsc, output, types_file)

    @handle_py4j
    def filter(self, condition, keep=True):
        """Filter rows.

        **Examples**

        Keep rows where ``C1`` equals 5:

        >>> kt_result = kt1.filter("C1 == 5")

        Remove rows where ``C1`` equals 10:

        >>> kt_result = kt1.filter("C1 == 10", keep=False)

        **Notes**

        The scope for ``condition`` is all column names in the input :class:`KeyTable`.

        For more information, see the documentation on writing `expressions <../overview.html#expressions>`_
        and using the `Hail Expression Language <../reference.html#HailExpressionLanguage>`_.

        .. caution::
           When ``condition`` evaluates to missing, the row will be removed regardless of whether ``keep=True`` or ``keep=False``.

        :param str condition: Annotation expression.

        :param bool keep: Keep rows where ``condition`` evaluates to True.

        :return: A key table whose rows have been filtered by evaluating ``condition``.
        :rtype: :class:`.KeyTable`
        """

        return KeyTable(self.hc, self._jkt.filter(condition, keep))

    @handle_py4j
    def annotate(self, expr):
        """Add new columns computed from existing columns.

        **Examples**

        Add new column ``Y`` which is equal to 5 times ``X``:

        >>> kt_result = kt1.annotate("Y = 5 * X")


        **Notes**

        The scope for ``expr`` is all column names in the input :class:`KeyTable`.

        For more information, see the documentation on writing `expressions <../overview.html#expressions>`_
        and using the `Hail Expression Language <../reference.html#HailExpressionLanguage>`_.

        :param expr: Annotation expression or multiple annotation expressions.
        :type expr: str or list of str

        :return: A key table with new columns specified by ``expr``.
        :rtype: :class:`.KeyTable`
        """

        if isinstance(expr, list):
            expr = ','.join(expr)

        return KeyTable(self.hc, self._jkt.annotate(expr))

    def join(self, right, how='inner'):
        """Join two KeyTables together.

        **Examples**

        Join ``kt1`` to ``kt2`` to produce ``kt_joined``:

        >>> kt_result = kt1.join(kt2)

        **Notes:**

        Hail supports four types of joins specified by ``how``:

         - **inner** -- Key must be present in both ``kt1`` and ``kt2``.
         - **outer** -- Key present in ``kt1`` or ``kt2``. For keys only in ``kt1``, the value of non-key columns from ``kt2`` is set to missing.
           Likewise, for keys only in ``kt2``, the value of non-key columns from ``kt1`` is set to missing.
         - **left** -- Key present in ``kt1``. For keys only in ``kt1``, the value of non-key columns from ``kt2`` is set to missing.
         - **right** -- Key present in ``kt2``. For keys only in ``kt2``, the value of non-key columns from ``kt1`` is set to missing.

        .. note::
            Both KeyTables must have identical key schemas and non-overlapping column names.

        :param  right: KeyTable to join
        :type right: :class:`.KeyTable`

        :param str how: Method for joining two tables together. One of "inner", "outer", "left", "right".

        :return: A key table that is the result of joining this key table with another.
        :rtype: :class:`.KeyTable`
        """

        return KeyTable(self.hc, self._jkt.join(right._jkt, how))

    @handle_py4j
    def aggregate_by_key(self, key_expr, agg_expr):
        """Group by key condition and aggregate results.

        **Examples**

        Compute mean height by sex:

        >>> kt_ht_by_sex = kt1.aggregate_by_key("SEX = SEX", "MEAN_HT = HT.stats().mean")

        The result of :py:meth:`.aggregate_by_key` is a KeyTable ``kt_ht_by_sex`` with the following data:

        +--------+----------+
        |   SEX  |MEAN_HT   |
        +========+==========+
        |   M    |  68.5    |
        +--------+----------+
        |   F    |   65     |
        +--------+----------+

        **Notes**

        The scope for both ``key_expr`` and ``agg_expr`` is all column names in the input :class:`KeyTable`.

        For more information, see the documentation on writing `expressions <../overview.html#expressions>`_
        and using the `Hail Expression Language <../reference.html#HailExpressionLanguage>`_.

        :param key_expr: Named expression(s) for how to compute the keys of the new key table.
        :type key_expr: str or list of str

        :param agg_expr: Named aggregation expression(s).
        :type agg_expr: str or list of str

        :return: A new key table with the keys computed from the ``key_expr`` and the remaining columns computed from the ``agg_expr``.
        :rtype: :class:`.KeyTable`
        """

        if isinstance(key_expr, list):
            key_expr = ",".join(key_expr)

        if isinstance(agg_expr, list):
            agg_expr = ", ".join(agg_expr)

        return KeyTable(self.hc, self._jkt.aggregate(key_expr, agg_expr))

    @handle_py4j
    def forall(self, code):
        """Test whether a condition is true for all rows.

        **Examples**

        Test whether all rows in the KeyTable have the value of ``C1`` equal to 5:

        >>> if kt1.forall("C1 == 5"):
        ...     print("All rows have C1 equal 5.")

        :param str code: Boolean expression.

        :rtype: bool
        """

        return self._jkt.forall(code)

    @handle_py4j
    def exists(self, code):
        """Test whether a condition is true for any row.

        **Examples**

        Test whether any row in the KeyTable has the value of ``C1`` equal to 5:

        >>> if kt1.exists("C1 == 5"):
        ...     print("At least one row has C1 equal 5.")

        :param str code: Boolean expression.

        :rtype: bool
        """

        return self._jkt.exists(code)

    @handle_py4j
    def rename(self, column_names):
        """Rename columns of KeyTable.

        ``column_names`` can be either a list of new names or a dict
        mapping old names to new names.  If ``column_names`` is a list,
        its length must be the number of columns in this :py:class:`.KeyTable`.

        **Examples**

        Rename using a list:

        >>> kt2.rename(['newColumn1', 'newColumn2', 'newColumn3'])

        Rename using a dict:

        >>> kt2.rename({'A' : 'C1'})

        :param column_names: list of new column names or a dict mapping old names to new names.
        :type list of str or dict of str: str

        :return: A key table with renamed columns.
        :rtype: :class:`.KeyTable`
        """

        return KeyTable(self.hc, self._jkt.rename(column_names))

    @handle_py4j
    def expand_types(self):
        """Expand types Locus, Interval, AltAllele, Variant, Genotype, Char,
        Set and Dict.  Char is converted to String.  Set is converted
        to Array.  Dict[K, V] is converted to

        .. code-block:: text

            Array[Struct {
                key: K
                value: V
            }]

        :return: key table with signature containing only types:
          Boolean, Int, Long, Float, Double, Array and Struct
        :rtype: :class:`.KeyTable`
        """

        return KeyTable(self.hc, self._jkt.expandTypes())

    @handle_py4j
    def key_by(self, key_names):
        """Change which columns are keys.

        **Examples**

        Assume ``kt`` is a :py:class:`.KeyTable` with three columns: c1, c2 and
        c3 and key c1.

        Change key columns:

        >>> kt_result = kt1.key_by(['C2', 'C3'])

        Set to no keys:

        >>> kt_result = kt1.key_by([])

        **Notes**

        The order of the columns will be the original order with the key
        columns moved to the beginning in the order given by ``key_names``.

        :param key_names: List of columns to be used as keys.
        :type key_names: list of str

        :return: A key table whose key columns are given by ``key_names``.
        :rtype: :class:`.KeyTable`
        """

        return KeyTable(self.hc, self._jkt.select(self.column_names, key_names))

    @handle_py4j
    def flatten(self):
        """Flatten nested Structs.  Column names will be concatenated with dot
        (.).

        **Examples**

        Flatten Structs in KeyTable:

        >>> kt_result = kt3.flatten()

        Consider a KeyTable ``kt`` with signature

        .. code-block:: text

            a: Struct {
                p: Int
                q: Double
            }
            b: Int
            c: Struct {
                x: String
                y: Array[Struct {
                z: Map[Int]
                }]
            }

        and a single key column ``a``.  The result of flatten is

        .. code-block:: text

            a.p: Int
            a.q: Double
            b: Int
            c.x: String
            c.y: Array[Struct {
                z: Map[Int]
            }]

        with key columns ``a.p, a.q``.

        Note, structures inside non-struct types will not be
        flattened.

        :return: A key table with no columns of type Struct.
        :rtype: :class:`.KeyTable`
        """

        return KeyTable(self.hc, self._jkt.flatten())

    @handle_py4j
    def select(self, column_names):
        """Select a subset of columns.

        **Examples**

        Assume ``kt`` is a :py:class:`.KeyTable` with three columns: C1, C2 and
        C3.

        Select/drop columns:

        >>> kt_result = kt1.select(['C1'])

        Reorder the columns:

        >>> kt_result = kt1.select(['C3', 'C1', 'C2'])

        Drop all columns:

        >>> kt_result = kt1.select([])

        **Notes**

        The order of the columns will be the order given
        by ``column_names`` with the key columns moved to the beginning
        in the order of the key columns in this :py:class:`.KeyTable`.

        :param column_names: List of columns to be selected.
        :type: list of str

        :return: A key table with selected columns in the order given by ``column_names``.
        :rtype: :class:`.KeyTable`
        """

        new_key_names = [k for k in self.key_names if k in column_names]
        return KeyTable(self.hc, self._jkt.select(column_names, new_key_names))

    @handle_py4j
    def to_dataframe(self, expand=True, flatten=True):
        """Converts this KeyTable to a Spark DataFrame.

        :param bool expand: If true, expand_types before converting to
          DataFrame.

        :param bool flatten: If true, flatten before converting to
          DataFrame.  If both are true, flatten is run after expand so
          that expanded types are flattened.

        :rtype: :class:`pyspark.sql.DataFrame`
        """

        jkt = self._jkt
        if expand:
            jkt = jkt.expandTypes()
        if flatten:
            jkt = jkt.flatten()
        return DataFrame(jkt.toDF(self.hc._jsql_context), self.hc._sql_context)

    @handle_py4j
    def to_pandas(self, expand=True, flatten=True):
        """Converts this KeyTable into a Pandas DataFrame.

        :param bool expand: If true, expand_types before converting to
          Pandas DataFrame.

        :param bool flatten: If true, flatten before converting to Pandas
          DataFrame.  If both are true, flatten is run after expand so
          that expanded types are flattened.

        :returns: A Pandas DataFrame constructed from the KeyTable
        :rtype: :py:class:`pandas.DataFrame`
        """

        return self.to_dataframe(expand, flatten).toPandas()

    @handle_py4j
    def export_mongodb(self, mode='append'):
        """Export to MongoDB"""
        (scala_package_object(self.hc._hail.driver)
         .exportMongoDB(self.hc._jsql_context, self._jkt, mode))

    @handle_py4j
    def explode(self, column_names):
        """Explode columns of this KeyTable.

        The explode operation unpacks the elements in a column of type ``Array`` or ``Set`` into its own row.
        If an empty ``Array`` or ``Set`` is exploded, the entire row is removed from the :py:class:`.KeyTable`.

        **Examples**

        Assume ``kt3`` is a :py:class:`.KeyTable` with three columns: c1, c2 and
        c3.

        >>> kt3 = hc.import_keytable("data/kt_example3.tsv", [],
        ...   config=TextTableConfig(impute=True, types='c1:String,c2:Array[Int],c3:Array[Array[Int]]'))

        The types of each column are ``String``, ``Array[Int]``, and ``Array[Array[Int]]`` respectively.
        c1 cannot be exploded because its type is not an ``Array`` or ``Set``.
        c2 can only be exploded once because the type of c2 after the first explode operation is ``Int``.

        +----+----------+----------------+
        | c1 |   c2     |   c3           |
        +====+==========+================+
        |  a | [1,2,NA] |[[3,4], []]     |
        +----+----------+----------------+

        Explode c2:

        >>> kt3.explode('c2')

        +----+-------+-----------------+
        | c1 |   c2  |    c3           |
        +====+=======+=================+
        |  a | 1     | [[3,4], []]     |
        +----+-------+-----------------+
        |  a | 2     | [[3,4], []]     |
        +----+-------+-----------------+

        Explode c2 once and c3 twice:

        >>> kt3.explode(['c2', 'c3', 'c3'])

        +----+-------+-------------+
        | c1 |   c2  |   c3        |
        +====+=======+=============+
        |  a | 1     |3            |
        +----+-------+-------------+
        |  a | 2     |3            |
        +----+-------+-------------+
        |  a | 1     |4            |
        +----+-------+-------------+
        |  a | 2     |4            |
        +----+-------+-------------+

        :param column_names: Column name(s) to be exploded.
        :type column_names: str or list of str
            
        :return: A key table with columns exploded.
        :rtype: :class:`.KeyTable`
        """

        if isinstance(column_names, str):
            column_names = [column_names]
        return KeyTable(self.hc, self._jkt.explode(column_names))

    @handle_py4j
    def _typecheck(self):
        """Check if all values with the schema."""

        self._jkt.typeCheck()
