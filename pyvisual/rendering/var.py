import math
import time
import os
import re
import sys
import traceback

def make_var(x):
    if isinstance(x, Var):
        return x
    return Const(x)

def lerp(alpha, v0, v1):
    if not isinstance(alpha, Var):
        alpha = Const(alpha)
    return (Const(1.0) - alpha) * v0 + alpha * v1

class Var:
    
    @property
    def value(self):
        raise NotImplementedError()

    def __float__(self):
        return float(self.value)

    def apply(self, operation, *args):
        #return OpVar(operation, self, *map(make_var, args))
        return OpVar(operation, self, *args)

    def __add__(self, other):
        return self.apply(lambda a, b: a + b, other)
    def __sub__(self, other):
        return self.apply(lambda a, b: a - b, other)
    def __mul__(self, other):
        return self.apply(lambda a, b: a * b, other)
    def __truediv__(self, other):
        return self.apply(lambda a, b: a / b, other)
    def __floordiv__(self, other):
        return self.apply(lambda a, b: a // b, other)

    def __and__(self, other):
        return self.apply(lambda a, b: bool(a) and bool(b), other)
    def __or__(self, other):
        return self.apply(lambda a, b: bool(a) or bool(b), other)
    def __invert__(self):
        return self.apply(lambda a, b: not bool(a))

    # mod
    # pos
    # neg
    # abs
    # floor
    # ceil

    def map_range(self, min0, max0, min1, max1):
        # original range mapped to [0; 1]
        rel = (self - min0) / (max0 - min0)
        return Const(min1) + rel * (max1 - min1)

class Const(Var):
    def __init__(self, value=0.0):
        super().__init__()
        self.value = value

    @property
    def value(self):
        return self._value
    @value.setter
    def value(self, value):
        self._value = value

class OpVar(Var):
    def __init__(self, operation, *args):
        super().__init__()
        self._operation = operation
        self._args = args

    @property
    def value(self):
        return self._operation(*map(float, self._args))

class ExprVar(Var):
    def __init__(self, expr):
        super().__init__()
        self._expr = expr

    @property
    def value(self):
        return self._expr()

class ReloadVar(Var):
    # when we last updated vars
    last_update = 0
    # filename => number of vars currently (for assigning ids)
    counter = {}
    # variables per filename
    variables = {}
    variables_by_location = {}
    ignore_files = set()

    def __init__(self, value):
        self._value = float(value)

    @property
    def value(self):
        return self._value

    @classmethod
    def get(cls, frame, value):
        location = "%s%s" % (frame.filename, frame.lineno)

        # TODO hmm allow multiple variables per line or assume only one variable per line
        # (one variable per line would allow using variable in for-bodies for example)
        # (this that's better for now)
        if location in cls.variables_by_location:
            #print("Instance for location %s already exists" % location)
            return cls.variables_by_location[location]

        #print("Creating instance for", location)
        variable = cls(value)
        filename = frame.filename
        if filename not in ReloadVar.variables:
            cls.variables[filename] = []
        cls.variables[filename].append(variable)
        cls.variables_by_location[location] = variable
        return variable

    @staticmethod
    def reload_vars():
        for filename, variables in ReloadVar.variables.items():
            # ignore file not found errors
            # seems to happen the very moment a file is written
            try:
                if ReloadVar.last_update < os.path.getmtime(filename) and filename not in ReloadVar.ignore_files:
                    ReloadVar.reload_vars_from_file(filename, variables)
            except FileNotFoundError:
                pass
        ReloadVar.last_update = time.time()
    
    @staticmethod
    def reload_vars_from_file(filename, variables):
        source = ""
        print(os.getcwd(), filename)
        with open(filename, "r") as f:
            source = f.read()
        values = []
        #print("Gotta reload %s" % filename)
        for m in re.finditer(r"_V\((-?[0-9\.]+)\)", source):
            values.append(float(m.group(1)))
        if len(values) != len(variables):
            print("### Warning: Number of ReloadVar's in file %s has changed (got %d, expected %d). Ignoring reloading this file from now on." % (filename, len(values), len(variables)), file=sys.stderr)
            ReloadVar.ignore_files.add(filename)
        else:
            #print("Got values %s" % values)
            for value, variable in zip(values, variables):
                variable._value = value

def _V(value):
    frame = traceback.extract_stack()[-2]
    return ReloadVar.get(frame, value)

class Time(Var):

    @property
    def value(self):
        return time.time()

class RelativeTime(Var):
    def __init__(self, start=None):
        if start is None:
            start = time.time()
        self._start = float(start)

    @property
    def value(self):
        return time.time() - self._start
