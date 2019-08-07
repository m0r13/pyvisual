cdef class Value:
    @property
    def value(self):
        return None

    @value.setter
    def value(self, object value):
        pass

    def is_connected(self):
        return False

    cpdef has_changed(self):
        return False

    cpdef reset_changed(self):
        pass

    cpdef copy_to(self, object value):
        if self.has_changed():
            value.value = self.value

cdef class SettableValue(Value):
    cdef object _value
    cdef int _changed
    # force value is used for events
    # button widgets can force an event by setting this to 1. must reset it in the next frame also
    cdef int _force_value

    def __init__(self, default_value):
        self.value = default_value

    def __cinit__(self):
        self._value = None
        self._changed = False
        self._force_value = False

    @property
    def value(self):
        if self._force_value:
            return self._force_value
        return self._value
    @value.setter
    def value(self, object value):
        self._value = value
        self._changed = True

    @property
    def force_value(self):
        return self._force_value
    @force_value.setter
    def force_value(self, int force_value):
        self._force_value = force_value
        self._changed = True

    cpdef has_changed(self):
        return self._changed

    cpdef reset_changed(self):
        self._changed = False

cdef class ConnectedValue(Value):
    cdef object _connected_node
    cdef SettableValue _connected_value
    cdef SettableValue _manual_value
    cdef int _keep_value_on_disconnect
    cdef int _has_connection_changed

    def __init__(self, default_value, keep_value_on_disconnect=False):
        self._keep_value_on_disconnect = keep_value_on_disconnect
        self._manual_value = SettableValue(default_value)

    def __cinit__(self):
        self._connected_node = None
        self._keep_value_on_disconnect = True
        self._has_connection_changed = False

    def connect(self, node, port_id):
        self._connected_node = node
        self._connected_value = node.get_value(port_id)
        self._has_connection_changed = True

    def disconnect(self):
        # make the manual input keep the value when connection is removed
        if self._keep_value_on_disconnect and self._connected_value is not None:
            self._manual_value.value = self._connected_value.value
        self._connected_node = None
        self._connected_value = None
        self._has_connection_changed = True

    @property
    def manual_value(self):
        return self._manual_value

    @property
    def connected_node(self):
        return self._connected_node

    cpdef is_connected(self):
        return self._connected_node is not None

    @property
    def value(self):
        connected_value = self._connected_value
        manual_value = self._manual_value
        # connected value over manual value
        # but forced manual value over connected value
        if connected_value is not None and not manual_value._force_value:
            return connected_value.value
        return manual_value.value
    @value.setter
    def value(self, object value):
        self._manual_value.value = value

    cpdef has_changed(self):
        connected_value = self._connected_value
        return (connected_value and connected_value.has_changed()) \
                or self._manual_value.has_changed() \
                or self._has_connection_changed

    cpdef reset_changed(self):
        self._manual_value.reset_changed()
        self._has_connection_changed = False

