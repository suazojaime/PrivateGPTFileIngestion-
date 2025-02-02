import collections

__author__ = 'shattar'


def where(test_vector, min_index=0):
    if not isinstance(test_vector, Vector):
        raise TypeError()
    indices = [list_index for list_index in xrange(min_index, len(test_vector)) if test_vector.list[list_index]]
    return Vector(cols=len(indices), initial_value=indices, dtype='int32')


def cols_where_eq(test_matrix, row_index, test_value, min_col_index=0, max_col_index=float('inf')):
    shape = test_matrix.shape
    row_offset = row_index * shape[1]
    indices = [list_index-row_offset
               for list_index in xrange(row_offset+min_col_index, row_offset+min(shape[1], max_col_index+1))
               if test_matrix.list[list_index] == test_value]
    return Vector(cols=len(indices), initial_value=indices, dtype='int32')


def where_eq(test_matrix, test_value):
    if not isinstance(test_matrix, Matrix):
        raise TypeError()
    if min(test_matrix.shape) > 1:
        raise ValueError()
    indices = [index for index, value in enumerate(test_matrix) if value == test_value]
    return Vector(cols=len(indices), initial_value=indices, dtype='int32')


def all_ne(test_array, test_value):
    return not any_eq(test_array, test_value)


def any_eq(test_array, test_value):
    if not isinstance(test_array, Matrix):
        raise TypeError()
    if min(test_array.shape) > 1:
        raise ValueError()
    for value in test_array:
        if value == test_value:
            return True
    return False


class Matrix(object):
    def __init__(self, rows=1, cols=1, initial_value=0, dtype='float64'):
        ###change code due to jython jar issue:pcf
        ### if isinstance(initial_value, collections.Sequence):
        if hasattr(initial_value, '__iter__'):
            if rows*cols != len(initial_value):
                raise ValueError()
            self.list = initial_value
        else:
            self.list = [initial_value]*(rows*cols)
        self._dtype = dtype
        self._is_bool = dtype == 'bool'
        self._rows = rows
        self._cols = cols

    def __len__(self):
        return self._rows * self._cols

    def __iter__(self):
        return iter(self.list)

    @property
    def shape(self):
        return self._rows, self._cols

    @property
    def is_bool(self):
        return self._is_bool

    def _flatten_index(self, row, column):
        if row >= self._rows or column >= self._cols:
            raise IndexError()
        else:
            return row * self._cols + column

    def _to_indices(self, key):
        if isinstance(key, tuple):
            if len(key) != 2:
                raise IndexError()
            else:
                rows = key[0]
                cols = key[1]
        elif self._cols == 1:
            rows = key
            cols = 0
        elif self._rows == 1:
            rows = 0
            cols = key
        else:
            raise IndexError()

        try:
            rows = [int(rows)]
        except TypeError:
            if isinstance(rows, slice):
                rows = rows.indices(self._rows)
                rows = xrange(rows[0], rows[1], rows[2])
            elif isinstance(rows, Matrix):
                if min(rows.shape) > 1:
                    raise IndexError()
                if rows.is_bool:
                    if len(rows) != self._rows:
                        raise IndexError()
                    rows = [index for index, value in enumerate(rows) if value]
            ###change code due to jython jar issue:pcf
            ###xxx elif isinstance(rows, collections.Sequence): 
            elif hasattr(rows, '__iter__'):                    
                if len(rows) > 0 and isinstance(rows[0], bool):
                    if len(rows) != self._rows:
                        raise IndexError()
                    rows = [index for index, value in enumerate(rows) if value]
            else:
                raise TypeError()

        try:
            cols = [int(cols)]
        except TypeError:
            if isinstance(cols, slice):
                cols = cols.indices(self._cols)
                cols = xrange(cols[0], cols[1], cols[2])
            elif isinstance(cols, Matrix):
                if min(cols.shape) > 1:
                    raise IndexError()
                if cols.is_bool:
                    if len(cols) != self._cols:
                        raise IndexError()
                    cols = [index for index, value in enumerate(cols) if value]
            ###change code due to jython jar issue:pcf
            ### elif isinstance(cols, collections.Sequence):
            elif hasattr(cols, '__iter__'):                    
                if len(cols) > 0 and isinstance(cols[0], bool):
                    if len(cols) != self._cols:
                        raise IndexError()
                    cols = [index for index, value in enumerate(cols) if value]
            else:
                raise TypeError()

        return rows, cols

    def __setitem__(self, key, value):
        rows, cols = self._to_indices(key)
        for row in rows:
            for col in cols:
                self.list[self._flatten_index(row, col)] = value

    def __getitem__(self, item):
        rows, cols = self._to_indices(item)
        if len(rows) > 0 and len(cols) > 0:
            if len(rows) > 1 or len(cols) > 1:
                result = [self.list[self._flatten_index(row, col)] for row in rows for col in cols]
                if len(rows) == 1:
                    return Vector(rows=1, cols=len(result), initial_value=result, dtype=self._dtype)
                elif len(cols) == 1:
                    return Vector(rows=len(result), cols=1, initial_value=result, dtype=self._dtype)
                else:
                    return Matrix(rows=len(rows), cols=len(cols), initial_value=result, dtype=self._dtype)
            else:
                return self.list[self._flatten_index(rows[0], cols[0])]
        else:
            return Matrix(rows=len(rows), cols=len(cols), initial_value=[], dtype=self._dtype)

    def __str__(self):
        return '\n'.join((str(self[r, :]) for r in xrange(self._rows)))


class Vector(Matrix):
    ROW = 1
    COL = -1
    UNK = 0

    def __init__(self, rows=1, cols=1, initial_value=0, dtype='float64'):

        Matrix.__init__(self, rows=rows, cols=cols, initial_value=initial_value, dtype=dtype)

        if rows == 1:
            if cols == 1:
                self._orientation = Vector.UNK
            else:
                self._orientation = Vector.ROW
        elif cols == 1:
            self._orientation = Vector.COL
        else:
            raise ValueError()

    def _to_indices(self, key):
        if isinstance(key, tuple):
            if len(key) != 2:
                raise IndexError()

            rows = key[0]
            cols = key[1]

            if rows != 0 and cols != 0:
                raise IndexError()

            if self._orientation == Vector.ROW:
                if rows == 0:
                    indices = cols
                else:
                    raise IndexError()
            elif self._orientation == Vector.COL:
                if cols == 0:
                    indices = rows
                else:
                    raise IndexError()
            else:
                indices = cols if rows == 0 else rows
        else:
            indices = key

        try:
            indices = [int(indices)]
        except TypeError:
            if isinstance(indices, slice):
                indices = indices.indices(len(self))
                indices = xrange(indices[0], indices[1], indices[2])
            elif isinstance(indices, Matrix):
                if min(indices.shape) > 1:
                    raise IndexError()
                if indices.is_bool:
                    if len(indices) != len(self):
                        raise IndexError()
                    indices = [index for index, value in enumerate(indices) if value]
            ###change code due to jython jar issue:pcf
            ### elif isinstance(indices, collections.Sequence):
            elif hasattr(indices, '__iter__'):                    
                if len(indices) > 0 and isinstance(indices[0], bool):
                    if len(indices) != len(self):
                        raise IndexError()
                    indices = [index for index, value in enumerate(indices) if value]
            else:
                raise TypeError()

        return indices

    def __setitem__(self, key, value):
        indices = self._to_indices(key)
        for index in indices:
            self.list[index] = value

    def __getitem__(self, item):
        indices = self._to_indices(item)
        if len(indices) > 0:
            if len(indices) > 1:
                result = [self.list[index] for index in indices]
                if self._orientation == Vector.COL:
                    return Vector(rows=len(result), initial_value=result, dtype=self._dtype)
                else:
                    return Vector(cols=len(result), initial_value=result, dtype=self._dtype)
            else:
                return self.list[indices[0]]
        else:
            return Vector(rows=0, cols=0, initial_value=[], dtype=self._dtype)

    def __str__(self):
        return ','.join((str(i) for i in self))
